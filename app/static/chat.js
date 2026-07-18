const form = document.querySelector('#chat-form');
const chat = document.querySelector('#chat');

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
    .replaceAll('\n', '<br>');
}

if (form) form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const text = data.get('mensagem');
  chat.insertAdjacentHTML('beforeend', `<div class="msg usuario"><strong>usuario:</strong> ${escapeHtml(text)}</div>`);
  const resp = await fetch(`${location.pathname}/chat`, { method: 'POST', body: data });
  const json = await resp.json();
  chat.insertAdjacentHTML('beforeend', `<div class="msg sistema"><strong>sistema:</strong> ${escapeHtml(json.resposta)}</div>`);
  form.reset();
  if (['adicionado', 'editado', 'removido', 'finalizada'].includes(json.status)) setTimeout(() => location.reload(), 700);
});