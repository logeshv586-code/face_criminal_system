import axios from 'axios';

const getToken = () => {
  let token = sessionStorage.getItem('auth_token');
  if (!token) {
    const legacy = localStorage.getItem('auth_token');
    if (legacy) {
      sessionStorage.setItem('auth_token', legacy);
      localStorage.removeItem('auth_token');
      token = legacy;
    }
  }
  return token;
};

const isBackendRequest = (value) => {
  const url = typeof value === 'string' ? value : value?.url || '';
  return url.includes('/api/') || url.includes('/capture_face_');
};

(function installFetchShim() {
  const originalFetch = window.fetch.bind(window);
  window.fetch = async function(input, options = {}) {
    const token = getToken();
    if (token && isBackendRequest(input)) {
      const existing = options.headers instanceof Headers
        ? Object.fromEntries(options.headers.entries())
        : (options.headers || {});
      return originalFetch(input, {
        ...options,
        headers: { ...existing, Authorization: `Bearer ${token}` },
      });
    }
    return originalFetch(input, options);
  };
})();

axios.interceptors.request.use((config) => {
  const token = getToken();
  if (token && isBackendRequest(config?.url || '')) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

axios.interceptors.response.use((response) => response, (error) => {
  if (error?.response?.status === 401) {
    sessionStorage.removeItem('auth_token');
    localStorage.removeItem('auth_token');
  }
  return Promise.reject(error);
});

export const apiRequest = async (url, options = {}) => {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token && isBackendRequest(url)) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail || `HTTP error ${response.status}`);
  }
  return response.json();
};

export const getAuthHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export { getToken };
