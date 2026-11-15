import pytest

from app.config import Config
from app.errors import ValidationError
from app.services.catalog_service import CatalogService
from app.services.cart_service import CartService


@pytest.fixture
def cart():
    return CartService(CatalogService(Config.CATALOG_PATH))


def test_total(cart, items):
    before = Config.CATALOG_PATH.read_bytes()
    result = cart.validate(items)
    assert result.item_count == 3
    assert result.total_kopeks == 189700
    assert [line.line_total_kopeks for line in result.lines] == [99800, 89900]
    assert Config.CATALOG_PATH.read_bytes() == before


@pytest.mark.parametrize('quantity', [0, -1, 11, 1.5, '2', True, None])
def test_bad_quantity(cart, quantity):
    with pytest.raises(ValidationError) as error:
        cart.validate([{'product_id': 'invisible-socks', 'quantity': quantity}])
    assert error.value.status_code == 422


@pytest.mark.parametrize('items', [[], {}, None, [1], [{'product_id': 'missing', 'quantity': 1}],
    [{'product_id': 'invisible-socks', 'quantity': 1, 'price': 1}],
    [{'product_id': 'invisible-socks', 'quantity': 1}] * 2,
    [{'product_id': 'invisible-socks', 'quantity': 1}] * 16])
def test_invalid_items(cart, items):
    with pytest.raises(ValidationError): cart.validate(items)


def test_limit(cart):
    with pytest.raises(ValidationError, match='50'):
        cart.validate([{'product_id': p.id, 'quantity': 10} for p in cart.catalog.list_products()[:6]])
