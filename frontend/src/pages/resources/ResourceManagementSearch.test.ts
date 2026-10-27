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

type SearchScopeType = 'all' | 'title' | 'code' | 'authority' | 'author' | 'attachment';

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

  if (searchField === 'title') {
    return checkMatch(doc.tieu_de);
  } else if (searchField === 'code') {
    return checkMatch(doc.ky_hieu);
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
});
