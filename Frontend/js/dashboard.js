// static/js/dashboard.js
import { API } from './api.js';
import { loading, notify, avatarColor, initials, formatTime, escHtml, openModal, closeModal } from './ui.js';

let emailQueue = [];
let currentEmailId = null;
const config = { tone: 'professional', auto_send: false, confidence_threshold: 0.75, max_emails_per_run: 10 };

export async function loadStats() {
  if (!API.userEmail) {
    document.getElementById('recent-list').innerHTML = '<div class="empty"><div class="empty-text">Select a workspace</div></div>';
    document.getElementById('cat-chart').innerHTML = '<div class="empty"><div class="empty-text">No workspace selected</div></div>';
    return;
  }
  try {
    const stats = await API.request('/dashboard/stats');
    document.getElementById('stat-total').textContent = stats.total_processed;
    document.getElementById('stat-sent').textContent = stats.sent;
    document.getElementById('stat-pending').textContent = stats.pending_review;
    document.getElementById('stat-drafts').textContent = stats.drafts;
    document.getElementById('stat-conf').textContent = stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(0) + '%' : '—';

    const cats = stats.categories || {};
    const total = Object.values(cats).reduce((a, b) => a + b, 0) || 1;
    const colors = { complaint:'var(--red)', inquiry:'var(--accent)', feedback:'var(--purple)',
                     request:'var(--teal)', billing:'var(--amber)', technical_support:'var(--accent2)',
                     refund:'var(--coral)', other:'var(--muted)' };
    const container = document.getElementById('cat-chart');
    if (total === 1 && Object.keys(cats).length === 0) {
      container.innerHTML = '<div class="empty"><div class="empty-text">No data yet</div></div>';
    } else {
      container.innerHTML = Object.entries(cats).sort((a,b) => b[1]-a[1]).map(([cat, cnt]) => `
        <div class="cat-bar">
          <div class="cat-bar-header">
            <span class="cat-bar-label">${cat}</span>
            <span class="cat-bar-count">${cnt}</span>
          </div>
          <div class="cat-bar-track">
            <div class="cat-bar-fill" style="width:${(cnt/total*100).toFixed(0)}%;background:${colors[cat]||'var(--muted)'}"></div>
          </div>
        </div>`).join('');
    }

    const history = await API.request('/dashboard/history?limit=6');
    renderHistoryList(history, 'recent-list', true);
    document.getElementById('history-updated').textContent = 'Updated just now';
  } catch (e) {
    console.warn("Could not load stats yet.");
  }
}

export async function fetchQueueEmails() {
  if (!API.userEmail) return notify('Please select a workspace', 'warn');
  loading(true);
  try {
    const data = await API.request('/emails/fetch?max_results=20');
    emailQueue = data.emails || [];
    document.getElementById('queue-count').textContent = emailQueue.length;
    renderQueue();
    notify(`Fetched ${emailQueue.length} unread emails`, 'success');
  } catch (e) {
    notify('Failed to fetch emails.', 'error');
  } finally {
    loading(false);
  }
}

function renderQueue() {
  const container = document.getElementById('queue-list');
  if (!emailQueue.length) {
    container.innerHTML = '<div class="empty"><div class="empty-icon">📬</div><div class="empty-text">No emails in queue</div></div>';
    return;
  }
  container.innerHTML = emailQueue.map(e => `
    <div class="email-item" data-id="${e.id}">
      <div class="email-avatar" style="background:${avatarColor(e.from)};color:#fff">${initials(e.from)}</div>
      <div class="email-body">
        <div class="email-from">${escHtml(e.from)}</div>
        <div class="email-subject">${escHtml(e.subject)}</div>
        <div class="email-snippet">${escHtml(e.snippet || e.body?.slice(0,80) || '')}</div>
      </div>
      <div class="email-meta">
        <div class="email-time">${formatTime(e.date)}</div>
        <button class="btn primary btn-process-single" data-id="${e.id}" style="font-size:11px;padding:4px 10px;margin-top:6px">Process</button>
      </div>
    </div>`).join('');

  container.querySelectorAll('.email-item').forEach(el => {
      el.addEventListener('click', (e) => {
          if(!e.target.classList.contains('btn-process-single')) openQueueItemModal(el.dataset.id);
      });
  });
  container.querySelectorAll('.btn-process-single').forEach(btn => {
      btn.addEventListener('click', (e) => {
          e.stopPropagation();
          processSingleEmail(btn.dataset.id);
      });
  });
}

