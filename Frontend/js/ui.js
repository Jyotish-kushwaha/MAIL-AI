// static/js/ui.js

export function loading(show) {
  document.getElementById('loading').classList.toggle('show', show);
}

export function notify(msg, type = 'info') {
  const colors = { success: 'var(--green)', error: 'var(--red)', info: 'var(--accent)', warn: 'var(--amber)' };
  document.getElementById('notif-dot').style.background = colors[type] || colors.info;
  document.getElementById('notif-text').textContent = msg;
  const el = document.getElementById('notif');
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3500);
}

export function showTab(name) {
  ['dashboard','queue','history','config','compose'].forEach(t => {
    const el = document.getElementById('tab-'+t);
    if (el) el.style.display = t === name ? 'block' : 'none';
  });
  document.querySelectorAll('.nav-item').forEach(el => {
    if (el.dataset.tab === name) el.classList.add('active');
    else el.classList.remove('active');
  });
  const titles = { dashboard: 'Dashboard', queue: 'Email Queue', history: 'Reply History', config: 'Configuration', compose: 'Test Compose' };
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = titles[name] || name;
  
  // Dispatch event so individual tabs can reload their data
  const event = new CustomEvent('tabChanged', { detail: { tab: name } });
  window.dispatchEvent(event);
}

export function escHtml(str) {
  return String(str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

export function initials(str) {
  const parts = (str||'?').split(/[@\s.]/);
  return parts.filter(Boolean).slice(0,2).map(p => p[0].toUpperCase()).join('') || '?';
}

const palette = ['#4f8ef7','#6366f1','#34d399','#fbbf24','#f87171','#a78bfa','#2dd4bf','#fb7185'];
export function avatarColor(str) {
  let h = 0;
  for (let i = 0; i < (str||'').length; i++) h = (h + str.charCodeAt(i)) % palette.length;
  return palette[h];
}

export function formatTime(str) {
  if (!str) return '—';
  const d = new Date(str);
  if (isNaN(d)) return str.slice(0,10);
  const diff = Date.now() - d;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return Math.floor(diff/60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff/3600000) + 'h ago';
  return d.toLocaleDateString();
}

export function openModal(title, bodyHtml, footerHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-footer').innerHTML = footerHtml;
  document.getElementById('email-modal').classList.add('show');
}

export function closeModal() {
  document.getElementById('email-modal').classList.remove('show');
}

// Global modal close event
document.getElementById('btn-modal-close')?.addEventListener('click', closeModal);
document.getElementById('email-modal')?.addEventListener('click', e => {
  if (e.target.id === 'email-modal') closeModal();
});
