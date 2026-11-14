import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ResourceCategory, ResourceItem, ResourceType } from '@app-types/resource';

const apiMocks = vi.hoisted(() => {
  const post = vi.fn();
  const put = vi.fn();
  const patch = vi.fn();
  const del = vi.fn();
  const client = vi.fn();
  Object.assign(client, { post, put, patch, delete: del, blob: vi.fn() });
  return {
    client: client as ReturnType<typeof vi.fn> & {
      post: typeof post;
      put: typeof put;
      patch: typeof patch;
      delete: typeof del;
    },
    post,
    put,
    patch,
    delete: del,
  };
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

describe('Issue #824: ResourceManagementPage Scoped Sync & Stability', () => {
  let categoriesStore: ResourceCategory[];
  let typesStore: ResourceType[];
  let documentsStore: ResourceItem[];

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();

    categoriesStore = [
      { id: 1, stt_uu_tien: 2, ky_hieu: 'TM-01', ten_tai_lieu: 'Thư mục Tài chính' },
      { id: 2, stt_uu_tien: 3, ky_hieu: 'TM-02', ten_tai_lieu: 'Thư mục Nhân sự' },
    ];

    typesStore = [
      { id: 10, dm_tai_lieu: 1, ten_loai: 'Quy chế tài chính', is_public: true },
      { id: 20, dm_tai_lieu: 2, ten_loai: 'Biểu mẫu nhân sự', is_public: true },
    ];

    documentsStore = Array.from({ length: 6 }, (_, i) => ({
      id: 100 + i + 1,
      dm_tai_lieu: 1,
      dm_tai_lieu_name: 'Thư mục Tài chính',
      loai_tai_lieu: [10],
      loai_tai_lieu_names: ['Quy chế tài chính'],
      ky_hieu: `DOC-0${i + 1}`,
      tieu_de: `Tài liệu số ${i + 1}`,
      ngay_dang: '2026-11-14',
      hieu_luc: 'CON_HIEU_LUC',
      file_dinh_kem: `/media/doc-${i + 1}.pdf`,
      hien_thi: 'TAT_CA',
    }));

    apiMocks.client.mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/resources/categories/')) {
        return { count: categoriesStore.length, next: null, previous: null, results: categoriesStore };
      }
      if (endpoint.startsWith('/api/resources/types/')) {
        return { count: typesStore.length, next: null, previous: null, results: typesStore };
      }
      if (endpoint.startsWith('/api/resources/documents/')) {
        return { count: documentsStore.length, next: null, previous: null, results: documentsStore };
      }
      return [];
    });
  });

  it('xóa tài liệu cuối trang > 1 lùi trang hợp lệ ngay và chỉ đồng bộ phạm vi documents (không refetch categories/types)', async () => {
    apiMocks.delete.mockImplementation(async (endpoint: string) => {
      if (endpoint === '/api/resources/documents/106/') {
        documentsStore = documentsStore.filter((d) => d.id !== 106);
      }
      return {};
    });

    render(
      <MemoryRouter>
        <ResourceManagementPage />
      </MemoryRouter>
    );

    // Chờ nạp trang 1 xong (5/6 tài liệu)
    await waitFor(() => {
      expect(screen.getByText('Tài liệu số 1')).toBeInTheDocument();
      expect(screen.getByText('Hiển thị 1–5 / 6 tài liệu')).toBeInTheDocument();
    });

    // Sang trang 2 (hiển thị dòng thứ 6 duy nhất)
    fireEvent.click(screen.getByRole('button', { name: 'Trang 2' }));
    await waitFor(() => {
      expect(screen.getByText('Tài liệu số 6')).toBeInTheDocument();
      expect(screen.getByText('Hiển thị 6–6 / 6 tài liệu')).toBeInTheDocument();
    });

    // Xóa đếm call ban đầu để chỉ theo dõi các GET phát sinh sau khi xóa
    apiMocks.client.mockClear();

    fireEvent.click(screen.getByLabelText('Thao tác với tài liệu DOC-06'));
    fireEvent.click(screen.getByRole('button', { name: 'Xóa' }));
    expect(screen.getByText('Xác nhận xóa tài liệu')).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole('button', { name: 'Xóa' });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    // Kiểm tra gọi API DELETE đúng endpoint và trang tự lùi về trang 1 hợp lệ ngay
    await waitFor(() => {
      expect(apiMocks.delete).toHaveBeenCalledWith('/api/resources/documents/106/');
      expect(screen.getByText('Hiển thị 1–5 / 5 tài liệu')).toBeInTheDocument();
      expect(screen.getByText('Tài liệu số 5')).toBeInTheDocument();
    });

    await waitFor(() => {
      const postDeleteGets = apiMocks.client.mock.calls.map(([url]) => String(url));
      expect(postDeleteGets.some((u) => u.startsWith('/api/resources/documents/'))).toBe(true);
      expect(postDeleteGets.some((u) => u.startsWith('/api/resources/categories/'))).toBe(false);
      expect(postDeleteGets.some((u) => u.startsWith('/api/resources/types/'))).toBe(false);
    });
  });

  it('tạo mới thư mục sắp xếp ngay theo stt_uu_tien và chỉ đồng bộ phạm vi categories khi không có loại con', async () => {
    const newCategory: ResourceCategory = {
      id: 99,
      stt_uu_tien: 1,
      ky_hieu: 'TM-TOP',
      ten_tai_lieu: 'Thư mục Ưu tiên Số 1',
      ngay_lap: '2026-11-14',
    };

    apiMocks.post.mockImplementation(async (endpoint: string) => {
      if (endpoint === '/api/resources/categories/') {
        categoriesStore = [newCategory, ...categoriesStore];
        return newCategory;
      }
      return {};
    });

    render(
      <MemoryRouter>
        <ResourceManagementPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Tài liệu số 1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Danh mục' }));
    fireEvent.click(screen.getByTitle('Thêm mới'));

    fireEvent.change(screen.getByPlaceholderText(/VD: Tài liệu, Biểu mẫu chung/i), {
      target: { value: 'Thư mục Ưu tiên Số 1' },
    });
    fireEvent.change(screen.getByPlaceholderText('VD: 1, 2, 3...'), {
      target: { value: '1' },
    });

    apiMocks.client.mockClear();
    fireEvent.click(screen.getByRole('button', { name: /Lưu thư mục/i }));

    await waitFor(() => {
      expect(apiMocks.post).toHaveBeenCalledWith(
        '/api/resources/categories/',
        expect.objectContaining({
          stt_uu_tien: 1,
          ten_tai_lieu: 'Thư mục Ưu tiên Số 1',
        })
      );
    });

    // Dòng đầu bảng thư mục trong modal phải là "Thư mục Ưu tiên Số 1" (stt_uu_tien = 1)
    await waitFor(() => {
      const modalDialog = screen.getByRole('dialog');
      const rows = within(modalDialog).getAllByRole('row');
      expect(rows[1].textContent).toContain('Thư mục Ưu tiên Số 1');
    });

    await waitFor(() => {
      const postCreateGets = apiMocks.client.mock.calls.map(([url]) => String(url));
      expect(postCreateGets.some((u) => u.startsWith('/api/resources/categories/'))).toBe(true);
      expect(postCreateGets.some((u) => u.startsWith('/api/resources/types/'))).toBe(false);
      expect(postCreateGets.some((u) => u.startsWith('/api/resources/documents/'))).toBe(false);
    });
  });
});
