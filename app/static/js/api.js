async function request(url, options = {}) {
  let response;
  try { response = await fetch(url, {cache: 'no-store', ...options, signal: AbortSignal.timeout(15000)}); }
  catch { throw new Error('Не удалось связаться с магазином. Проверьте соединение и попробуйте ещё раз.'); }
  let data;
  try { data = await response.json(); }
  catch { throw new Error('Магазин ответил неожиданно. Попробуйте ещё раз.'); }
  if (!response.ok) throw new Error(data.error?.message || 'Не удалось выполнить запрос.');
  return data;
}
export const getCatalog = () => request('/api/catalog');
export const createOrder = payload => request('/api/orders', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
export const getTracking = token => request('/api/orders/' + encodeURIComponent(token) + '/tracking');
