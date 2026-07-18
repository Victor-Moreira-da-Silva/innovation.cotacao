const form = document.querySelector('#chat-form');
const chat = document.querySelector('#chat');
const itensBody = document.querySelector('#itens-proposta tbody');
const totalProposta = document.querySelector('#total-proposta');
const statusProposta = document.querySelector('#status-proposta');

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
    .replaceAll('\n', '<br>');
}

function formatCurrency(value) {
  const number = Number(value || 0);
  return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function renderItens(itens = [], total = 0) {
  if (!itensBody) return;

  if (!itens.length) {
    itensBody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">Nenhum item adicionado.</td></tr>';
  } else {
    itensBody.innerHTML = itens.map((item) => `
      <tr>
        <td>${escapeHtml(item.quantidade)}</td>
        <td>${escapeHtml(item.produto)}</td>
        <td>${formatCurrency(item.valor_unitario)}</td>
        <td>${formatCurrency(item.valor_total)}</td>
      </tr>
    `).join('');
  }

  if (totalProposta) totalProposta.textContent = formatCurrency(total);
}

if (form) form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const text = data.get('mensagem');
  chat.insertAdjacentHTML('beforeend', `<div class="msg usuario"><strong>usuario:</strong> ${escapeHtml(text)}</div>`);
  const resp = await fetch(`${location.pathname}/chat`, { method: 'POST', body: data });
  const json = await resp.json();
  chat.insertAdjacentHTML('beforeend', `<div class="msg sistema"><strong>sistema:</strong> ${escapeHtml(json.resposta)}</div>`);
  chat.scrollTop = chat.scrollHeight;
  form.reset();

  if (json.itens) renderItens(json.itens, json.valor_total);
  if (json.status_proposta && statusProposta) statusProposta.textContent = json.status_proposta;
});