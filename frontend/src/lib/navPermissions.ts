import { MAIN_MODULES } from '@lib/constants';
import { usePermissions } from '@lib/permissions';
import type { MainModule } from '@app-types/navigation';

/**
 * Mã quyền xem mà backend bắt buộc cho từng trang trên menu (khớp mã trong view/permission của backend).
 * Trang không có trong bảng này giữ nguyên cho mọi người đăng nhập, vì backend không đòi quyền xem riêng:
 * Dashboard, Công việc (lọc theo vai trò trong công việc), Văn bản (người nhận/người tạo vẫn xem được
 * dù không có view_*), Trình ký.
 */
/**
 * Mã quyền của phân hệ Trình ký. Backend (`signing/permissions.py`, MA_QUYEN_TRINH_KY) cho vào API khi có bất kỳ
 * mã nào, nên trang cũng hiện khi có một trong các mã này, không chỉ view_trinhky (#849).
 */
const SIGNING_PERMISSIONS = [
  'view_trinhky',
  'add_trinhky',
  'manage_signing_process',
  'send_trinhky',
  'sign_trinhky',
  'cancel_trinhky',
  'view_signing_audit',
  'view_all_trinhky',
] as const;

export const PAGE_VIEW_PERMISSION: Record<string, string | readonly string[]> = {
  records: 'view_hoso',
  record_types: 'view_hoso',
  resources: 'view_tailieu',
  birthdays: 'view_sinhnhat',
  meetings: 'view_schedule_phonghop',
  organizations: 'view_donvi',
  positions: 'view_chucvu',
  employees: 'view_list_cbnv',
  roles: 'view_nhomquyen',
  approvals: SIGNING_PERMISSIONS,
  ai_assistant: 'use_aiassistant',
};

/** Trang không có trong bảng thì mở cho mọi người đăng nhập; giá trị là mảng thì chỉ cần một mã trong đó. */
export function canViewPage(pageId: string, can: (codename: string) => boolean): boolean {
  const required = PAGE_VIEW_PERMISSION[pageId];
  if (!required) return true;
  return typeof required === 'string' ? can(required) : required.some((code) => can(code));
}

/** Lọc menu theo quyền: ẩn mục con thiếu quyền, ẩn phân hệ không còn mục con nào. */
export function filterModulesByPermission(
  modules: MainModule[],
  loaded: boolean,
  can: (codename: string) => boolean,
): MainModule[] {
  const result: MainModule[] = [];
  for (const mod of modules) {
    const subItems = mod.subItems.filter((sub) => !PAGE_VIEW_PERMISSION[sub.id] || (loaded && canViewPage(sub.id, can)));
    if (subItems.length === 0) continue;
    const defaultPage = subItems.some((sub) => sub.id === mod.defaultPage) ? mod.defaultPage : subItems[0].id;
    result.push(subItems.length === mod.subItems.length ? mod : { ...mod, subItems, defaultPage });
  }
  return result;
}

export function useVisibleModules(): MainModule[] {
  const { loaded, can } = usePermissions();
  return filterModulesByPermission(MAIN_MODULES, loaded, can);
}
