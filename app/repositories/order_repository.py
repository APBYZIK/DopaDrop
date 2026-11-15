from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.order import Order


class OrderRepository:
    def __init__(self, session):
        self.session = session

    def get_by_public_token(self, token):
        return self.session.scalar(select(Order).where(Order.public_token == token).options(selectinload(Order.items)))

    def get_by_idempotency_key(self, key):
        return self.session.scalar(select(Order).where(Order.idempotency_key == key).options(selectinload(Order.items)))

    def save(self, order):
        self.session.add(order)
        self.session.flush()
        return order
