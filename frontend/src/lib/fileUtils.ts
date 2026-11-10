/**
 * Tiện ích xử lý URL tệp đính kèm và tài liệu
 */

/**
 * Chuyển đổi đường dẫn tệp đính kèm thành URL tuyệt đối trỏ trực tiếp tới máy chủ backend.
 * Tránh lỗi Vite SPA router trả về index.html khi mở tệp nhị phân trên tab mới.
 */
export const getAbsoluteFileUrl = (filePath: string | null | undefined): string => {
  if (!filePath) return '';
  if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
    return filePath;
  }
  const cleanPath = filePath.startsWith('/') ? filePath : `/${filePath}`;
  const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const backendBase = isLocal ? 'http://127.0.0.1:8000' : window.location.origin;
  return `${backendBase}${cleanPath}`;
};
