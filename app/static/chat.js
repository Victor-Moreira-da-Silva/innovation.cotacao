const form = document.querySelector('#chat-form');
const chat = document.querySelector('#chat');
if (form) form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const text = data.get('mensagem');
  chat.insertAdjacentHTML('beforeend', `<div class="msg usuario"><strong>usuario:</strong> ${text}</div>`);
  const resp = await fetch(`${location.pathname}/chat`, { method: 'POST', body: data });
  const json = await resp.json();
  chat.insertAdjacentHTML('beforeend', `<div class="msg sistema"><strong>sistema:</strong> ${json.resposta}</div>`);
  form.reset();
  if (json.status === 'adicionado') setTimeout(() => location.reload(), 700);
});
