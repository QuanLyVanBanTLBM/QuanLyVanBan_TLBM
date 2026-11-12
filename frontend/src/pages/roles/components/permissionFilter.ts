import { Permission } from '@app-types/authorization';
import { getModuleLabel, getPermissionLabel } from './permissionLabels';

// Bỏ dấu tiếng Việt và hoa/thường để tìm "chuc vu" vẫn ra "Chức vụ".
function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase();
}

function matchesQuery(perm: Permission, normalizedQuery: string): boolean {
  if (!normalizedQuery) return true;
  return [perm.name, perm.codename, perm.module_ten, getPermissionLabel(perm), getModuleLabel(perm.module_ten)]
    .some((field) => normalizeText(field || '').includes(normalizedQuery));
}

/** Các quyền đang hiện theo ô tìm (dùng chung cho danh sách và nút Chọn tất cả / Bỏ chọn). */
export function filterPermissions(permissions: Permission[], query: string): Permission[] {
  const normalizedQuery = normalizeText(query.trim());
  return permissions.filter((perm) => matchesQuery(perm, normalizedQuery));
}