async function processSingleEmail(emailId) {
  loading(true);
  try {
    const cfg = getConfigOptions();
    const result = await API.request(`/emails/process/${emailId}`, {
      method: 'POST',
      body: JSON.stringify(cfg)
    });

    if (result.status === 'draft_saved' || result.status === 'pending_review') {
      const reply = result.reply || result.draft || {};
      const email = emailQueue.find(e => e.id === emailId);
      const body = `
        <div style="margin-bottom:10px">
          <span class="tag tag-${result.category||'other'}">${result.category||'other'}</span>
          <span style="font-size:11px;color:var(--muted);margin-left:8px">${result.status}</span>
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:4px">Original Email</div>
        <div class="email-original">${escHtml(email?.body||email?.snippet||'')}</div>
        <div style="font-size:12px;color:var(--muted);margin:12px 0 6px">AI Generated Reply</div>
        <div class="reply-preview">
          <div class="reply-subject">📧 ${escHtml(reply.subject||'')}</div>
          <div class="reply-body">${escHtml(reply.body||'')}</div>
        </div>`;
      const footer = `
        <button class="btn btn-close-modal">Cancel</button>
        <button class="btn primary btn-modal-send-draft" data-id="${emailId}">✉ Send Reply</button>`;

      openModal(email?.subject || 'Draft Reply', body, footer);
      document.querySelector('.btn-close-modal').addEventListener('click', closeModal);
      document.querySelector('.btn-modal-send-draft').addEventListener('click', async () => {
        loading(true);
        try {
          await API.request(`/emails/approve/${emailId}`, { method: 'POST' });
          notify('Reply sent!', 'success');
          closeModal();
          emailQueue = emailQueue.filter(e => e.id !== emailId);
          renderQueue();
          await loadStats();
        } catch (e) { notify('Failed to send', 'error'); }
        finally { loading(false); }
      });
    } else {
      notify(`Email ${result.status}: ${result.category || ''}`, result.status === 'sent' ? 'success' : 'warn');
      emailQueue = emailQueue.filter(e => e.id !== emailId);
      renderQueue();
    }
    await loadStats();
  } catch (e) {
    notify('Processing failed', 'error');
  } finally {
    loading(false);
  }
}

export async function processAllBackground() {
  if (!API.userEmail) return notify('Please select a workspace', 'warn');
  loading(true);
  try {
    const cfg = getConfigOptions();
    await API.request('/emails/auto-process', { method: 'POST', body: JSON.stringify(cfg) });
    notify('Background processing started for all users', 'info');
    setTimeout(loadStats, 3000);
  } catch (e) {
    notify('Auto-process failed.', 'error');
  } finally {
    loading(false);
  }
}

export async function generateTestReply() {
  const emailText = document.getElementById('compose-email').value.trim();
  const tone = document.getElementById('compose-tone').value;
  if (!emailText) return notify('Enter email text first', 'warn');

  loading(true);
  try {
    const result = await API.request('/generate-reply', {
      method: 'POST',
      body: JSON.stringify({ email_text: emailText, tone })
    });

    document.getElementById('reply-meta').innerHTML = `
      <span class="tag tag-${result.category}">${result.category}</span>
      <span class="status status-sent" style="font-size:10px">${(result.confidence*100).toFixed(0)}% conf</span>`;

    document.getElementById('compose-result').innerHTML = `
      <div class="reply-preview">
        <div class="reply-subject">📧 ${escHtml(result.subject)}</div>
        <div class="reply-body">${escHtml(result.body)}</div>
      </div>`;
    notify('Reply generated', 'success');
  } catch (e) { notify('Failed to generate reply', 'error'); }
  finally { loading(false); }
}

export async function loadHistory() {
  if (!API.userEmail) return;
  const status = document.getElementById('filter-status')?.value || '';
  const category = document.getElementById('filter-category')?.value || '';
  let path = '/dashboard/history?limit=50';
  if (status) path += `&status=${status}`;
  if (category) path += `&category=${category}`;

  try {
    const data = await API.request(path);
    renderHistoryList(data, 'history-list', false);
  } catch (e) {}
}

