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

/**
 * Định dạng dung lượng tệp tin (bytes) sang chuỗi dễ đọc (B, KB, MB, GB)
 */
export const formatFileSize = (bytes: number | null | undefined): string => {
  if (bytes === null || bytes === undefined || isNaN(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};
