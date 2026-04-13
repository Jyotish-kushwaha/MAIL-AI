// static/js/api.js

export class API {
  static get userEmail() {
    return localStorage.getItem('activeUser') || '';
  }

  static async request(path, opts = {}) {
    let url = path;
    const email = this.userEmail;
    
    // Automatically inject active workspace parameter
    if (email) {
      const sep = url.includes('?') ? '&' : '?';
      url += `${sep}user_email=${encodeURIComponent(email)}`;
    }
    
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    
    // Attempt parsing JSON errors if possible
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
