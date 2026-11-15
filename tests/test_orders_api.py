from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models.order import Order


def test_create_replay_conflict(client, app, items):
    payload = {'idempotency_key': str(uuid4()), 'items': items}
    first = client.post('/api/orders', json=payload)
    assert first.status_code == 201
    body = first.json
    assert body['order']['total_kopeks'] == 189700
    assert body['order']['item_count'] == 3
    assert 'id' not in body['order']
    assert body['order']['created_at'].endswith('Z')
    assert first.headers['Cache-Control'] == 'no-store'
    payload['items'].reverse()
    replay = client.post('/api/orders', json=payload)
    assert replay.status_code == 200
    assert replay.json == body
    payload['items'][0]['quantity'] = 3
    assert client.post('/api/orders', json=payload).status_code == 409
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Order)) == 1


@pytest.mark.parametrize('key', [None, '', True, 123, 'x', str(uuid4()).replace('-', ''), '00000000-0000-1000-8000-000000000000'])
def test_bad_key(client, items, key):
    assert client.post('/api/orders', json={'items': items, 'idempotency_key': key}).status_code == 422


@pytest.mark.parametrize('payload', [{}, [], None, {'items': []}, {'items': [], 'idempotency_key': str(uuid4()), 'total_kopeks': 1}])
def test_bad_fields(client, payload):
    import json
    response = client.post('/api/orders', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 422
    assert set(response.json['error']) == {'code', 'message', 'details'}


@pytest.mark.parametrize('quantity', [0, -1, 11, 1.5, '2', True, None])
def test_quantity_http(client, quantity):
    response = client.post('/api/orders', json={'idempotency_key': str(uuid4()), 'items': [{'product_id': 'invisible-socks', 'quantity': quantity}]})
    assert response.status_code == 422
    assert response.json['error']['code'] == 'invalid_quantity'


def test_untrusted_cart(client, items):
    for invalid in ([], [{'product_id': 'missing', 'quantity': 1}], [dict(items[0], unit_price_kopeks=1)], items * 2):
        assert client.post('/api/orders', json={'idempotency_key': str(uuid4()), 'items': invalid}).status_code == 422


def test_http_errors(client):
    assert client.post('/api/orders', data='{', content_type='application/json').status_code == 400
    assert client.post('/api/orders', data='{}', content_type='text/plain').status_code == 415
    assert client.post('/api/orders', data=' ' * 17000, content_type='application/json').status_code == 413
    assert client.get('/api/orders').status_code == 405
    assert client.get('/api/unknown').status_code == 404
    assert 'Access-Control-Allow-Origin' not in client.options('/api/orders', headers={'Origin':'https://evil.test'}).headers


def test_storage_failure(client, monkeypatch, items, app):
    from app.repositories.order_repository import OrderRepository
    def fail(self, order):
        self.session.add(order)
        self.session.flush()
        raise OSError('sensitive SQL values')
    monkeypatch.setattr(OrderRepository, 'save', fail)
    response = client.post('/api/orders', json={'items':items, 'idempotency_key':str(uuid4())})
    assert response.status_code == 500
    assert b'sensitive' not in response.data
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Order)) == 0
