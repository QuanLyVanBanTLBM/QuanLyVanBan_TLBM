import { describe, it, expect } from 'vitest';
import type { ResourceCategory, ResourceType } from '@app-types/resource';
import {
  normalizeSearchText,
  filterResourceCategories,
  filterResourceTypes,
} from './resourceSearch';

describe('resourceSearch helpers', () => {
  const categories: ResourceCategory[] = [
    { id: 1, stt_uu_tien: 1, ky_hieu: 'TM-CHUNG', ten_tai_lieu: 'Tài liệu chung' },
    { id: 2, stt_uu_tien: 2, ky_hieu: 'HDQT-01', ten_tai_lieu: 'Hội đồng Quản trị' },
    { id: 3, stt_uu_tien: 3, ky_hieu: 'NS-BL', ten_tai_lieu: 'Hồ sơ Bảo Long Bến Thành' },
  ];

  const types: ResourceType[] = [
    { id: 10, dm_tai_lieu: 1, ten_loai: 'Quy chế - Quy định nội bộ', is_public: true },
    { id: 11, dm_tai_lieu: 1, ten_loai: 'Biểu mẫu hành chính chung', is_public: true },
    { id: 12, dm_tai_lieu: 2, ten_loai: 'Quyết định ban hành', is_public: false },
  ];

  it('normalizes Vietnamese diacritics and đ/Đ accurately', () => {
    expect(normalizeSearchText('  Hội đồng Quản trị  ')).toBe('hoi dong quan tri');
    expect(normalizeSearchText('Đơn vị Bảo Long')).toBe('don vi bao long');
    expect(normalizeSearchText(null)).toBe('');
  });

  it('filters categories by unaccented name and ky_hieu', () => {
    expect(filterResourceCategories(categories, '')).toHaveLength(3);
    expect(filterResourceCategories(categories, '   ')).toHaveLength(3);

    const byName = filterResourceCategories(categories, 'ben thanh');
    expect(byName.map((c) => c.id)).toEqual([3]);

    const byDLetter = filterResourceCategories(categories, 'hoi dong');
    expect(byDLetter.map((c) => c.id)).toEqual([2]);

    const byCode = filterResourceCategories(categories, 'hdqt-01');
    expect(byCode.map((c) => c.id)).toEqual([2]);

    expect(filterResourceCategories(categories, 'khong ton tai')).toEqual([]);
  });

  it('filters document types by unaccented Vietnamese name', () => {
    expect(filterResourceTypes(types, '')).toHaveLength(3);

    const byDiacriticless = filterResourceTypes(types, 'quy dinh noi bo');
    expect(byDiacriticless.map((t) => t.id)).toEqual([10]);

    const byMixedCase = filterResourceTypes(types, 'QuYếT đỊnH');
    expect(byMixedCase.map((t) => t.id)).toEqual([12]);

    expect(filterResourceTypes(types, 'xyz-not-found')).toEqual([]);
  });
});

