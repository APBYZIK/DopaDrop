from uuid import uuid4

import pytest


def test_catalog_pages(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.count(b'class="product-card"') == 15
    assert client.get('/?category=invisible').data.count(b'class="product-card"') == 3
    assert client.get('/?q=НОСКИ').data.count(b'class="product-card"') == 1
    assert client.get('/?category=unknown').data.count(b'class="product-card"') == 0
    assert len(client.get('/api/catalog').json['products']) == 15
    for path in ('/cart', '/checkout'):
        assert client.get(path).status_code == 200


@pytest.mark.parametrize('token', ['1', 'unknown', 'a'*32, 'a'*65])
def test_unknown_order(client, token):
    for path in (f'/track/{token}', f'/orders/{token}/success', f'/orders/{token}/qr.png', f'/api/orders/{token}/tracking'):
        response = client.get(path)
        assert response.status_code == 404
        assert response.headers['Cache-Control'] == 'no-store'


def test_order_pages(client, items):
    data = client.post('/api/orders', json={'items':items,'idempotency_key':str(uuid4())}).json
    for link in ('success','tracking'):
        response = client.get(data['links'][link])
        assert response.status_code == 200
        assert data['order']['order_number'].encode() in response.data
        assert b'noindex,nofollow' in response.data
        assert response.headers['Referrer-Policy'] == 'no-referrer'
        assert response.headers['Cache-Control'] == 'no-store'
    success = client.get(data['links']['success']).text
    assert '1 897,00 ₽' in success
    assert 'Деньги не списаны' in success
    assert data['links']['qr'] in success and data['links']['tracking'] in success


def test_init_db_preserves_orders(app, client, items):
    data = client.post('/api/orders', json={'items':items,'idempotency_key':str(uuid4())}).json
    result = app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code == 0
    assert client.get(data['links']['success']).status_code == 200


def test_xss_escaped(client):
    response = client.get('/?q=<script>alert(1)</script>')
    assert b'<script>alert(1)</script>' not in response.data
    assert b'&lt;script&gt;' in response.data
