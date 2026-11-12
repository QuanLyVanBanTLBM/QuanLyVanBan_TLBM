// Lớp gọi API dùng chung cho module Công việc.
// Mọi lỗi từ máy chủ được chuyển thành câu tiếng Việt có hướng khắc phục để hiển thị thẳng cho người dùng.

const RAW_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api` : '/api');
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

// ---------------------------------------------------------------------------
// XÁC THỰC: dùng JWT chung của dự án (accounts/login/ cấp access token).
// Lớp xác thực giả lập X-Mock-User-Id đã bị gỡ ở backend (issue #65-1).
// TODO(C1 Nhom 7): doi ACCESS_TOKEN_STORAGE_KEY cho khop khoa ma trang dang nhap luu token.
// ---------------------------------------------------------------------------
export const ACCESS_TOKEN_STORAGE_KEY = 'tlbm_access_token';

export function getAccessToken(): string {
  try {
    return (
      window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) ||
      window.localStorage.getItem('tlbm_token') ||
      ''
    );
  } catch {
    return '';
  }
}

/** Header xác thực gắn vào mọi request của module. */
export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------

export type FieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  status: number;
  fieldErrors: FieldErrors;

  constructor(message: string, status: number, fieldErrors: FieldErrors = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }

  /** Lỗi của riêng một trường trên form, ví dụ errorFor('dueDate'). */
  errorFor(field: string): string | undefined {
    const messages = this.fieldErrors[field];
    return messages && messages.length ? messages[0] : undefined;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  params?: Record<string, string | number | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, params?: RequestOptions['params']): string {
  const cleanPath = path.replace(/^\/+/, '');
  const rawUrl = `${API_BASE_URL}/${cleanPath}`;
  const origin =
    typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : 'http://127.0.0.1:8000';
  const url = new URL(rawUrl, origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

/** Lỗi của danh sách (ví dụ nhiều file) có dạng lồng nhau {"0": ["..."]}: gom hết thành câu chữ. */
function collectMessages(value: unknown): string[] {
  if (typeof value === 'string') return value ? [value] : [];
  if (Array.isArray(value)) return value.flatMap(collectMessages);
  if (value && typeof value === 'object') return Object.values(value as Record<string, unknown>).flatMap(collectMessages);
  return [];
}

export function flattenErrors(payload: unknown): { message: string; fieldErrors: FieldErrors } {
  const fieldErrors: FieldErrors = {};
  let message = '';

  if (typeof payload === 'string') {
    return { message: payload, fieldErrors };
  }

  if (payload && typeof payload === 'object') {
    Object.entries(payload as Record<string, unknown>).forEach(([field, value]) => {
      const messages = collectMessages(value);
      if (!messages.length) return;
      fieldErrors[field] = messages;
      if (!message) message = messages[0];
    });
  }

  return { message, fieldErrors };
}

export function messageForStatus(status: number): string {
  if (status === 401) {
    return 'Bạn chưa đăng nhập hoặc phiên đăng nhập đã hết hạn. Hãy đăng nhập lại rồi thử lại.';
  }
  if (status === 403) {
    return 'Bạn không có quyền thực hiện thao tác này.';
  }
  if (status === 404) {
    return 'Không tìm thấy dữ liệu, hoặc bạn không có quyền xem. Hãy quay lại danh sách và tải lại trang.';
  }
  if (status >= 500) {
    return 'Máy chủ gặp lỗi khi xử lý yêu cầu. Hãy thử lại, nếu vẫn lỗi thì xem log của cửa sổ chạy runserver.';
  }
  return 'Yêu cầu không thực hiện được. Hãy kiểm tra lại dữ liệu vừa nhập rồi thử lại.';
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, signal } = options;
  const headers = authHeaders();

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    // Không tự đặt Content-Type: trình duyệt cần tự sinh boundary cho multipart.
    payload = body;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body: payload, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError(
      'Không kết nối được máy chủ. Hãy kiểm tra backend đã chạy (python manage.py runserver) rồi thử lại.',
      0,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('Content-Type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const { message, fieldErrors } = flattenErrors(data);
    throw new ApiError(message || messageForStatus(response.status), response.status, fieldErrors);
  }

  return data as T;
}

/** Lấy câu thông báo hiển thị được từ bất kỳ lỗi nào. */
export function toMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return 'Có lỗi không xác định. Hãy tải lại trang rồi thử lại.';
}
