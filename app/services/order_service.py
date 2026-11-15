import hashlib
import json
import re
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models.order import Order, OrderItem


def utc_now():
    return datetime.now(timezone.utc)


class OrderService:
    def __init__(self, cart, repository, clock=utc_now, token_generator=None):
        self.cart, self.repository, self.clock = cart, repository, clock
        self.token_generator = token_generator or (lambda: secrets.token_urlsafe(24))
        self.was_created = False  # This service is request-scoped, never shared.

    def create_order(self, raw_items, idempotency_key):
        try:
            key = UUID(idempotency_key)
            if key.version != 4 or len(idempotency_key) != 36 or str(key) != idempotency_key.lower():
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValidationError('invalid_idempotency_key', 'Для оформления нужен корректный UUIDv4.') from None
        key = str(key)
        cart = self.cart.validate(raw_items)
        normalized = sorted([{'product_id': l.product_id, 'quantity': l.quantity} for l in cart.lines], key=lambda l: l['product_id'])
        fingerprint = hashlib.sha256(json.dumps(normalized, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
        existing = self.repository.get_by_idempotency_key(key)
        if existing:
            return self._replay(existing, fingerprint)
        for attempt in range(3):
            now = self.clock().astimezone(timezone.utc)
            order = Order(public_token=self.token_generator(), order_number=f'DD-{now:%Y%m%d}-{secrets.token_hex(3).upper()}',
                          created_at=now, total_kopeks=cart.total_kopeks, item_count=cart.item_count,
                          tracking_scenario_id='default-v1', tracking_version=1,
                          idempotency_key=key, request_fingerprint=fingerprint,
                          items=[OrderItem(**asdict(line)) for line in cart.lines])
            try:
                self.repository.save(order)
                self.repository.session.commit()
                self.was_created = True
                return order
            except IntegrityError:
                self.repository.session.rollback()
                existing = self.repository.get_by_idempotency_key(key)
                if existing:
                    return self._replay(existing, fingerprint)
                if attempt == 2:
                    raise
            except Exception:
                self.repository.session.rollback()
                raise

    def _replay(self, existing, fingerprint):
        self.was_created = False
        if existing.request_fingerprint != fingerprint:
            raise ConflictError()
        return existing

    def get_order(self, public_token):
        if not isinstance(public_token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}', public_token, re.ASCII):
            raise NotFoundError()
        order = self.repository.get_by_public_token(public_token)
        if order is None:
            raise NotFoundError()
        return order
