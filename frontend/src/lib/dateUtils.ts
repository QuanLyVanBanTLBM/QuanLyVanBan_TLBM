/**
 * Tiện ích xử lý và định dạng Ngày/Giờ & Tệp tin.
 * Tuân thủ quy định chuẩn đề tài ITC:
 * "Định dạng ngày tháng bắt buộc phải lưu và hiển thị kèm cả Giờ : Phút : Giây (HH:mm:ss dd/MM/yyyy)".
 */

/**
 * Định dạng chuỗi ISO Datetime thành chuỗi ngày giờ đầy đủ chuẩn: HH:mm:ss dd/MM/yyyy
 * Ví dụ: "2026-09-23T08:30:15Z" -> "08:30:15 23/09/2026"
 */
export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return '—';

  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '—';

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  return `${hours}:${minutes}:${seconds} ${day}/${month}/${year}`;
}

/**
 * Định dạng chuỗi Datetime thành dạng ngày tháng: dd/MM/yyyy
 * Ví dụ: "2026-09-23" -> "23/09/2026"
 */
export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';

  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '—';

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  return `${day}/${month}/${year}`;
}

/**
 * Định dạng dung lượng tệp tin (bytes) thành đơn vị thân thiện (KB, MB, GB).
 * Ví dụ: 1048576 -> "1.0 MB", 2048 -> "2.0 KB"
 */
export function formatFileSize(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));

  if (i === 0) return `${bytes} B`;

  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(1)} ${units[i]}`;
}

/**
 * Lấy phần mở rộng của file (đuôi file) dạng chữ thường.
 */
export function getFileExtension(fileName?: string | null): string {
  if (!fileName) return '';
  const parts = fileName.split('.');
  return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
}

/**
 * Nhận diện icon FontAwesome và màu sắc đại diện cho từng loại file đính kèm.
 */
export function getFileMeta(fileName?: string | null): {
  icon: string;
  colorClass: string;
  badgeLabel: string;
} {
  const ext = getFileExtension(fileName);

  switch (ext) {
    case 'pdf':
      return {
        icon: 'fa-file-pdf',
        colorClass: 'text-red-500',
        badgeLabel: 'PDF',
      };
    case 'doc':
    case 'docx':
      return {
        icon: 'fa-file-word',
        colorClass: 'text-blue-500',
        badgeLabel: 'WORD',
      };
    case 'xls':
    case 'xlsx':
      return {
        icon: 'fa-file-excel',
        colorClass: 'text-emerald-500',
        badgeLabel: 'EXCEL',
      };
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'webp':
      return {
        icon: 'fa-file-image',
        colorClass: 'text-purple-500',
        badgeLabel: 'ẢNH',
      };
    default:
      return {
        icon: 'fa-file-lines',
        colorClass: 'text-slate-400',
        badgeLabel: ext ? ext.toUpperCase() : 'TỆP',
      };
  }
}
