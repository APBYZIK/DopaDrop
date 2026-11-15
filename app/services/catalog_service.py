import json
import re
from collections import Counter
from pathlib import Path

from app.models.dto import Category, Product

ID_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*', re.ASCII)


class CatalogService:
    def __init__(self, catalog_path: Path):
        try:
            data = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
            if type(data['schema_version']) is not int or data['schema_version'] != 1:
                raise ValueError('неподдерживаемая версия')
            categories = [Category(**row) for row in data['categories']]
            products = [Product(**row) for row in data['products']]
            if len(categories) != 5 or len(products) != 15:
                raise ValueError('ожидаются 5 категорий и 15 товаров')
            for rows in (categories, products):
                ids = [row.id for row in rows]
                if any(not isinstance(i, str) or len(i) > 64 or not ID_PATTERN.fullmatch(i) for i in ids) or len(set(ids)) != len(ids):
                    raise ValueError('неверные или повторяющиеся ID')
                if any(not isinstance(row.name, str) or not row.name.strip() or len(row.name) > 160 for row in rows):
                    raise ValueError('неверное название')
            category_ids = {c.id for c in categories}
            for p in products:
                if p.category_id not in category_ids:
                    raise ValueError('неизвестная категория')
                if type(p.price_kopeks) is not int or not 0 <= p.price_kopeks <= 10_000_000:
                    raise ValueError('цена должна быть целым числом копеек от 0 до 10000000')
                if type(p.featured) is not bool or any(not isinstance(t, str) or not t.strip() for t in (p.description, p.meme, p.emoji)):
                    raise ValueError('неверные поля товара')
            if any(n != 3 for n in Counter(p.category_id for p in products).values()):
                raise ValueError('нужно по 3 товара в категории')
            self._categories, self._products = tuple(categories), tuple(products)
            self._by_id = {p.id: p for p in products}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError(f'Ошибка каталога {catalog_path}: {exc}') from exc

    def list_products(self, *, category_id=None, query=None):
        query = (query or '').strip().casefold()
        return [p for p in self._products if (not category_id or p.category_id == category_id)
                and (not query or query in f'{p.name} {p.description}'.casefold())]

    def get_product(self, product_id):
        return self._by_id.get(product_id)

    def list_categories(self):
        return list(self._categories)
