from datetime import timezone

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.types import DateTime, TypeDecorator

from app.extensions import db


class UTCDateTime(TypeDecorator):
    """SQLite stores naive UTC; Python always receives aware UTC datetimes."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError('Expected timezone-aware datetime')
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    public_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    order_number = db.Column(db.String(32), nullable=False, unique=True)
    created_at = db.Column(UTCDateTime(), nullable=False)
    total_kopeks = db.Column(db.Integer, nullable=False)
    item_count = db.Column(db.Integer, nullable=False)
    tracking_scenario_id = db.Column(db.String(64), nullable=False, default='default-v1')
    tracking_version = db.Column(db.Integer, nullable=False, default=1)
    idempotency_key = db.Column(db.String(36), nullable=False, unique=True, index=True)
    request_fingerprint = db.Column(db.String(64), nullable=False)
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan', order_by='OrderItem.id')
    __table_args__ = (CheckConstraint('total_kopeks >= 0'), CheckConstraint('item_count BETWEEN 1 AND 50'))


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.String(64), nullable=False)
    product_name = db.Column(db.String(160), nullable=False)
    unit_price_kopeks = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total_kopeks = db.Column(db.Integer, nullable=False)
    order = db.relationship('Order', back_populates='items')
    __table_args__ = (UniqueConstraint('order_id', 'product_id'), CheckConstraint('quantity BETWEEN 1 AND 10'),
                      CheckConstraint('unit_price_kopeks >= 0'), CheckConstraint('line_total_kopeks >= 0'),
                      CheckConstraint('line_total_kopeks = unit_price_kopeks * quantity'))
