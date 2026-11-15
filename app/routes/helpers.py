from dataclasses import asdict

from flask import current_app, url_for

from app.extensions import db
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService


def services():
    return current_app.extensions['dopadrop']


def order_service():
    s = services()
    return OrderService(s['cart'], OrderRepository(db.session), s['clock'], current_app.config.get('TOKEN_GENERATOR'))


def iso(value):
    return value.isoformat().replace('+00:00', 'Z') if value is not None else None


def links(order):
    token = order.public_token
    return {'success': url_for('pages.success', public_token=token),
            'tracking': url_for('pages.tracking', public_token=token),
            'qr': url_for('qr.image', public_token=token)}


def tracking_payload(order):
    s = services()
    state = s['tracking'].get_state(order)
    return {'order_number': order.order_number, 'server_time': iso(s['clock']()), 'created_at': iso(order.created_at),
            'tracking': {'current_stage_index': state.current_stage_index, 'current_stage_id': state.current_stage.id,
                         'elapsed_seconds': state.elapsed_seconds, 'is_final': state.is_final,
                         'next_stage_at': iso(state.next_stage_at),
                         'stages': [dict(asdict(stage), state='complete' if i < state.current_stage_index else 'current' if i == state.current_stage_index else 'pending')
                                    for i, stage in enumerate(state.stages)]}}