function renderHistoryList(items, containerId, compact) {
  const container = document.getElementById(containerId);
  if (!items.length) {
    container.innerHTML = '<div class="empty"><div class="empty-icon">📋</div><div class="empty-text">No records found</div></div>';
    return;
  }
  container.innerHTML = items.map(item => `
    <div class="email-item" data-historyid="${item.id}">
      <div class="email-avatar" style="background:${avatarColor(item.from_address||'')};color:#fff">${initials(item.from_address||'?')}</div>
      <div class="email-body">
        <div class="email-from">${escHtml(item.from_address||'Unknown')}</div>
        <div class="email-subject">${escHtml(item.subject||'(no subject)')}</div>
        ${compact ? '' : `<div class="email-snippet">${escHtml((item.reply_body||'').slice(0,80))}</div>`}
      </div>
      <div class="email-meta">
        <div class="email-time">${formatTime(item.processed_at)}</div>
        <div style="margin-top:4px">
          <span class="tag tag-${item.category||'other'}">${item.category||'other'}</span>
        </div>
        <div style="margin-top:4px">
          <span class="status status-${item.status||'error'}">${item.status}</span>
        </div>
      </div>
    </div>`).join('');

  container.querySelectorAll('.email-item').forEach(el => {
      el.addEventListener('click', () => openHistoryModal(el.dataset.historyid));
  });
}

function openQueueItemModal(emailId) {
  const email = emailQueue.find(e => e.id === emailId);
  if (!email) return;
  currentEmailId = emailId;
  const body = `
    <div style="margin-bottom:12px">
      <div style="font-size:12px;color:var(--muted);margin-bottom:4px">From</div>
      <div style="font-size:13px">${escHtml(email.from)}</div>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:6px">Email content</div>
    <div class="email-original">${escHtml(email.body||email.snippet||'')}</div>`;
  const footer = `
    <button class="btn btn-close-modal">Cancel</button>
    <button class="btn primary btn-modal-process">Process & Reply</button>`;

  openModal(email.subject || '(no subject)', body, footer);
  document.querySelector('.btn-close-modal').addEventListener('click', closeModal);
  document.querySelector('.btn-modal-process').addEventListener('click', () => {
      processSingleEmail(emailId);
      closeModal();
  });
}

async function openHistoryModal(emailId) {
  try {
    const items = await API.request(`/dashboard/history?limit=100`);
    const item = items.find(i => i.id === emailId);
    if (!item) return;

    const body = `
      <div style="display:flex;gap:8px;margin-bottom:14px">
        <span class="tag tag-${item.category||'other'}">${item.category}</span>
        <span class="status status-${item.status}">${item.status}</span>
        ${item.confidence ? `<span style="font-size:11px;color:var(--muted);font-family:'DM Mono',monospace">${(item.confidence*100).toFixed(0)}% confidence</span>` : ''}
      </div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:4px">Original email</div>
      <div class="email-original">${escHtml(item.email_body||'')}</div>
      <div style="font-size:12px;color:var(--muted);margin:12px 0 6px">AI Generated Reply</div>
      <div class="reply-preview">
        <div class="reply-subject">📧 ${escHtml(item.reply_subject||'')}</div>
        <div class="reply-body">${escHtml(item.reply_body||'')}</div>
      </div>`;

    let footer = `<button class="btn btn-close-modal">Close</button>`;
    if (item.status === 'pending_review' || item.status === 'draft') {
      footer += `<button class="btn primary btn-modal-approve">✉ Send Reply</button>`;
    }

    openModal(item.subject || '(no subject)', body, footer);
    document.querySelector('.btn-close-modal').addEventListener('click', closeModal);

    const approveBtn = document.querySelector('.btn-modal-approve');
    if (approveBtn) {
        approveBtn.addEventListener('click', async () => {
            loading(true);
            try {
              await API.request(`/emails/approve/${emailId}`, { method: 'POST' });
              notify('Email approved and sent!', 'success');
              closeModal();
              loadStats();
              if (document.getElementById('tab-history').style.display === 'block') loadHistory();
            } catch (e) { notify('Failed to send', 'error'); }
            finally { loading(false); }
        });
    }
  } catch(e) {}
}

export function getConfigOptions() {
  return {
    tone: document.getElementById('cfg-tone')?.value || 'professional',
    auto_send: document.getElementById('cfg-auto-send')?.checked || false,
    confidence_threshold: parseFloat(document.getElementById('cfg-confidence')?.value || 0.75),
    max_emails_per_run: parseInt(document.getElementById('cfg-max-emails')?.value || 10)
  };
}

export function saveConfigHandler() {
  Object.assign(config, getConfigOptions());
  notify('Settings saved', 'success');
}