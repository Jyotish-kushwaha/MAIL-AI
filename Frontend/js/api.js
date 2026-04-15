const BASE_URL = "mail-ai-production.up.railway.app";

export class API {
  static get userEmail() {
    return localStorage.getItem('activeUser') || '';
  }

  static async request(path, opts = {}) {
    const email = this.userEmail;
    let url = BASE_URL + path;

    if (email) {
      const sep = url.includes('?') ? '&' : '?';
      url += `${sep}user_email=${encodeURIComponent(email)}`;
    }

    const res = await fetch(url, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {})
      }
    });

    if (res.status === 204) return null;

    if (!res.ok) {
      let errDetail = `${res.status}`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch (e) {}
      throw new Error(errDetail);
    }

    return res.json();
  }
}