from dataclasses import asdict

from flask import Blueprint, abort, jsonify, request

from app.errors import ValidationError
from app.routes.helpers import iso, links, order_service, services, tracking_payload

orders_api = Blueprint('orders_api', __name__, url_prefix='/api')


@orders_api.get('/catalog')
def catalog():
    catalog = services()['catalog']
    return jsonify(categories=[asdict(c) for c in catalog.list_categories()], products=[asdict(p) for p in catalog.list_products()])


@orders_api.post('/orders')
def create_order():
    if request.mimetype != 'application/json':
        abort(415)
    data = request.get_json()
    if not isinstance(data, dict) or set(data) != {'items', 'idempotency_key'}:
        raise ValidationError('invalid_fields', 'Нужны только поля items и idempotency_key.')
    service = order_service()
    order = service.create_order(data['items'], data['idempotency_key'])
    receipt = services()['receipt'].build(order)
    payload = {'order_number': order.order_number, 'public_token': order.public_token, 'created_at': iso(order.created_at),
               'total_kopeks': order.total_kopeks, 'item_count': order.item_count, 'items': receipt['lines']}
    return jsonify(order=payload, links=links(order)), 201 if service.was_created else 200


@orders_api.get('/orders/<public_token>/tracking')
def tracking(public_token):
    return jsonify(tracking_payload(order_service().get_order(public_token)))
