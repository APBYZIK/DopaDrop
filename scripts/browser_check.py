"""Optional real-browser regression checks; isolated DB, no user data touched.

Run: python scripts/browser_check.py
Uses installed Edge on Windows; otherwise Playwright Chromium.
"""
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import func, select
from werkzeug.serving import make_server

from app import create_app
from app.extensions import db
from app.models.order import Order


def main():
    artifacts = Path('artifacts').resolve()
    artifacts.mkdir(exist_ok=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    now = [datetime(2026, 11, 15, 12, tzinfo=timezone.utc)]
    with TemporaryDirectory(prefix='browser-', dir=artifacts) as temporary:
        app = create_app({'TESTING':True, 'CLOCK':lambda: now[0],
                          'SQLALCHEMY_DATABASE_URI':f'sqlite:///{Path(temporary).as_posix()}/browser.db',
                          'PUBLIC_BASE_URL':'http://127.0.0.1:5010'})
        with app.app_context(): db.create_all()
        server = make_server('127.0.0.1', 5010, app, threaded=True)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        errors, checks = [], []
        try:
            with sync_playwright() as p:
                edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
                browser = p.chromium.launch(headless=True, executable_path=str(edge) if edge.exists() else None)
                context = browser.new_context(viewport={'width':1280,'height':900})
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto('http://127.0.0.1:5010')
                expect(page.locator('.product-card')).to_have_count(15)
                page.screenshot(path=str(artifacts / 'catalog-desktop.png'), full_page=True)
                page.select_option('#category', 'invisible')
                expect(page.locator('.product-card')).to_have_count(3)
                page.goto('http://127.0.0.1:5010/?q=НОСКИ')
                expect(page.locator('.product-card')).to_have_count(1)
                checks.append('catalog, category and case-insensitive search')
                page.goto('http://127.0.0.1:5010')
                page.locator('[data-add="invisible-socks"]').click()
                page.locator('[data-add="invisible-socks"]').click()
                page.locator('[data-add="tomorrow-planner"]').click()
                page.goto('http://127.0.0.1:5010/cart')
                expect(page.locator('.cart-row')).to_have_count(2)
                expect(page.locator('[data-cart-count]')).to_have_text('3')
                assert '1 897,00' in page.locator('.cart-total').inner_text().replace('\xa0',' ')
                page.reload()
                expect(page.locator('.cart-row')).to_have_count(2)
                other = context.new_page()
                other.goto('http://127.0.0.1:5010/cart')
                expect(other.locator('[data-cart-count]')).to_have_text('3')
                page.locator('[data-product="invisible-socks"] input').fill('3')
                page.locator('[data-product="invisible-socks"] input').press('Tab')
                expect(other.locator('[data-cart-count]')).to_have_text('4')
                page.locator('[data-product="invisible-socks"] input').fill('2')
                page.locator('[data-product="invisible-socks"] input').press('Tab')
                expect(other.locator('[data-cart-count]')).to_have_text('3')
                other.close()
                checks.append('cart total, quantity, reload and two-tab storage sync')
                for width in (320,375,768,1280):
                    page.set_viewport_size({'width':width,'height':900})
                    for path in ('/cart', '/checkout'):
                        page.goto('http://127.0.0.1:5010' + path)
                        expect(page.locator('.cart-row')).to_have_count(2)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width,path,'filled')
                        if width == 375:
                            page.screenshot(path=str(artifacts / (path[1:] + '-mobile.png')), full_page=True)
                page.goto('http://127.0.0.1:5010/checkout')
                expect(page.locator('#checkout-form')).to_be_visible()
                page.locator('#submit-order').click()
                expect(page).to_have_url('http://127.0.0.1:5010/checkout')
                page.locator('#fake-consent').check()
                sent = []
                def lose_response(route):
                    sent.append(route.request.post_data_json)
                    route.fetch()  # The server commits, but the browser loses the response.
                    route.abort('failed')
                page.route('**/api/orders', lose_response)
                page.locator('#submit-order').click()
                expect(page.locator('#checkout-message')).to_contain_text('Повторите')
                first_attempt = page.evaluate("JSON.parse(sessionStorage.getItem('dopadrop.checkout.v1'))")
                page.unroute('**/api/orders')
                page.reload()
                expect(page.locator('#checkout-form')).to_be_visible()
                page.locator('#fake-consent').check()
                page.locator('#submit-order').dblclick()
                page.wait_for_url('**/orders/*/success')
                assert sent[0] == first_attempt
                with app.app_context():
                    assert db.session.scalar(select(func.count()).select_from(Order)) == 1
                expect(page.locator('.receipt-total')).to_contain_text('1 897,00')
                expect(page.locator('.qr-code')).to_be_visible()
                assert page.locator('.qr-code').evaluate('(img) => img.complete && img.naturalWidth > 0')
                assert page.evaluate("JSON.parse(localStorage.getItem('dopadrop.cart.v1')).items.length") == 0
                page.screenshot(path=str(artifacts / 'receipt-desktop.png'), full_page=True)
                success_url = page.url
                page.reload()
                checks.append('consent, lost POST response, reload retry, double click, single DB order, receipt and QR')
                page.clock.install()
                page.locator('a.button', has_text='Отследить').click()
                tracking_url = page.url
                expect(page.locator('[aria-current="step"]')).to_have_attribute('data-stage','accepted')
                polls = []
                page.on('request', lambda req: polls.append(req.url) if req.url.endswith('/tracking') else None)
                page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true,get:()=>true}); document.dispatchEvent(new Event('visibilitychange'))")
                before = len(polls)
                page.clock.fast_forward(10000)
                assert len(polls) == before
                now[0] += timedelta(seconds=30)
                page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true,get:()=>false}); document.dispatchEvent(new Event('visibilitychange'))")
                expect(page.locator('[aria-current="step"]')).to_have_attribute('data-stage','packing')
                page.route('**/tracking', lambda route: route.abort('failed'))
                page.clock.fast_forward(5100)
                expect(page.locator('#tracking-message')).to_contain_text('Не удалось обновить')
                expect(page.locator('[aria-current="step"]')).to_have_attribute('data-stage','packing')
                page.unroute('**/tracking')
                for offset, stage in [(30,'packing'),(90,'courier'),(180,'multiverse'),(300,'delivered')]:
                    now[0] = datetime(2026,11,15,12,tzinfo=timezone.utc) + timedelta(seconds=offset)
                    page.clock.fast_forward(5100)
                    expect(page.locator('[aria-current="step"]')).to_have_attribute('data-stage',stage)
                before = len(polls)
                page.clock.fast_forward(20000)
                assert len(polls) == before
                checks.append('visibility event pauses polling, return refreshes, network failure preserves status, final stops polling')
                now[0] += timedelta(days=1)
                page.reload()
                expect(page.locator('[aria-current="step"]')).to_have_attribute('data-stage','delivered')
                second_context = browser.new_context()
                second = second_context.new_page()
                second.goto(tracking_url)
                expect(second.locator('[aria-current="step"]')).to_have_attribute('data-stage','delivered')
                second_context.close()
                page.screenshot(path=str(artifacts / 'tracking-desktop.png'), full_page=True)
                checks.append('real JS polling at all four transitions, reload and independent browser context')
                # Validate the entire page width, not only a cropped screenshot.
                for width in (320,375,768,1280):
                    page.set_viewport_size({'width':width,'height':900})
                    for path in ('/', '/cart', '/checkout', success_url, tracking_url):
                        page.goto(path if path.startswith('http') else 'http://127.0.0.1:5010' + path)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width,path)
                        if width == 375 and path == '/':
                            page.screenshot(path=str(artifacts / 'catalog-mobile.png'), full_page=True)
                checks.append('all pages have no horizontal overflow at 320/375/768/1280px')
                page.goto('http://127.0.0.1:5010/cart')
                page.evaluate("localStorage.setItem('dopadrop.cart.v1', '{broken')")
                page.reload()
                expect(page.locator('.empty')).to_contain_text('откладывает')
                expect(page.locator('#toast')).to_contain_text('повреждена')
                page.goto('http://127.0.0.1:5010')
                page.locator('[data-add="invisible-socks"]').click()
                page.goto('http://127.0.0.1:5010/cart')
                page.get_by_role('button', name='Удалить: Невидимые носки', exact=True).click()
                expect(page.locator('.empty')).to_be_visible()
                page.goto('http://127.0.0.1:5010/checkout')
                expect(page.locator('.empty')).to_be_visible()
                expect(page.locator('#checkout-form')).to_be_hidden()
                checks.append('damaged storage recovery, remove item and empty checkout')
                page.evaluate("""localStorage.setItem('dopadrop.cart.v1', JSON.stringify({version:1,items:[
                    {product_id:'gone',quantity:1},{product_id:'invisible-socks',quantity:8},
                    {product_id:'invisible-socks',quantity:8}]}))""")
                page.goto('http://127.0.0.1:5010/cart')
                expect(page.locator('.cart-row')).to_have_count(1)
                expect(page.locator('[data-cart-count]')).to_have_text('10')
                expect(page.locator('.quantity input')).to_have_value('10')
                checks.append('old unknown products removed and duplicate quantities clamped')
                no_storage = browser.new_context()
                no_storage.add_init_script("""Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Blocked','SecurityError')}});""")
                blocked = no_storage.new_page()
                blocked.on('pageerror', lambda error: errors.append(str(error)))
                blocked.goto('http://127.0.0.1:5010')
                blocked.locator('[data-add="invisible-socks"]').click()
                expect(blocked.locator('[data-cart-count]')).to_have_text('1')
                no_storage.close()
                checks.append('blocked localStorage uses in-memory cart without JS errors')
                assert not errors, errors
                browser.close()
                (artifacts / 'browser-report.json').write_text(json.dumps({'checks':checks,'page_errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
                print('Browser checks passed:', len(checks))
                for check in checks: print('PASS:', check)
        finally:
            server.shutdown()
            worker.join(timeout=5)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == '__main__':
    main()
