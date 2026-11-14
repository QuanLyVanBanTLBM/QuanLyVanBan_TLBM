import type { ResourceCategory, ResourceType } from '@app-types/resource';

/**
 * Chuẩn hóa chuỗi tiếng Việt để so khớp không phân biệt hoa/thường và dấu thanh.
 */
export const normalizeSearchText = (str?: string | null): string => {
  return (str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .trim();
};

/**
 * Lọc danh sách Danh mục / Thư mục (Cấp 1) theo tên thư mục hoặc ký hiệu.
 */
export const filterResourceCategories = (
  categories: ResourceCategory[],
  query: string
): ResourceCategory[] => {
  const normQuery = normalizeSearchText(query);
  if (!normQuery) return categories;
  return categories.filter(
    (cat) =>
      normalizeSearchText(cat.ten_tai_lieu).includes(normQuery) ||
      normalizeSearchText(cat.ky_hieu).includes(normQuery)
  );
};

/**
 * Lọc danh sách Loại tài liệu (Cấp 2) theo tên loại.
 */
export const filterResourceTypes = (
  types: ResourceType[],
  query: string
): ResourceType[] => {
  const normQuery = normalizeSearchText(query);
  if (!normQuery) return types;
  return types.filter((typeItem) =>
    normalizeSearchText(typeItem.ten_loai).includes(normQuery)
  );
};

