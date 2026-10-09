/**
 * API Client dùng chung cho toàn bộ dự án (theo chuẩn Issue #8 & Issue #9).
 * - Tự động quản lý baseURL từ biến môi trường VITE_API_URL hoặc mặc định /api.
 * - Tự động đính kèm Authorization: Bearer <access_token>.
 * - Xử lý HTTP 401 tập trung và hỗ trợ làm mới token (Refresh Token) tự động.
 */

import { t } from '@i18n/translate';

export interface ApiErrorResponse {
  success?: boolean;
  error?: string;
  detail?: string;
  message?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  status: number;
  data: ApiErrorResponse;

  constructor(status: number, data: ApiErrorResponse, message?: string) {
    super(message || data.error || data.detail || data.message || t('common.apiError', { status: String(status) }));
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

const BASE_URL = import.meta.env.VITE_API_URL || '';

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

async function handleResponse<T>(res: Response): Promise<T> {
  const headersObj = res.headers;
  const contentType = headersObj?.get ? headersObj.get('content-type') : null;
  const isJson = !contentType || contentType.includes('application/json');
  let data: unknown;
  if (isJson && typeof res.json === 'function') {
    data = await res.json().catch(() => ({}));
  } else if (typeof res.text === 'function') {
    data = await res.text();
  } else {
    data = {};
  }

  if (!res.ok) {
    throw new ApiError(
      res.status,
      typeof data === 'object' && data !== null ? (data as ApiErrorResponse) : { error: String(data) }
    );
  }

  return data as T;
}

function getCsrfToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function apiClient<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken && !headers.has('X-CSRFToken')) {
      headers.set('X-CSRFToken', csrfToken);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      credentials: options.credentials || 'include',
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(0, {
      error: t('common.networkError'),
    });
  }

  // Xử lý tự động làm mới token nếu gặp 401 Unauthorized và không phải endpoint login/refresh
  if (response.status === 401 && !endpoint.includes('/auth/login/') && !endpoint.includes('/token/refresh/')) {
    const refreshToken = localStorage.getItem('tlbm_refresh_token');

    if (refreshToken) {
      if (!isRefreshing) {
        isRefreshing = true;

        try {
          const csrfToken = getCsrfToken();
          const refreshHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
          if (csrfToken) refreshHeaders['X-CSRFToken'] = csrfToken;

          const refreshRes = await fetch(`${BASE_URL}/api/auth/token/refresh/`, {
            method: 'POST',
            headers: refreshHeaders,
            credentials: 'include',
            body: JSON.stringify({ refresh: refreshToken }),
          });

          if (refreshRes.ok) {
            const refreshData = await refreshRes.json();
            const newAccess = refreshData.access || refreshData.token;
            if (newAccess) {
              localStorage.setItem('tlbm_access_token', newAccess);
              localStorage.setItem('tlbm_token', newAccess);
              processQueue(null, newAccess);
              isRefreshing = false;

              // Thực hiện lại request ban đầu với token mới và kiểm tra response.ok
              headers.set('Authorization', `Bearer ${newAccess}`);
              const retryRes = await fetch(url, { ...options, headers });
              return await handleResponse<T>(retryRes);
            }
          }
          throw new Error('Refresh token invalid');
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          isRefreshing = false;
          // Refresh thất bại -> Dọn sạch session và đăng xuất
          localStorage.removeItem('tlbm_access_token');
          localStorage.removeItem('tlbm_token');
          localStorage.removeItem('tlbm_refresh_token');
          localStorage.removeItem('tlbm_session');
          window.dispatchEvent(new Event('tlbm_auth_changed'));
          throw new ApiError(401, { error: t('auth.sessionExpired') });
        }
      } else {
        // Đang có tiến trình refresh -> Đợi token mới
        return new Promise<T>((resolve, reject) => {
          failedQueue.push({
            resolve: (newToken: string) => {
              headers.set('Authorization', `Bearer ${newToken}`);
              fetch(url, { ...options, headers })
                .then((res) => handleResponse<T>(res))
                .then(resolve)
                .catch(reject);
            },
            reject,
          });
        });
      }
    }
  }

  return await handleResponse<T>(response);
}

apiClient.get = <T>(endpoint: string, options?: RequestInit) =>
  apiClient<T>(endpoint, { ...options, method: 'GET' });

apiClient.post = <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
  apiClient<T>(endpoint, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });

apiClient.put = <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
  apiClient<T>(endpoint, {
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  });

apiClient.patch = <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
  apiClient<T>(endpoint, {
    ...options,
    method: 'PATCH',
    body: body ? JSON.stringify(body) : undefined,
  });

apiClient.delete = <T>(endpoint: string, options?: RequestInit) =>
  apiClient<T>(endpoint, { ...options, method: 'DELETE' });

/**
 * Tải file nhị phân (Blob) từ API, tự động đính kèm Token và kích hoạt tải về trên trình duyệt.
 */
export async function downloadBlob(endpoint: string, defaultFilename?: string): Promise<void> {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers();
  const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { method: 'GET', headers });
  if (!response.ok) {
    const errorData: ApiErrorResponse = { error: 'organizations.messages.exportError' };
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const parsed = await response.json().catch(() => null);
      if (parsed && typeof parsed === 'object') {
        Object.assign(errorData, parsed);
      }
    }
    throw new ApiError(response.status, errorData);
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;

  const disposition = response.headers.get('Content-Disposition');
  let filename = defaultFilename || t('common.defaultDownloadFilename');
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function apiClientBlob(endpoint: string, options: RequestInit = {}): Promise<Blob> {
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    credentials: options.credentials || 'include',
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData: ApiErrorResponse = { error: t('common.apiError', { status: String(response.status) }) };
    throw new ApiError(response.status, errorData);
  }

  return await response.blob();
}

apiClient.blob = downloadBlob;

export default apiClient;
