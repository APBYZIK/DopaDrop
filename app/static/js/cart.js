import {getCatalog} from './api.js';
const KEY = 'dopadrop.cart.v1';
let memory = {version:1, items:[]}, storageAvailable = true, products = null, toastTimer;
export const money = value => new Intl.NumberFormat('ru-RU', {style:'currency', currency:'RUB'}).format(value / 100);
export function notify(message) {
  const toast = document.querySelector('#toast');
  if (!toast) return;
  toast.textContent = message; toast.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => {toast.hidden = true;}, 6500);
}
function persist(cart) {
  memory = structuredClone(cart);
  if (storageAvailable) {
    try { localStorage.setItem(KEY, JSON.stringify(cart)); }
    catch { storageAvailable = false; notify('Хранилище недоступно. Корзина останется только до перезагрузки страницы.'); }
  }
}
export function readCart() {
  let data = memory;
  if (storageAvailable) {
    try { data = JSON.parse(localStorage.getItem(KEY) || '{"version":1,"items":[]}'); }
    catch { data = null; }
  }
  if (!data || data.version !== 1 || !Array.isArray(data.items)) {
    notify('Сохранённая корзина повреждена или устарела. Начнём с чистого листа.');
    persist({version:1, items:[]}); return structuredClone(memory);
  }
  const items = [], byId = new Map();
  let count = 0;
  for (const row of data.items) {
    if (!row || typeof row.product_id !== 'string' || !Number.isInteger(row.quantity) || row.quantity < 1) continue;
    if (products && !products.has(row.product_id)) continue;
    const existing = byId.get(row.product_id);
    if (!existing && items.length >= 15) continue;
    const quantity = Math.min(row.quantity, 10 - (existing?.quantity || 0), 50 - count);
    if (quantity < 1) continue;
    if (existing) existing.quantity += quantity;
    else { const item = {product_id:row.product_id, quantity}; items.push(item); byId.set(item.product_id, item); }
    count += quantity;
  }
  const normalized = {version:1, items};
  if (JSON.stringify(normalized) !== JSON.stringify(data)) {
    notify('Корзина обновлена: недоступные товары удалены, количество приведено к лимитам.');
    persist(normalized);
  }
  return normalized;
}
export function writeCart(cart) {
  persist(cart); window.dispatchEvent(new Event('cart:changed'));
}
export const getItemCount = () => readCart().items.reduce((n, r) => n + r.quantity, 0);
export function addItem(productId, qty = 1) {
  if (products && !products.has(productId)) return false;
  const cart = readCart(), row = cart.items.find(r => r.product_id === productId);
  if (!Number.isInteger(qty) || qty < 1 || (row?.quantity || 0) + qty > 10 || getItemCount() + qty > 50 || (!row && cart.items.length >= 15)) {
    notify('Лимит: 10 штук одного товара и 50 вещей в корзине. Даже воображению нужен отдых.'); return false;
  }
  if (row) row.quantity += qty; else cart.items.push({product_id:productId, quantity:qty});
  writeCart(cart); notify('Добавлено в корзину. Решение можно отложить.'); return true;
}
export function setQuantity(productId, qty) {
  const cart = readCart(), row = cart.items.find(r => r.product_id === productId);
  if (!row) return;
  if (!Number.isInteger(qty) || qty < 1 || qty > 10 || getItemCount() - row.quantity + qty > 50) {
    notify('Выберите от 1 до 10 штук, всего не больше 50.'); render(); return;
  }
  row.quantity = qty; writeCart(cart);
}
export const removeItem = id => writeCart({version:1, items:readCart().items.filter(r => r.product_id !== id)});
export const clearCart = () => writeCart({version:1, items:[]});
export function element(tag, text, className) {
  const el = document.createElement(tag); if (text !== undefined) el.textContent = text;
  if (className) el.className = className; return el;
}
function render() {
  document.querySelectorAll('[data-cart-count]').forEach(el => {el.textContent = getItemCount();});
  const view = document.querySelector('[data-cart-view]');
  if (!view || !products) return;
  const items = readCart().items;
  view.replaceChildren();
  const checkout = document.querySelector('#checkout-link'), form = document.querySelector('#checkout-form');
  if (checkout) checkout.hidden = !items.length;
  if (form && !form.dataset.submitted) form.hidden = !items.length;
  if (!items.length) {
    const empty = element('section', undefined, 'empty');
    empty.append(element('span', '🛒', 'empty-icon'), element('h2', 'Ваша корзина пока откладывает принятие решений'), element('p', 'Самое время найти что-нибудь совершенно необязательное.'));
    const link = element('a', 'Заглянуть в каталог', 'button'); link.href = '/'; empty.append(link); view.append(empty);
    return;
  }
  let total = 0;
  for (const item of items) {
    const p = products.get(item.product_id), row = element('article', undefined, 'cart-row');
    row.dataset.product = p.id;
    const art = element('span', p.emoji, 'cart-emoji'); art.setAttribute('aria-hidden','true');
    const info = element('div', undefined, 'cart-info'); info.append(element('h2', p.name), element('p', money(p.price_kopeks) + ' / шт.'));
    row.append(art, info);
    if (view.dataset.editable) {
      const controls = element('div', undefined, 'quantity');
      for (const [label, delta] of [['−', -1], ['+', 1]]) {
        const button = element('button', label); button.type = 'button'; button.setAttribute('aria-label', (delta < 0 ? 'Уменьшить: ' : 'Увеличить: ') + p.name);
        button.disabled = delta < 0 ? item.quantity <= 1 : item.quantity >= 10 || getItemCount() >= 50;
        button.addEventListener('click', () => {setQuantity(p.id, item.quantity + delta); focusControl(p.id, button.getAttribute('aria-label'));});
        if (delta > 0) {
          const input = element('input'); input.type = 'number'; input.min = 1; input.max = 10; input.value = item.quantity;
          input.setAttribute('aria-label', 'Количество: ' + p.name);
          input.addEventListener('change', () => {setQuantity(p.id, Number(input.value)); focusControl(p.id, input.getAttribute('aria-label'));});
          controls.append(input);
        }
        controls.append(button);
      }
      row.append(controls);
      const remove = element('button', 'Удалить', 'text-button'); remove.type = 'button'; remove.setAttribute('aria-label', 'Удалить: ' + p.name); remove.addEventListener('click', () => removeItem(p.id)); row.append(remove);
    } else row.append(element('span', item.quantity + ' шт.'));
    row.append(element('strong', money(p.price_kopeks * item.quantity), 'line-total')); total += p.price_kopeks * item.quantity;
    view.append(row);
  }
  const sum = element('div', undefined, 'cart-total');
  sum.append(element('span', getItemCount() + ' шт. · ' + items.length + ' поз.'), element('strong', 'Итого: ' + money(total))); view.append(sum);
}
function focusControl(id, label) {
  const row = [...document.querySelectorAll('.cart-row')].find(el => el.dataset.product === id);
  const target = row && [...row.querySelectorAll('[aria-label]')].find(el => el.getAttribute('aria-label') === label);
  target?.focus();
}
window.addEventListener('cart:changed', render);
window.addEventListener('storage', event => {if (event.key === KEY || event.key === null) window.dispatchEvent(new Event('cart:changed'));});
render();
export async function loadCatalog() {
  try {
    const data = await getCatalog(); products = new Map(data.products.map(p => [p.id,p])); render();
    window.dispatchEvent(new Event('catalog:ready')); return true;
  } catch (error) {
    const view = document.querySelector('[data-cart-view]');
    if (view) {
      view.replaceChildren(element('p', error.message));
      const retry = element('button', 'Повторить загрузку', 'button'); retry.addEventListener('click', loadCatalog); view.append(retry);
    } else notify(error.message);
    return false;
  }
}
export const ready = loadCatalog();
export const hasCatalog = () => products !== null;
