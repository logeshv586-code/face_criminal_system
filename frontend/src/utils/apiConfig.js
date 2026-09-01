// Runtime API endpoint configuration for browser development and packaged Electron builds.
const normalizeApiBaseUrl = (value) => {
  if (!value) return null;
  const raw = String(value).trim().replace(/\/$/, '');
  if (!raw) return null;
  const candidate = /^https?:\/\//i.test(raw) ? raw : `http://${raw}:8005`;
  try {
    const parsed = new URL(candidate);
    if (!['http:', 'https:'].includes(parsed.protocol)) return null;
    return parsed.origin + (parsed.pathname === '/' ? '' : parsed.pathname.replace(/\/$/, ''));
  } catch (_) {
    return null;
  }
};

const getApiBaseUrl = () => {
  const configured = normalizeApiBaseUrl(process.env.REACT_APP_API_BASE_URL);
  if (configured) return configured;

  const savedUrl = normalizeApiBaseUrl(localStorage.getItem('api_base_url'));
  if (savedUrl) return savedUrl;

  const hostname = window.location?.hostname;
  if (hostname && hostname !== 'localhost') return `http://${hostname}:8005`;
  return 'http://127.0.0.1:8005';
};

export const API_BASE_URL = getApiBaseUrl();

export const saveApiBaseUrl = async (value) => {
  const normalized = normalizeApiBaseUrl(value);
  if (!normalized) throw new Error('Enter a valid backend address or IP.');
  localStorage.setItem('api_base_url', normalized);
  if (window?.electronAPI?.setApiBaseUrl) {
    try { await window.electronAPI.setApiBaseUrl(normalized); } catch (_) { /* renderer setting still works */ }
  }
  return normalized;
};

export const getAugmentUrl = (endpoint = '') => {
  const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  return endpoint ? `${base}/${String(endpoint).replace(/^\//, '')}` : base;
};

export const getApiUrl = (endpoint = '') => `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

export const fixImageUrl = (url) => {
  if (!url) return '';
  const currentApiUrl = API_BASE_URL.replace(/\/$/, '');
  if (url.startsWith('/')) return `${currentApiUrl}${url}`;
  if (/^http:\/\/(localhost|127\.0\.0\.1):\d+/i.test(url)) {
    return url.replace(/^http:\/\/(localhost|127\.0\.0\.1):\d+/i, currentApiUrl);
  }
  return url;
};

export const detectBackendUrl = async () => {
  const hostname = window.location?.hostname;
  const candidates = [
    normalizeApiBaseUrl(localStorage.getItem('api_base_url')),
    hostname && !['localhost', ''].includes(hostname) ? `http://${hostname}:8005` : null,
    'http://127.0.0.1:8005',
    'http://localhost:8005',
  ].filter(Boolean);

  for (const url of [...new Set(candidates)]) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);
      const response = await fetch(`${url}/api/status`, { method: 'GET', signal: controller.signal });
      clearTimeout(timeout);
      if (response.ok) return url;
    } catch (_) { /* try next candidate */ }
  }
  return null;
};

export { normalizeApiBaseUrl };
export default { API_BASE_URL, saveApiBaseUrl, getAugmentUrl, getApiUrl, fixImageUrl, detectBackendUrl };
