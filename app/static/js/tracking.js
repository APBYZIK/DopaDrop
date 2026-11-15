import {getTracking} from './api.js';
import './cart.js';
const root = document.querySelector('#tracking'), message = document.querySelector('#tracking-message');
let final = root.dataset.final === 'true', timer = null, running = false;
function stop() {clearTimeout(timer); timer = null;}
function schedule() {stop(); if (!final && !document.hidden) timer = setTimeout(refresh, 5000);}
async function refresh() {
  if (document.hidden || final || running) return;
  running = true;
  try {
    const data = await getTracking(root.dataset.token), state = data.tracking;
    final = state.is_final;
    const current = state.stages[state.current_stage_index], title = document.querySelector('#current-status');
    if (title.textContent !== current.title) {
      title.textContent = current.title; document.querySelector('#current-description').textContent = current.description;
      document.querySelector('#current-emoji').textContent = current.emoji;
    }
    for (const stage of state.stages) {
      const li = [...document.querySelectorAll('[data-stage]')].find(el => el.dataset.stage === stage.id);
      if (!li) continue;
      li.className = stage.state;
      li.querySelector('.stage-state').textContent = {complete:'Пройдено', current:'Сейчас', pending:'Впереди'}[stage.state];
      if (stage.state === 'current') li.setAttribute('aria-current','step'); else li.removeAttribute('aria-current');
    }
    message.textContent = final ? 'Приключение завершено. Воображение благодарит вас.' : 'Обновляется автоматически каждые 5 секунд.';
  } catch {message.textContent = 'Не удалось обновить. Попробуем ещё раз. Последний известный статус сохранён.';}
  finally {running = false; schedule();}
}
document.addEventListener('visibilitychange', () => {stop(); if (!document.hidden) refresh();});
window.addEventListener('pagehide', stop);
schedule();
