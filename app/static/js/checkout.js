import {createOrder} from './api.js';
import {readCart, clearCart, notify, ready, hasCatalog} from './cart.js';
const form = document.querySelector('#checkout-form'), button = document.querySelector('#submit-order');
const message = document.querySelector('#checkout-message'), attemptKey = 'dopadrop.checkout.v1';
let busy = false, attempt = null;
try { attempt = JSON.parse(sessionStorage.getItem(attemptKey)); } catch { /* A fresh attempt is safe when no valid saved request exists. */ }
function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16)); bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(b => b.toString(16).padStart(2,'0')).join('');
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !form.reportValidity()) return;
  await ready;
  if (!hasCatalog()) {message.textContent = 'Сначала загрузите каталог кнопкой повтора.'; return;}
  const items = readCart().items.sort((a,b) => a.product_id.localeCompare(b.product_id));
  if (!items.length) {message.textContent = 'Сначала добавьте что-нибудь в корзину.'; return;}
  if (!attempt || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(attempt.idempotency_key) || JSON.stringify(attempt.items) !== JSON.stringify(items)) {
    attempt = {idempotency_key:uuid(), items};
    try {sessionStorage.setItem(attemptKey, JSON.stringify(attempt));}
    catch {notify('Попытка сохранена только в памяти. При сбое повторите оформление в этой вкладке, не перезагружая её.');}
  }
  busy = true; button.disabled = true; message.textContent = 'Оформляем ваше ничего…';
  try {
    const result = await createOrder(attempt);
    form.dataset.submitted = 'true';
    const link = document.querySelector('#success-link'); link.href = result.links.success; link.hidden = false;
    message.textContent = 'Заказ создан. Если переход не произошёл, откройте чек по ссылке ниже.';
    clearCart();
    try {sessionStorage.removeItem(attemptKey);} catch {}
    attempt = null; window.location.assign(result.links.success);
  } catch (error) {
    message.textContent = error.message + ' Повторите отправку: случайный дубль не появится.';
    busy = false; button.disabled = false; button.textContent = 'Повторить оформление без оплаты →';
  }
});
