/**
 * API Client dùng chung cho toàn bộ dự án (theo chuẩn Issue #8 & Issue #9).
 * - Tự động quản lý baseURL từ biến môi trường VITE_API_URL hoặc mặc định /api.
 * - Tự động đính kèm Authorization: Bearer <access_token>.
 * - Xử lý HTTP 401 tập trung và hỗ trợ làm mới token (Refresh Token) tự động.
 */

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
    super(message || data.error || data.detail || data.message || `API Error: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

const BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '';

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

type ApiRequestInit = RequestInit & { responseType?: 'json' | 'blob' };

async function handleResponse<T>(res: Response, responseType: 'json' | 'blob' = 'json'): Promise<T> {
  if (res.ok && responseType === 'blob') {
    return (await res.blob()) as T;
  }

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

export async function apiClient<T = unknown>(
  endpoint: string,
  options: ApiRequestInit = {}
): Promise<T> {
  const { responseType = 'json', ...requestOptions } = options;
  const url = endpoint.startsWith('http')
    ? endpoint
    : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers(requestOptions.headers || {});
  if (!headers.has('Content-Type') && !(requestOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, { ...requestOptions, headers });
  } catch {
    throw new ApiError(0, {
      error: 'Không thể kết nối đến máy chủ Backend. Vui lòng kiểm tra lại đường truyền!',
    });
  }

  // Xử lý tự động làm mới token nếu gặp 401 Unauthorized và không phải endpoint login/refresh
  if (response.status === 401 && !endpoint.includes('/auth/login/') && !endpoint.includes('/token/refresh/')) {
    const refreshToken = localStorage.getItem('tlbm_refresh_token');

    if (refreshToken) {
      if (!isRefreshing) {
        isRefreshing = true;

        try {
          const refreshRes = await fetch(`${BASE_URL}/api/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
              const retryRes = await fetch(url, { ...requestOptions, headers });
              return await handleResponse<T>(retryRes, responseType);
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
          throw new ApiError(401, { error: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại!' });
        }
      } else {
        // Đang có tiến trình refresh -> Đợi token mới
        return new Promise<T>((resolve, reject) => {
          failedQueue.push({
            resolve: (newToken: string) => {
              headers.set('Authorization', `Bearer ${newToken}`);
              fetch(url, { ...requestOptions, headers })
                .then((res) => handleResponse<T>(res, responseType))
                .then(resolve)
                .catch(reject);
            },
            reject,
          });
        });
      }
    }
  }

  return await handleResponse<T>(response, responseType);
}

export function apiClientBlob(endpoint: string, options: RequestInit = {}): Promise<Blob> {
  return apiClient<Blob>(endpoint, { ...options, responseType: 'blob' });
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

apiClient.delete = <T>(endpoint: string, options?: RequestInit) =>
  apiClient<T>(endpoint, { ...options, method: 'DELETE' });

export default apiClient;
