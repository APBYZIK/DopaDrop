import {addItem, ready} from './cart.js';
document.querySelectorAll('[data-add]').forEach(button => {
  button.addEventListener('click', async () => {
    await ready;
    if (addItem(button.dataset.add)) {
      button.textContent = 'Добавлено ✓'; setTimeout(() => {button.textContent = 'В корзину +';}, 1500);
    }
  });
});
document.querySelector('#category')?.addEventListener('change', event => event.target.form.requestSubmit());
