// static/js/app.js
import { initAuth } from './auth.js';
import { showTab } from './ui.js';
import { 
  loadStats, 
  fetchQueueEmails, 
  processAllBackground, 
  generateTestReply, 
  loadHistory,
  saveConfigHandler 
} from './dashboard.js';

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize user sessions
  await initAuth();
  
  // Set default tab
  showTab('dashboard');

  // React to workspace changes globally
  window.addEventListener('workspaceChanged', () => {
    // Re-verify the current tab and force reload
    const currentTab = document.querySelector('.nav-item.active')?.dataset.tab || 'dashboard';
    showTab(currentTab);
  });

  // Navigation Logic
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => {
      if (el.dataset.tab) {
         showTab(el.dataset.tab);
      }
    });
  });

  window.addEventListener('tabChanged', (e) => {
    if (e.detail.tab === 'dashboard') loadStats();
    if (e.detail.tab === 'history') loadHistory();
    // queue is manually fetched via button to prevent spamming
  });

  // Action Button Bindings
  document.getElementById('btn-fetch-emails')?.addEventListener('click', fetchQueueEmails);
  document.getElementById('qa-fetch')?.addEventListener('click', fetchQueueEmails);
  document.getElementById('q-refresh')?.addEventListener('click', fetchQueueEmails);

  document.getElementById('btn-auto-process')?.addEventListener('click', processAllBackground);
  document.getElementById('qa-process')?.addEventListener('click', processAllBackground);

  document.getElementById('qa-compose')?.addEventListener('click', () => showTab('compose'));
  document.getElementById('btn-generate-reply')?.addEventListener('click', generateTestReply);

  // Config Saving
  document.getElementById('btn-save-config')?.addEventListener('click', saveConfigHandler);
  
  // Quick slider label update
  const confSlider = document.getElementById('cfg-confidence');
  if (confSlider) {
    confSlider.addEventListener('input', function() {
        document.getElementById('conf-val').textContent = Math.round(this.value * 100) + '%';
    });
  }

  // History filters
  document.querySelectorAll('.filter-select').forEach(sel => {
      sel.addEventListener('change', loadHistory);
  });
});
