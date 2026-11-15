import './cart.js';
document.querySelector('#print-receipt').addEventListener('click', () => window.print());
document.querySelector('#copy-link').addEventListener('click', async () => {
  const field = document.querySelector('#tracking-url'), message = document.querySelector('#copy-message');
  try {await navigator.clipboard.writeText(field.value); message.textContent = 'Ссылка скопирована.';}
  catch {field.focus(); field.select(); message.textContent = 'Скопируйте выделенную ссылку вручную.';}
});
