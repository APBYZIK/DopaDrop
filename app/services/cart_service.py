from app.errors import ValidationError
from app.models.dto import CartLine, ValidatedCart


class CartService:
    def __init__(self, catalog):
        self.catalog = catalog

    def validate(self, raw_items):
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 15:
            raise ValidationError('invalid_items', 'В корзине должно быть от 1 до 15 разных товаров.')
        lines, seen = [], set()
        for index, item in enumerate(raw_items):
            details = {'index': index}
            if not isinstance(item, dict) or set(item) != {'product_id', 'quantity'}:
                raise ValidationError('invalid_item_fields', 'Для товара нужны только product_id и quantity.', details)
            pid, quantity = item['product_id'], item['quantity']
            if not isinstance(pid, str) or not 1 <= len(pid) <= 64 or not self.catalog.get_product(pid):
                raise ValidationError('unknown_product', 'Этот товар потерялся в мультивселенной. Удалите его из корзины.', details)
            if pid in seen:
                raise ValidationError('duplicate_product', 'Товар указан дважды. Измените его количество в одной строке.', details)
            if type(quantity) is not int or not 1 <= quantity <= 10:
                raise ValidationError('invalid_quantity', 'Количество товара должно быть целым числом от 1 до 10.', details)
            seen.add(pid)
            product = self.catalog.get_product(pid)
            lines.append(CartLine(pid, product.name, product.price_kopeks, quantity, product.price_kopeks * quantity))
        count = sum(line.quantity for line in lines)
        if count > 50:
            raise ValidationError('too_many_items', 'За один раз можно заказать не больше 50 вещей.')
        return ValidatedCart(tuple(lines), count, sum(line.line_total_kopeks for line in lines))
