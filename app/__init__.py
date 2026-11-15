from pathlib import Path
from urllib.parse import urlsplit

import click
from flask import Flask, request

from app.config import Config
from app.errors import register_errors
from app.extensions import db
from app.services.catalog_service import CatalogService
from app.services.cart_service import CartService
from app.services.order_service import utc_now
from app.services.receipt_service import ReceiptService
from app.services.qr_code_service import QRCodeService
from app.services.tracking_service import TrackingService


def create_app(config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    base = app.config['PUBLIC_BASE_URL'].rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError('PUBLIC_BASE_URL должен содержать только http(s)://домен[:порт].')
    app.config['PUBLIC_BASE_URL'] = base
    if not app.config['SECRET_KEY'] or app.config['SECRET_KEY'] in ('development-only-change-me', 'change-me-in-production'):
        if app.config['PRODUCTION']:
            raise ValueError('Для production задайте SECRET_KEY.')
        if not app.testing:
            app.logger.warning('Используется SECRET_KEY для локальной разработки.')
    if app.config['PRODUCTION'] and parsed.scheme != 'https':
        raise ValueError('Для production PUBLIC_BASE_URL должен использовать HTTPS.')
    app.json.ensure_ascii = False
    db.init_app(app)
    catalog = CatalogService(app.config['CATALOG_PATH'])
    clock = app.config.get('CLOCK', utc_now)
    app.extensions['dopadrop'] = {
        'catalog': catalog, 'cart': CartService(catalog), 'clock': clock,
        'receipt': ReceiptService(), 'qr': QRCodeService(),
        'tracking': TrackingService(app.config['TRACKING_SCENARIOS_PATH'], clock),
    }
    from app.routes.pages import pages
    from app.routes.orders_api import orders_api
    from app.routes.qr import qr
    app.register_blueprint(pages)
    app.register_blueprint(orders_api)
    app.register_blueprint(qr)
    register_errors(app)

    @app.template_filter('format_rub')
    def format_rub(value):
        return f'{value // 100:,}'.replace(',', ' ') + f',{value % 100:02d} ₽'

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        if any(part in request.path for part in ('/orders', '/track')):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        click.echo('DopaDrop tables initialized. Existing data preserved.')

    return app
