/**
 * 统一 API 调用层
 * 所有前端页面通过此模块与 FastAPI 后端通信。
 * 自动附加 Authorization header，401 时尝试 refresh token。
 */

const API_BASE = '/api';
const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

let _onUnauthorized = null;

/** Register a callback invoked when auth fails completely. */
export function setOnUnauthorized(fn) {
  _onUnauthorized = fn;
}

async function tryRefreshToken() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

function getHeaders(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers = { ...extra };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

async function request(url, options = {}, { retryOn401 = true } = {}) {
  try {
    const mergedOpts = { ...options };
    // Merge auth header (do not overwrite Content-Type for FormData)
    mergedOpts.headers = getHeaders(options.headers || {});
    // AbortController timeout: 120s for normal requests
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120_000);
    mergedOpts.signal = controller.signal;

    const response = await fetch(url, mergedOpts);
    clearTimeout(timer);

    if (response.status === 401 && retryOn401) {
      const newToken = await tryRefreshToken();
      if (newToken) {
        // Retry once with new token
        return request(url, options, { retryOn401: false });
      }
      // Refresh failed — notify app
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      if (_onUnauthorized) _onUnauthorized();
      throw new Error('认证已过期，请重新登录');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    // Some endpoints return no body (e.g. HTML responses)
    const ct = response.headers.get('content-type') || '';
    if (ct.includes('application/json')) return response.json();
    return response.text();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请重试');
    }
    console.error(`API Error [${url}]:`, error);
    throw error;
  }
}

export const api = {
  // ── 认证 ──────────────────────────────
  login: (email, password) =>
    request(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  register: (email, password, displayName) =>
    request(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),

  getMe: () => request(`${API_BASE}/auth/me`),

  // ── 画像库 ──────────────────────────────
  getPersonas: () =>
    request(`${API_BASE}/personas`),

  getPersona: (id) =>
    request(`${API_BASE}/personas/${id}`),

  // ── 报告中心 ────────────────────────────
  getReports: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`${API_BASE}/reports${qs ? '?' + qs : ''}`);
  },

  getReport: (id) =>
    request(`${API_BASE}/reports/${id}`),

  getReportHtmlUrl: (id) =>
    `${API_BASE}/reports/${id}/html`,

  getReportDownloadUrl: (id) =>
    `${API_BASE}/reports/${id}/download`,

  shareReport: (id) =>
    request(`${API_BASE}/reports/${id}/share`, { method: 'POST' }),

  // ── 项目管理 ────────────────────────────
  getProjects: () =>
    request(`${API_BASE}/projects`),

  getProject: (id) =>
    request(`${API_BASE}/projects/${id}`),

  createProject: (data) =>
    request(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  runProject: (id) =>
    request(`${API_BASE}/projects/${id}/run`, { method: 'POST' }),

  getProjectStatus: (id) =>
    request(`${API_BASE}/projects/${id}/status`),

  // ── 仪表盘 ──────────────────────────────
  getDashboardStats: () =>
    request(`${API_BASE}/stats/dashboard`),

  // ── 文件上传 ────────────────────────────
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    // Do NOT set Content-Type — browser sets multipart boundary
    return request(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  // ── 系统设置 ────────────────────────────
  getSettings: () =>
    request(`${API_BASE}/settings`),

  updateSettings: (data) =>
    request(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  testConnection: () =>
    request(`${API_BASE}/settings/test-connection`, { method: 'POST' }),

  // ── 生图 ────────────────────────────────
  generateAvatar: (payload) =>
    request(`${API_BASE}/images/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  // ── 健康检查 ────────────────────────────
  healthCheck: () =>
    request(`${API_BASE}/health`),
};
