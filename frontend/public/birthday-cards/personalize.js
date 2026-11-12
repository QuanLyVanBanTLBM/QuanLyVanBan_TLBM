(() => {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
  if (!token) return;

  // Remove the token before this page loads its animation scripts.
  history.replaceState(null, '', window.location.pathname);
  const data = fetch('/api/birthdays/card/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  }).then(async (response) => response.ok ? (await response.json()).card : null)
    .catch(() => null);

  document.addEventListener('DOMContentLoaded', async () => {
    const card = await data;
    if (!card) {
      const status = document.createElement('p');
      status.setAttribute('role', 'status');
      status.textContent = 'Liên kết thiệp không hợp lệ hoặc đã hết hạn.';
      document.body.prepend(status);
      return;
    }

    for (const field of document.querySelectorAll('[data-card-field]')) {
      const value = card[field.dataset.cardField];
      if (typeof value === 'string') field.textContent = value;
    }
  });
})();
