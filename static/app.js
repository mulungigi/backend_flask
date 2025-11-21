async function showAlert(msg, type='info') {
  const alerts = document.getElementById('alerts');
  const div = document.createElement('div');
  div.className = `alert alert-${type} alert-dismissible`;
  div.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
  alerts.appendChild(div);
  setTimeout(() => { try { div.remove(); } catch(e){} }, 8000);
}

async function updateRates() {
  const btn = document.getElementById('btn-update');
  btn.disabled = true;
  btn.textContent = 'Обновление...';
  try {
    const resp = await fetch('/api/update_rates', { method: 'POST' });
    const j = await resp.json();
    if (resp.ok) {
      showAlert('Курсы успешно обновлены', 'success');
      document.getElementById('last-update').textContent = 'Обновлено: ' + j.updated;
    } else {
      showAlert('Ошибка обновления: ' + (j.message || resp.statusText), 'danger');
    }
  } catch (e) {
    showAlert('Сетевая ошибка: ' + e.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Обновить курсы (из API)';
  }
}

async function getLastUpdate() {
  try {
    const resp = await fetch('/api/last_update');
    const j = await resp.json();
    if (resp.ok) {
      document.getElementById('last-update').textContent = 'Обновлено: ' + j.timestamp + ' (base: ' + j.base + ')';
    } else {
      document.getElementById('last-update').textContent = 'Курсы не загружены';
    }
  } catch (e) {
    document.getElementById('last-update').textContent = 'Ошибка получения времени обновления';
  }
}

document.getElementById('btn-update').addEventListener('click', (e) => {
  e.preventDefault();
  updateRates();
});

document.getElementById('convert-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const amount = document.getElementById('amount').value;
  const from = document.getElementById('from').value.trim().toUpperCase();
  const to = document.getElementById('to').value.trim().toUpperCase();

  if (!from || !to) {
    showAlert('Укажите коды валют', 'warning');
    return;
  }

  try {
    const resp = await fetch('/api/convert', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ from, to, amount })
    });
    const j = await resp.json();
    const pre = document.getElementById('result');
    if (resp.ok) {
      pre.textContent = `${j.amount} ${j.from} = ${j.result} ${j.to}\n(курсы взяты ${j.rates_timestamp}, base: ${j.base})`;
    } else {
      pre.textContent = 'Ошибка: ' + (j.message || 'Unknown');
      showAlert('Ошибка: ' + (j.message || 'Unknown'), 'danger');
    }
  } catch (e) {
    showAlert('Сетевая ошибка: ' + e.message, 'danger');
  }
});

window.addEventListener('load', () => {
  getLastUpdate();
});
