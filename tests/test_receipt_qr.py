from io import BytesIO
from uuid import uuid4

from PIL import Image

from app.services.qr_code_service import QRCodeService


def test_qr_url_and_png(app, client, items, monkeypatch):
    data = client.post('/api/orders', json={'items':items,'idempotency_key':str(uuid4())}).json
    calls = []
    original = QRCodeService.make_png
    def spy(self, url):
        calls.append(url)
        return original(self, url)
    monkeypatch.setattr(QRCodeService, 'make_png', spy)
    response = client.get(data['links']['qr'], headers={'Host':'attacker.test'})
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    assert response.data.startswith(b'\x89PNG\r\n\x1a\n')
    assert calls == ['https://example.test' + data['links']['tracking']]
    image = Image.open(BytesIO(response.data))
    assert image.width == image.height and image.width >= 264
    assert response.headers['Cache-Control'] == 'no-store'
