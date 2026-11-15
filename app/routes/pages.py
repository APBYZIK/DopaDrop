from flask import Blueprint, current_app, render_template, request

from app.routes.helpers import links, order_service, services, tracking_payload

pages = Blueprint('pages', __name__)


@pages.get('/')
def index():
    catalog = services()['catalog']
    category, query = request.args.get('category', ''), request.args.get('q', '')
    return render_template('index.html', products=catalog.list_products(category_id=category, query=query),
                           categories=catalog.list_categories(), category=category, query=query)


@pages.get('/cart')
def cart():
    return render_template('cart.html')


@pages.get('/checkout')
def checkout():
    return render_template('checkout.html')


@pages.get('/orders/<public_token>/success')
def success(public_token):
    order = order_service().get_order(public_token)
    urls = links(order)
    return render_template('order_success.html', receipt=services()['receipt'].build(order), links=urls,
                           absolute_tracking=current_app.config['PUBLIC_BASE_URL'] + urls['tracking'], private_page=True)


@pages.get('/track/<public_token>')
def tracking(public_token):
    order = order_service().get_order(public_token)
    return render_template('tracking.html', payload=tracking_payload(order), public_token=public_token,
                           links=links(order), private_page=True)
