import json
from collections import Counter

import pytest

from app.config import Config
from app.services.catalog_service import CatalogService


def test_catalog():
    catalog = CatalogService(Config.CATALOG_PATH)
    products = catalog.list_products()
    assert len(products) == len({p.id for p in products}) == 15
    assert len(catalog.list_categories()) == 5
    assert set(Counter(p.category_id for p in products).values()) == {3}
    assert all(type(p.price_kopeks) is int and p.price_kopeks >= 0 for p in products)
    assert catalog.get_product('invisible-socks').price_kopeks == 49900
    assert catalog.get_product('missing') is None
    assert len(catalog.list_products(category_id='invisible')) == 3
    assert catalog.list_products(category_id='missing') == []
    assert len(catalog.list_products(query='  НОСКИ ')) == 1
    assert len(catalog.list_products(query='   ')) == 15
    assert catalog.list_products(query='абракадабра') == []
    assert catalog.list_products(query='выходов')[0].id == 'invisible-socks'


@pytest.mark.parametrize('mutation', ['json', 'duplicate', 'category', 'negative', 'bool_price', 'featured', 'counts', 'version'])
def test_bad_catalog(tmp_path, mutation):
    data = json.loads(Config.CATALOG_PATH.read_text(encoding='utf-8'))
    if mutation == 'duplicate': data['products'][1]['id'] = data['products'][0]['id']
    if mutation == 'category': data['products'][0]['category_id'] = 'missing'
    if mutation == 'negative': data['products'][0]['price_kopeks'] = -1
    if mutation == 'bool_price': data['products'][0]['price_kopeks'] = True
    if mutation == 'featured': data['products'][0]['featured'] = 'true'
    if mutation == 'counts': data['products'].pop()
    if mutation == 'version': data['schema_version'] = True
    path = tmp_path / 'catalog.json'
    path.write_text('{' if mutation == 'json' else json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='Ошибка каталога'):
        CatalogService(path)
