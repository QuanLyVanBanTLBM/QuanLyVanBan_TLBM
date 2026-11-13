(() => {
  const optionalFieldStyle = document.createElement('style');
  optionalFieldStyle.textContent = '[data-card-optional][hidden] { display: none !important; }';
  document.head.append(optionalFieldStyle);

  const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
  if (!token) return;

  // Remove the token before this page loads its animation scripts.
  history.replaceState(null, '', window.location.pathname);
  const data = fetch('/api/birthdays/card/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  }).then(async (response) => {
    if (!response.ok) {
      console.warn(`[birthday-card] Personalization API returned HTTP ${response.status}.`);
      return null;
    }
    const payload = await response.json();
    if (!payload || typeof payload.card !== 'object' || payload.card === null) {
      console.error('[birthday-card] Personalization API returned an invalid card payload.');
      return null;
    }
    return payload.card;
  }).catch((error) => {
    console.error('[birthday-card] Personalization request failed.', error);
    return null;
  });

  function showStatus() {
    const status = document.createElement('p');
    status.dataset.cardStatus = 'error';
    status.setAttribute('role', 'status');
    status.textContent = 'Liên kết thiệp không hợp lệ hoặc đã hết hạn.';
    Object.assign(status.style, {
      position: 'fixed',
      top: 'max(0.75rem, env(safe-area-inset-top))',
      left: '50%',
      transform: 'translateX(-50%)',
      width: 'calc(100vw - 1.5rem)',
      maxWidth: '32rem',
      boxSizing: 'border-box',
      margin: '0',
      padding: '0.75rem 1rem',
      borderRadius: '0.75rem',
      background: 'rgba(7, 20, 43, 0.92)',
      color: '#ffffff',
      font: '600 0.875rem/1.4 system-ui, sans-serif',
      textAlign: 'center',
      zIndex: '1000',
      overflowWrap: 'anywhere',
    });
    document.body.append(status);
  }

  document.addEventListener('DOMContentLoaded', async () => {
    const card = await data;
    if (!card) {
      showStatus();
      return;
    }

    for (const field of document.querySelectorAll('[data-card-field]')) {
      const value = card[field.dataset.cardField];
      if (typeof value === 'string') field.textContent = value;
    }

    for (const optional of document.querySelectorAll('[data-card-optional]')) {
      const value = card[optional.dataset.cardOptional];
      const isEmpty = typeof value !== 'string' || !value.trim();
      optional.hidden = isEmpty;
      optional.style.display = isEmpty ? 'none' : '';
    }
  });
})();
