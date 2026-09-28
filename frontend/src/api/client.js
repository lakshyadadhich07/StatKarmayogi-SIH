/**
 * StatKarmayogi API Client
 * Base URL: http://localhost:8000/api/v1
 * Auth:     JWT Bearer token stored in module-level memory, falls back to localStorage
 *           for persistence across refresh (acknowledged: not production-secure).
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '');
const API_ORIGIN = BASE_URL.replace(/\/api\/v1$/, '');

// In-memory token store (primary). localStorage used for refresh persistence.
let _token = localStorage.getItem('sk_token') || null;

export function setToken(token) {
  _token = token;
  if (token) {
    localStorage.setItem('sk_token', token);
  } else {
    localStorage.removeItem('sk_token');
  }
}

export function getToken() {
  return _token;
}

export function clearToken() {
  _token = null;
  localStorage.removeItem('sk_token');
  localStorage.removeItem('sk_user');
}

/**
 * Core fetch wrapper.
 * - Injects Authorization header when token is present.
 * - On 401: clears token and dispatches a custom 'auth:expired' event so the
 *   auth context can redirect to login without circular imports.
 * - Surfaces the backend's own error message (detail field) rather than
 *   replacing it with a generic string.
 */
async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
  };

  // Don't set Content-Type for FormData — let the browser set multipart boundary.
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (_token) {
    headers['Authorization'] = `Bearer ${_token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new Event('auth:expired'));
    const err = new Error('Session expired. Please log in again.');
    err.status = 401;
    throw err;
  }

  // For non-JSON responses (e.g. 204 No Content)
  if (response.status === 204) {
    return null;
  }

  let body;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    // Surface the backend's human-readable error message exactly as returned.
    const message =
      (body && (body.detail || body.message)) ||
      `HTTP ${response.status}: ${response.statusText}`;
    const err = new Error(message);
    err.status = response.status;
    err.body = body;
    throw err;
  }

  return body;
}

// ─────────────────────────────────────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────────────────────────────────────
export const api = {
  health: () => fetch(`${API_ORIGIN}/health`).then(r => r.json()),

  // ─── Auth ───────────────────────────────────────────────────────────────
  auth: {
    register: (payload) =>
      apiFetch('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),

    login: (email, password) =>
      apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    me: () => apiFetch('/auth/me'),
  },

  // ─── Documents ──────────────────────────────────────────────────────────
  documents: {
    upload: (file) => {
      const form = new FormData();
      form.append('file', file);
      return apiFetch('/documents', { method: 'POST', body: form });
    },

    list: (skip = 0, limit = 100) =>
      apiFetch(`/documents?skip=${skip}&limit=${limit}`),

    get: (id) => apiFetch(`/documents/${id}`),

    delete: (id) => apiFetch(`/documents/${id}`, { method: 'DELETE' }),

    search: (query, top_k = 5, document_id = null) =>
      apiFetch('/documents/search', {
        method: 'POST',
        body: JSON.stringify({ query, top_k, ...(document_id ? { document_id } : {}) }),
      }),
  },

  // ─── Questions ──────────────────────────────────────────────────────────
  questions: {
    generate: (payload) =>
      apiFetch('/questions/generate', { method: 'POST', body: JSON.stringify(payload) }),

    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, v);
      });
      return apiFetch(`/questions?${qs.toString()}`);
    },

    get: (id) => apiFetch(`/questions/${id}`),

    review: (id, action, comment = null) =>
      apiFetch(`/questions/${id}/review`, {
        method: 'POST',
        body: JSON.stringify({ action, ...(comment ? { comment } : {}) }),
      }),
  },

  // ─── Assessments ────────────────────────────────────────────────────────
  assessments: {
    create: (payload) =>
      apiFetch('/assessments', { method: 'POST', body: JSON.stringify(payload) }),

    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, v);
      });
      return apiFetch(`/assessments?${qs.toString()}`);
    },

    get: (id) => apiFetch(`/assessments/${id}`),

    submit: (id, answers) =>
      apiFetch(`/assessments/${id}/submit`, {
        method: 'POST',
        body: JSON.stringify({ answers }),
      }),

    result: (id) => apiFetch(`/assessments/${id}/result`),

    reassess: (id, payload = {}) =>
      apiFetch(`/assessments/${id}/reassess`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    comparison: (id, baseline_id = null) => {
      const qs = baseline_id ? `?baseline_id=${baseline_id}` : '';
      return apiFetch(`/assessments/${id}/comparison${qs}`);
    },

    listReassessments: (id) => apiFetch(`/assessments/${id}/reassessments`),

    generateRecommendations: (id) =>
      apiFetch(`/assessments/${id}/recommendations`, { method: 'POST' }),

    listRecommendations: (id) =>
      apiFetch(`/assessments/${id}/recommendations`),
  },

  // ─── Courses ────────────────────────────────────────────────────────────
  courses: {
    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, v);
      });
      return apiFetch(`/courses?${qs.toString()}`);
    },

    get: (id) => apiFetch(`/courses/${id}`),
  },

  // ─── Recommendations ────────────────────────────────────────────────────
  recommendations: {
    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, v);
      });
      return apiFetch(`/recommendations?${qs.toString()}`);
    },

    get: (id) => apiFetch(`/recommendations/${id}`),

    updateStatus: (id, status) =>
      apiFetch(`/recommendations/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
  },
};
