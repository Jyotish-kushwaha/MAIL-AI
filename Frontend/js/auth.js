// static/js/auth.js
import { API } from './api.js';
import { notify } from './ui.js';

export async function initAuth() {
  // Handle OAuth callback URL parameter if returning from Google
  const urlParams = new URLSearchParams(window.location.search);
  const authCallbackEmail = urlParams.get('user_email');
  if (authCallbackEmail) {
    localStorage.setItem('activeUser', authCallbackEmail);
    window.history.replaceState({}, document.title, "/dashboard");
    notify(`Logged in as ${authCallbackEmail}`, 'success');
  }

  const selector = document.getElementById('user-selector');
  try {
    const data = await API.request('/users');
    const users = data.users || [];
    
    if (users.length === 0) {
      selector.innerHTML = '<option value="">No accounts connected</option>';
      localStorage.removeItem('activeUser');
    } else {
      selector.innerHTML = users.map(u => `<option value="${u}">${u}</option>`).join('');
      let active = localStorage.getItem('activeUser');
      if (!active || !users.includes(active)) {
        active = users[0]; // default to first
        localStorage.setItem('activeUser', active);
      }
      selector.value = active;
    }
  } catch (e) {
    selector.innerHTML = '<option value="">Error loading users</option>';
    console.error("Failed to load users", e);
  }

  // Handle active workspace switching
  selector.addEventListener('change', (e) => {
    if (e.target.value) {
      localStorage.setItem('activeUser', e.target.value);
      notify(`Switched to workspace: ${e.target.value}`, 'success');
      window.dispatchEvent(new Event('workspaceChanged'));
    }
  });

  // Handle add account button
  document.getElementById('btn-add-account').addEventListener('click', async () => {
    try {
      // Temporary bypass activeUser requirement just to fetch the generic URL
      const res = await fetch('/auth/gmail');
      const data = await res.json();
      if (data.auth_url && data.auth_url.startsWith('http')) {
        window.location.href = data.auth_url;
      } else {
        notify(data.auth_url || 'Could not find redirect URL', 'error');
      }
    } catch (e) {
      notify('Failed to connect to Google Auth', 'error');
    }
  });
}
