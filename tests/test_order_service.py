import json
import re
import secrets
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.order import Order, OrderItem
from app.repositories.order_repository import OrderRepository
from app.routes.helpers import order_service
from app.services.cart_service import CartService
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService


def test_snapshot_and_tokens(app, items, tmp_path):
    with app.app_context():
        service = order_service()
        first = service.create_order(items, str(uuid4()))
        token, number = first.public_token, first.order_number
        assert re.fullmatch(r'[A-Za-z0-9_-]{32}', token)
        assert re.fullmatch(r'DD-20261115-[A-F0-9]{6}', number)
        assert first.created_at.utcoffset().total_seconds() == 0
        assert first.items[0].product_name == 'Невидимые носки'
        data = json.loads(app.config['CATALOG_PATH'].read_text(encoding='utf-8'))
        data['products'][0].update(name='Новое название', price_kopeks=1)
        path = tmp_path / 'new.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        service.cart = CartService(CatalogService(path))
        second = service.create_order(items, str(uuid4()))
        assert second.public_token != token and second.order_number != number
        assert second.total_kopeks == 89902
        db.session.expire_all()
        saved = service.get_order(token)
        assert saved.total_kopeks == 189700
        assert saved.items[0].product_name == 'Невидимые носки'
        assert saved.items[0].unit_price_kopeks == 49900
        receipt = app.extensions['dopadrop']['receipt'].build(saved)
        assert receipt['total_kopeks'] == 189700
        assert receipt['lines'][0]['product_name'] == 'Невидимые носки'


def test_collision_retry(app, items):
    with app.app_context():
        first = order_service().create_order(items, str(uuid4()))
        values = iter([first.public_token, secrets.token_urlsafe(24)])
        service = OrderService(app.extensions['dopadrop']['cart'], OrderRepository(db.session),
                               app.extensions['dopadrop']['clock'], lambda: next(values))
        second = service.create_order(items, str(uuid4()))
        assert second.public_token != first.public_token
        assert db.session.scalar(select(func.count()).select_from(Order)) == 2


def test_rollback(app, items, monkeypatch):
    with app.app_context():
        service = order_service()
        original = service.repository.save
        def fail(order):
            original(order)
            raise RuntimeError('write failed after flush')
        monkeypatch.setattr(service.repository, 'save', fail)
        with pytest.raises(RuntimeError):
            service.create_order(items, str(uuid4()))
        assert db.session.scalar(select(func.count()).select_from(Order)) == 0
        assert db.session.scalar(select(func.count()).select_from(OrderItem)) == 0


def test_database_constraints_cascade(app, items):
    with app.app_context():
        order = order_service().create_order(items, str(uuid4()))
        order.items[0].quantity = 0
        with pytest.raises(IntegrityError): db.session.commit()
        db.session.rollback()
        db.session.delete(order)
        db.session.commit()
        assert db.session.scalar(select(func.count()).select_from(OrderItem)) == 0


def test_idempotency_race_recovery(app, items, monkeypatch):
    with app.app_context():
        key = str(uuid4())
        existing = order_service().create_order(items, key)
        service = order_service()
        lookup = service.repository.get_by_idempotency_key
        calls = 0
        def hidden_on_first(value):
            nonlocal calls
            calls += 1
            return None if calls == 1 else lookup(value)
        monkeypatch.setattr(service.repository, 'get_by_idempotency_key', hidden_on_first)
        replay = service.create_order(items, key)
        assert replay.public_token == existing.public_token
        assert not service.was_created
        assert db.session.scalar(select(func.count()).select_from(Order)) == 1
