import { Attachment, TaskComment, TaskDetail } from '../types/task';
import { API_BASE_URL, ApiError, authHeaders, flattenErrors, messageForStatus, request } from './client';

/** Backend trả đường dẫn tương đối (/api/...); dựng URL đầy đủ từ API_BASE_URL hoặc origin trang. URL tuyệt đối giữ nguyên. */
export function resolveDownloadUrl(downloadUrl: string): string {
  if (/^https?:\/\//i.test(downloadUrl)) return downloadUrl;
  const pageOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000';
  const origin = /^https?:\/\//i.test(API_BASE_URL) ? new URL(API_BASE_URL).origin : pageOrigin;
  return new URL(downloadUrl, origin).toString();
}

/** Ghi nhận "đã mở" (nếu đủ điều kiện) và trả về chi tiết mới nhất. Gọi khi vào trang chi tiết. */
export function openTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/open/`, { method: 'POST' });
}

export function deleteEvidence(taskId: number, attachmentId: number): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/evidences/${attachmentId}/`, { method: 'DELETE' });
}

export function approveTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/approve/`, { method: 'POST' });
}

export function unapproveTask(taskId: number): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/unapprove/`, { method: 'POST' });
}

export function listComments(taskId: number, signal?: AbortSignal): Promise<TaskComment[]> {
  return request<TaskComment[]>(`work/tasks/${taskId}/comments/`, { signal });
}

/**
 * Ghi ý kiến, có thể kèm file. File kèm theo là file kết quả (bằng chứng hoàn thành):
 * ý kiến có file đầu tiên sẽ chuyển công việc sang Chờ duyệt.
 */
export function createComment(taskId: number, content: string, files: File[] = []): Promise<TaskComment> {
  const data = new FormData();
  data.append('content', content);
  files.forEach((file) => data.append('files', file));
  return request<TaskComment>(`work/tasks/${taskId}/comments/`, { method: 'POST', body: data });
}

/**
 * Tải file về máy. Không dùng thẻ <a href> trực tiếp vì thẻ này không gửi được header xác thực,
 * nên phải tải bằng fetch rồi tự kích hoạt lưu file.
 */
export async function downloadAttachment(attachment: Attachment): Promise<void> {
  let response: Response;
  try {
    response = await fetch(resolveDownloadUrl(attachment.downloadUrl), { headers: authHeaders() });
  } catch {
    throw new ApiError(
      'Không kết nối được máy chủ để tải file. Hãy kiểm tra backend đã chạy rồi thử lại.',
      0,
    );
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const { message } = flattenErrors(data);
    throw new ApiError(message || messageForStatus(response.status), response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = attachment.fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
