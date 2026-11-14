import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ResourceCategory, ResourceItem, ResourceType } from '@app-types/resource';

const apiMocks = vi.hoisted(() => {
  const client = vi.fn();
  Object.assign(client, {
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    blob: vi.fn(),
  });
  return { client };
});

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof import('@lib/apiClient')>('@lib/apiClient');
  return {
    ...actual,
    apiClient: apiMocks.client,
    default: apiMocks.client,
  };
});

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({
    can: () => true,
    isSuperuser: true,
    isSystemAdmin: true,
  }),
}));

vi.mock('@lib/authService', () => ({
  authService: {
    getSession: () => ({
      username: 'admin',
      fullName: 'Quản trị viên',
      roles: ['ADMIN'],
    }),
  },
}));

import ResourceManagementPage from './ResourceManagementPage';

describe('Issue #828: ResourceManagementPage Dropdown Search (Danh mục & Loại tài liệu)', () => {
  const categoriesData: ResourceCategory[] = [
    { id: 1, stt_uu_tien: 1, ky_hieu: 'TM-CHUNG', ten_tai_lieu: 'Tài liệu chung' },
    { id: 2, stt_uu_tien: 2, ky_hieu: 'NS-BL', ten_tai_lieu: 'Hồ sơ Bảo Long Bến Thành' },
    { id: 3, stt_uu_tien: 3, ky_hieu: 'HDQT-01', ten_tai_lieu: 'Hội đồng Quản trị' },
  ];

  const typesData: ResourceType[] = [
    { id: 10, dm_tai_lieu: 1, ten_loai: 'Quy chế - Quy định nội bộ', is_public: true },
    { id: 11, dm_tai_lieu: 1, ten_loai: 'Biểu mẫu hành chính chung', is_public: true },
    { id: 12, dm_tai_lieu: 1, ten_loai: 'Tờ trình phê duyệt', is_public: true },
  ];

  const documentsData: ResourceItem[] = [
    {
      id: 101,
      dm_tai_lieu: 1,
      dm_tai_lieu_name: 'Tài liệu chung',
      loai_tai_lieu: [10],
      loai_tai_lieu_names: ['Quy chế - Quy định nội bộ'],
      ky_hieu: 'DOC-01',
      tieu_de: 'Văn bản mẫu 1',
      ngay_dang: '2026-11-14',
      hieu_luc: 'CON_HIEU_LUC',
      file_dinh_kem: '/media/doc-1.pdf',
      hien_thi: 'TAT_CA',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();

    apiMocks.client.mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/resources/categories/')) {
        return { count: categoriesData.length, next: null, previous: null, results: categoriesData };
      }
      if (endpoint.startsWith('/api/resources/types/')) {
        return { count: typesData.length, next: null, previous: null, results: typesData };
      }
      if (endpoint.startsWith('/api/resources/documents/')) {
        return { count: documentsData.length, next: null, previous: null, results: documentsData };
      }
      return [];
    });
  });

  it('lọc được Danh mục (Thư mục Cấp 1) theo tên không dấu/ký hiệu, hiện rỗng, xóa nhanh và tự reset khi chọn', async () => {
    render(
      <MemoryRouter>
        <ResourceManagementPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Văn bản mẫu 1')).toBeInTheDocument();
    });

    const catDropdownBtn = screen.getByRole('button', { name: 'Mở danh sách tất cả Danh mục' });
    fireEvent.click(catDropdownBtn);

    const searchInput = screen.getByPlaceholderText('Tìm tên thư mục, ký hiệu...');
    expect(searchInput).toBeInTheDocument();

    // Lọc theo tên không dấu có chữ Đ/đ
    fireEvent.change(searchInput, { target: { value: 'hoi dong' } });
    expect(screen.getByRole('button', { name: 'Hội đồng Quản trị' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hồ sơ Bảo Long Bến Thành' })).not.toBeInTheDocument();
    // Nút 'Tất cả thư mục' vẫn luôn cố định
    expect(screen.getByRole('button', { name: /Tất cả thư mục/i })).toBeInTheDocument();

    // Nhập từ khóa không khớp -> hiển thị trạng thái trống
    fireEvent.change(searchInput, { target: { value: 'khong-co-ket-qua' } });
    expect(screen.getByText('Không tìm thấy thư mục nào phù hợp')).toBeInTheDocument();

    // Bấm nút xóa nhanh
    fireEvent.click(screen.getByRole('button', { name: 'Xóa tìm kiếm' }));
    expect(searchInput).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Tài liệu chung' })).toBeInTheDocument();

    // Tìm theo ký hiệu rồi bấm chọn thư mục -> tự đóng dropdown & reset search
    fireEvent.change(searchInput, { target: { value: 'tm-chung' } });
    const filteredBtn = screen.getByRole('button', { name: 'Tài liệu chung' });
    fireEvent.click(filteredBtn);

    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Tìm tên thư mục, ký hiệu...')).not.toBeInTheDocument();
    });

    // Mở lại dropdown -> từ khóa phải đã được reset rỗng
    fireEvent.click(catDropdownBtn);
    expect(screen.getByPlaceholderText('Tìm tên thư mục, ký hiệu...')).toHaveValue('');
  });

  it('lọc được Loại tài liệu (Cấp 2) không dấu, giữ nguyên thứ tự ghim # và tự reset khi đóng/chọn', async () => {
    render(
      <MemoryRouter>
        <ResourceManagementPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Văn bản mẫu 1')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Tài liệu chung/i })).toBeInTheDocument();
    });

    // Chọn danh mục 1 trên thanh chính để mở hàng Cấp 2 (Loại tài liệu)
    fireEvent.click(screen.getByRole('button', { name: /Tài liệu chung/i }));

    const typeDropdownBtn = await screen.findByTitle('Mở danh sách tất cả Loại tài liệu');
    fireEvent.click(typeDropdownBtn);

    const typeSearchInput = screen.getByPlaceholderText('Tìm tên loại tài liệu...');
    expect(typeSearchInput).toBeInTheDocument();

    // Lọc loại thứ 3 ('Tờ trình phê duyệt') bằng tiếng Việt không dấu
    fireEvent.change(typeSearchInput, { target: { value: 'to trinh' } });
    expect(screen.getByRole('button', { name: 'Tờ trình phê duyệt' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Biểu mẫu hành chính chung' })).not.toBeInTheDocument();
    // Thứ tự ghim #3 của mục thứ 3 vẫn giữ nguyên #3 (không nhảy về #1)
    expect(screen.getByText('#3')).toBeInTheDocument();

    // Từ khóa không khớp -> thông báo rỗng
    fireEvent.change(typeSearchInput, { target: { value: 'khong-ton-tai' } });
    expect(screen.getByText('Không tìm thấy loại tài liệu nào phù hợp')).toBeInTheDocument();

    // Đóng qua Escape -> mở lại phải reset rỗng
    fireEvent.keyDown(typeSearchInput, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Tìm tên loại tài liệu...')).not.toBeInTheDocument();
    });

    fireEvent.click(typeDropdownBtn);
    expect(screen.getByPlaceholderText('Tìm tên loại tài liệu...')).toHaveValue('');

    // Chọn loại tài liệu từ kết quả tìm kiếm -> đóng & reset
    fireEvent.change(screen.getByPlaceholderText('Tìm tên loại tài liệu...'), {
      target: { value: 'bieu mau' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Biểu mẫu hành chính chung' }));
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Tìm tên loại tài liệu...')).not.toBeInTheDocument();
    });

    fireEvent.click(typeDropdownBtn);
    expect(screen.getByPlaceholderText('Tìm tên loại tài liệu...')).toHaveValue('');
  });
});
