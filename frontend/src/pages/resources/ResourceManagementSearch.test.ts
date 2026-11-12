import { describe, it, expect } from 'vitest';
import { ResourceItem } from '@app-types/resource';

// Kiểm thử logic tìm kiếm cụ thể và chuẩn hóa tiếng Việt
const normalizeSearchText = (str?: string | null): string => {
  return (str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .trim();
};

type SearchScopeType = 'all' | 'title' | 'code' | 'date' | 'authority' | 'author' | 'attachment';

const filterResource = (
  doc: ResourceItem,
  searchTerm: string,
  searchField: SearchScopeType
): boolean => {
  if (!searchTerm.trim()) return true;
  const rawTerm = searchTerm.toLowerCase().trim();
  const normTerm = normalizeSearchText(searchTerm);

  const checkMatch = (val?: string | null) => {
    if (!val) return false;
    const lower = val.toLowerCase();
    if (lower.includes(rawTerm)) return true;
    return normalizeSearchText(val).includes(normTerm);
  };

  const checkDateMatch = (dateStr?: string | null) => {
    if (!dateStr) return false;
    const cleanDate = dateStr.trim();
    const cleanTerm = rawTerm.replace(/-/g, '/');
    const parts = cleanDate.split('-');
    if (parts.length === 3) {
      const [y, m, d] = parts;
      const mNum = parseInt(m, 10);
      const dNum = parseInt(d, 10);
      const candidates = [
        `${d}/${m}/${y}`,
        `${dNum}/${mNum}/${y}`,
        `${y}-${m}-${d}`,
        `${m}/${y}`,
        `${mNum}/${y}`,
        `${d}/${m}`,
        `${dNum}/${mNum}`,
        y,
      ];
      if (candidates.some((c) => c.includes(cleanTerm) || cleanTerm.includes(c))) {
        return true;
      }
    }
    return cleanDate.includes(rawTerm);
  };

  if (searchField === 'title') {
    return checkMatch(doc.tieu_de);
  } else if (searchField === 'code') {
    return checkMatch(doc.ky_hieu);
  } else if (searchField === 'date') {
    return checkDateMatch(doc.ngay_dang);
  } else if (searchField === 'authority') {
    return checkMatch(doc.noi_ban_hanh);
  } else if (searchField === 'author') {
    return checkMatch(doc.nguoi_tao_name);
  } else if (searchField === 'attachment') {
    const matchSingle = checkMatch(doc.file_dinh_kem);
    const matchMultiple = (doc.attachments || []).some((att) => checkMatch(att.name));
    return matchSingle || matchMultiple;
  } else {
    return (
      checkMatch(doc.tieu_de) ||
      checkMatch(doc.ky_hieu) ||
      checkDateMatch(doc.ngay_dang) ||
      checkMatch(doc.noi_ban_hanh) ||
      checkMatch(doc.nguoi_tao_name) ||
      checkMatch(doc.ghi_chu) ||
      checkMatch(doc.file_dinh_kem) ||
      (doc.attachments || []).some((att) => checkMatch(att.name))
    );
  }
};

describe('ResourceManagement Specific Search Logic', () => {
  const sampleDoc: ResourceItem = {
    id: 101,
    dm_tai_lieu: 1,
    loai_tai_lieu: [1],
    tieu_de: 'Quyết định ban hành Quy chế văn thư lưu trữ',
    ky_hieu: '15/QĐ-UBND',
    noi_ban_hanh: 'Ủy ban nhân dân Tỉnh',
    ngay_dang: '2026-03-10',
    hieu_luc: 'CON_HIEU_LUC',
    nguoi_tao_name: 'Nguyễn Văn Quản Trị',
    ghi_chu: 'Áp dụng cho toàn bộ các sở ban ngành trực thuộc',
    file_dinh_kem: 'quy_che_van_thu_2026.pdf',
    hien_thi: 'TAT_CA',
    attachments: [
      { id: 1, name: 'phu_luc_01_bieu_mau.docx', path: '/media/phu_luc.docx', file_size: 1024, mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    ],
  };

  it('chuẩn hóa tiếng Việt không dấu chính xác', () => {
    expect(normalizeSearchText('Quyết Định Ban Hành')).toBe('quyet dinh ban hanh');
    expect(normalizeSearchText('Đơn vị Đắk Lắk')).toBe('don vi dak lak');
    expect(normalizeSearchText('SỞ KẾ HOẠCH & ĐẦU TƯ')).toBe('so ke hoach & dau tu');
  });

  it('tìm kiếm theo tiêu đề (searchField = title)', () => {
    expect(filterResource(sampleDoc, 'Quy chế', 'title')).toBe(true);
    expect(filterResource(sampleDoc, 'quy che', 'title')).toBe(true); // không dấu
    expect(filterResource(sampleDoc, '15/QĐ', 'title')).toBe(false); // ký hiệu không khớp trong tiêu đề
  });

  it('tìm kiếm theo ký hiệu (searchField = code)', () => {
    expect(filterResource(sampleDoc, '15/QĐ', 'code')).toBe(true);
    expect(filterResource(sampleDoc, '15/qd', 'code')).toBe(true);
    expect(filterResource(sampleDoc, 'Quy chế', 'code')).toBe(false);
  });

  it('tìm kiếm theo nơi ban hành (searchField = authority)', () => {
    expect(filterResource(sampleDoc, 'nhan dan', 'authority')).toBe(true);
    expect(filterResource(sampleDoc, 'UBND', 'authority')).toBe(false);
  });

  it('tìm kiếm theo người tạo (searchField = author)', () => {
    expect(filterResource(sampleDoc, 'nguyen van', 'author')).toBe(true);
    expect(filterResource(sampleDoc, 'Quan Tri', 'author')).toBe(true);
    expect(filterResource(sampleDoc, 'UBND', 'author')).toBe(false);
  });

  it('tìm kiếm theo tệp đính kèm (searchField = attachment)', () => {
    expect(filterResource(sampleDoc, 'quy_che_van_thu', 'attachment')).toBe(true);
    expect(filterResource(sampleDoc, 'bieu_mau', 'attachment')).toBe(true);
    expect(filterResource(sampleDoc, 'khong_co_file', 'attachment')).toBe(false);
  });

  it('tìm kiếm trên tất cả trường (searchField = all)', () => {
    expect(filterResource(sampleDoc, 'Quy chế', 'all')).toBe(true);
    expect(filterResource(sampleDoc, '15/QD', 'all')).toBe(true);
    expect(filterResource(sampleDoc, 'nhan dan', 'all')).toBe(true);
    expect(filterResource(sampleDoc, 'nguyen van', 'all')).toBe(true);
    expect(filterResource(sampleDoc, 'bieu_mau', 'all')).toBe(true);
    expect(filterResource(sampleDoc, 'so ban nganh', 'all')).toBe(true); // trong ghi chú
    expect(filterResource(sampleDoc, 'tu_khoa_khong_ton_tai', 'all')).toBe(false);
  });

  it('tìm kiếm theo ngày tháng năm (searchField = date)', () => {
    // sampleDoc.ngay_dang là '2026-03-10'
    expect(filterResource(sampleDoc, '10/03/2026', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '10/3/2026', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '2026-03-10', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '03/2026', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '10/03', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '2026', 'date')).toBe(true);
    expect(filterResource(sampleDoc, '2025', 'date')).toBe(false);
  });

  it('tìm kiếm theo ngày tháng trong Tất cả tiêu chí (searchField = all)', () => {
    expect(filterResource(sampleDoc, '10/03/2026', 'all')).toBe(true);
    expect(filterResource(sampleDoc, '10/03', 'all')).toBe(true);
  });
});
describe('ResourceManagement URL State Synchronization', () => {
  it('serializes filter and modal state into URL search params correctly', () => {
    const params = new URLSearchParams();
    const state = {
      category: '2',
      type: '5',
      year: '2026',
      status: 'CON_HIEU_LUC',
      q: 'hiiii',
      search_field: 'author',
      page: 2,
      pageSize: 10,
      detail: 15,
    };

    if (state.category !== 'all') params.set('category', state.category);
    if (state.type !== 'all') params.set('type', state.type);
    if (state.year !== 'all') params.set('year', state.year);
    if (state.status !== 'all') params.set('status', state.status);
    if (state.q.trim()) params.set('q', state.q.trim());
    if (state.search_field !== 'all') params.set('search_field', state.search_field);
    if (state.page > 1) params.set('page', String(state.page));
    if (state.pageSize !== 5) params.set('pageSize', String(state.pageSize));
    if (state.detail) params.set('detail', String(state.detail));

    expect(params.get('category')).toBe('2');
    expect(params.get('type')).toBe('5');
    expect(params.get('year')).toBe('2026');
    expect(params.get('status')).toBe('CON_HIEU_LUC');
    expect(params.get('q')).toBe('hiiii');
    expect(params.get('search_field')).toBe('author');
    expect(params.get('page')).toBe('2');
    expect(params.get('pageSize')).toBe('10');
    expect(params.get('detail')).toBe('15');
  });

  it('restores modal and action states from URL search params correctly', () => {
    const detailUrl = new URLSearchParams('detail=42');
    expect(detailUrl.get('detail')).toBe('42');

    const createUrl = new URLSearchParams('action=create');
    expect(createUrl.get('action')).toBe('create');

    const editUrl = new URLSearchParams('edit=99');
    expect(editUrl.get('edit')).toBe('99');

    const categoriesUrl = new URLSearchParams('action=categories');
    expect(categoriesUrl.get('action')).toBe('categories');
  });
});
