/**
 * CRM Centralized API Client
 * Automatically manages Authorization headers, error responses, and session redirection.
 */

const API_BASE = window.location.pathname.startsWith("/excel-crm") ? "/excel-crm" : "";
window.API_BASE = API_BASE;

class ApiClient {
  constructor() {
    this.token = localStorage.getItem("crm_token") || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem("crm_token", token);
    } else {
      localStorage.removeItem("crm_token");
    }
  }

  getHeaders(customHeaders = {}) {
    const headers = { ...customHeaders };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = this.getHeaders(options.headers || {});
    
    // Default credentials to include cookies
    const config = {
      ...options,
      headers,
      credentials: "include"
    };

    try {
      const response = await fetch(url, config);

      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.setToken(null);
        if (!window.location.pathname.includes("login.html") && !window.location.pathname.endsWith("/login")) {
          window.location.href = `${API_BASE}/login.html?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`;
        }
        throw new Error("Session expired or unauthorized. Redirecting to login...");
      }

      // Check if response is file download
      const contentType = response.headers.get("content-type");
      if (contentType && (contentType.includes("application/octet-stream") || contentType.includes("spreadsheetml"))) {
        return response.blob();
      }

      const data = await response.json();
      if (!response.ok) {
        const errorMsg = data.detail || (data.message ? data.message : "Request failed");
        throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
      }

      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  }

  get(endpoint, params = {}) {
    const cleanParams = {};
    for (const [k, v] of Object.entries(params || {})) {
      if (v !== undefined && v !== null && v !== "") {
        cleanParams[k] = v;
      }
    }
    const query = new URLSearchParams(cleanParams).toString();
    const url = query ? `${endpoint}?${query}` : endpoint;
    return this.request(url, { method: "GET" });
  }

  post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
  }

  put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  }

  upload(endpoint, formData) {
    return this.request(endpoint, {
      method: "POST",
      body: formData // Browser automatically sets multipart/form-data with boundary
    });
  }
}

window.api = new ApiClient();
