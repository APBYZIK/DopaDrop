class ReceiptService:
    def build(self, order):
        return {'order_number': order.order_number, 'created_at': order.created_at,
                'lines': [{'product_id': l.product_id, 'product_name': l.product_name,
                           'unit_price_kopeks': l.unit_price_kopeks, 'quantity': l.quantity,
                           'line_total_kopeks': l.line_total_kopeks} for l in order.items],
                'item_count': order.item_count, 'total_kopeks': order.total_kopeks,
                'disclaimer': 'Это шуточная покупка. Деньги не списаны. Доставки не будет'}
