from flask import Blueprint, Response, current_app

from app.routes.helpers import links, order_service, services

qr = Blueprint('qr', __name__)


@qr.get('/orders/<public_token>/qr.png')
def image(public_token):
    order = order_service().get_order(public_token)
    content = services()['qr'].make_png(current_app.config['PUBLIC_BASE_URL'] + links(order)['tracking'])
    return Response(content, mimetype='image/png')
