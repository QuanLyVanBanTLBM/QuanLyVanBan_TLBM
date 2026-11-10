import { ActivePageId } from '@app-types/navigation';
import type { ModulePage } from '@app/moduleRoutes';

// Mỗi module khai báo trang của mình trong `paths.ts` (pages/<module>/paths.ts, modules/<module>/paths.ts).
const MODULE_PAGES: ModulePage[] = Object.values(
  import.meta.glob<ModulePage[]>(['../pages/*/paths.ts', '../modules/*/paths.ts'], { eager: true, import: 'default' })
).flat();

export const pageIdToPath = (pageId: ActivePageId): string =>
  MODULE_PAGES.find((page) => page.id === pageId)?.path ?? '/dashboard';

export const pathToPageId = (pathname: string): ActivePageId => {
  const clean = pathname.replace(/\/+$/, '') || '/';
  return MODULE_PAGES.find((page) => page.matches(clean))?.id ?? 'dashboard';
};

export interface DocumentRouteTarget {
  id: number | string;
  loai?: string | null;
  document_kind?: string | null;
  pham_vi?: string | null;
}

/**
 * Phân nhánh URL xem chi tiết văn bản (Đúng cấu trúc if - else theo yêu cầu của Thầy).
 * Hệ thống chuẩn hóa 2 phân hệ: Văn bản Đến (/documents/incoming) và Văn bản Đi (/documents/outgoing).
 *
 * @param doc Đối tượng văn bản hoặc ID văn bản
 * @param fallbackType Phân hệ dự phòng ('DEN' | 'DI') nếu là văn bản cũ không có trường loai
 * @returns Đường dẫn URL kèm query param detail
 */
export function resolveDocumentDetailUrl(
  doc: DocumentRouteTarget | number | string,
  fallbackType?: 'DEN' | 'DI'
): string {
  // 1. Trường hợp truyền đối tượng văn bản có thông tin phân hệ
  if (typeof doc === 'object' && doc !== null) {
    const loaiUpper = (doc.loai || '').toUpperCase();
    const kindLower = (doc.document_kind || '').toLowerCase();

    // Nếu là Văn bản Đi (kể cả Hạn chế Đi) -> Điều hướng theo phân hệ Văn bản Đi
    if (loaiUpper === 'DI' || kindLower === 'vanbandi') {
      return `/documents/outgoing?detail=${doc.id}`;
    }
    // Mặc định là Văn bản Đến (kể cả Hạn chế Đến) -> Điều hướng theo phân hệ Văn bản Đến
    return `/documents/incoming?detail=${doc.id}`;
  }

  // 2. Trường hợp là văn bản cũ (chỉ truyền ID từ liên kết cũ của GĐ1 hoặc link thay thế)
  if (fallbackType === 'DI') {
    return `/documents/outgoing?detail=${doc}`;
  }
  // Mặc định cho toàn bộ văn bản cũ GĐ1 thuộc hệ Văn bản Đến
  return `/documents/incoming?detail=${doc}`;
}

/**
 * Phân nhánh URL gọi API Backend tương ứng cho từng văn bản.
 * Tương thích giữa API phân hệ mới (/api/documents/{id}/?loai=...) và API Facade tổng hợp cũ (/api/documents/{id}/)
 */
export function resolveDocumentApiUrl(
  id: number | string,
  loai?: string | null
): string {
  if (!loai) {
    // Gọi API Facade tổng hợp: Backend tự động if-else tìm kiếm trong VanBanDen -> VanBanDi
    return `/api/documents/${id}/`;
  }

  const loaiUpper = String(loai).trim().toUpperCase();
  if (loaiUpper === 'DI') {
    return `/api/documents/${id}/?loai=DI`;
  }
  return `/api/documents/${id}/?loai=DEN`;
}

