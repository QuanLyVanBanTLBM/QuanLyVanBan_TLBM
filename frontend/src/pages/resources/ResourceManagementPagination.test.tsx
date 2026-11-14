import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLanguage } from '@i18n/translate';
import { ResourceCategory, ResourceItem, ResourceType } from '@app-types/resource';

const apiMocks = vi.hoisted(() => {
  const client = vi.fn();
  const post = vi.fn();
  const put = vi.fn();
  const patch = vi.fn();
  const del = vi.fn();
  Object.assign(client, { post, put, patch, delete: del });
  return { client, post, put, patch, del };
});

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof import('@lib/apiClient')>('@lib/apiClient');
  return {
    ...actual,
    apiClient: apiMocks.client as unknown as typeof actual.apiClient,
    default: apiMocks.client as unknown as typeof actual.apiClient,
  };
});

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({
    loaded: true,
    isSuperuser: false,
    isSystemAdmin: true,
    can: () => true,
  }),
}));

vi.mock('@lib/authService', () => ({
  authService: {
    getSession: () => ({
      username: 'admin',
      fullName: 'Quản trị viên',
      role: 'admin',
    }),
  },
}));

import { fetchAllResourcePages } from '@lib/resourcePagination';
import ResourceManagementPage from './ResourceManagementPage';

describe('Issue #819: Tải đầy đủ phân trang >100 bản ghi & đưa mục mới tạo lên đầu', () => {
  beforeEach(() => {
    setLanguage('vi');
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('fetchAllResourcePages tải nối tiếp toàn bộ các trang (>100 bản ghi) và chống trùng lặp id', async () => {
    apiMocks.client
      .mockResolvedValueOnce({
        count: 105,
        next: 'https://example.local/api/resources/types/?page=2&page_size=100',
        previous: null,
        results: [
          ...Array.from({ length: 100 }, (_, i) => ({
            id: 105 - i,
            ten_loai: `Loại ${105 - i}`,
          })),
        ],
      })
      .mockResolvedValueOnce({
        count: 105,
        next: null,
        previous: 'https://example.local/api/resources/types/?page=1&page_size=100',
        results: [
          // Cố tình chồng 1 bản ghi id=6 (như trường hợp chèn bản ghi mới giữa 2 request)
          { id: 6, ten_loai: 'Loại 6 (trùng)' },
          ...Array.from({ length: 5 }, (_, i) => ({
            id: 5 - i,
            ten_loai: `Loại ${5 - i}`,
          })),
        ],
      });

    const res = (await fetchAllResourcePages<ResourceType>(
      '/api/resources/types/',
      'types'
    )) as { count: number; next: null; results: ResourceType[] };

    expect(apiMocks.client).toHaveBeenCalledTimes(2);
    expect(apiMocks.client).toHaveBeenNthCalledWith(1, '/api/resources/types/?page_size=100');
    expect(apiMocks.client).toHaveBeenNthCalledWith(2, '/api/resources/types/?page=2&page_size=100');
    expect(res.next).toBeNull();
    expect(res.results).toHaveLength(105);
    expect(res.results[0].id).toBe(105);
    expect(res.results[res.results.length - 1].id).toBe(1);
    expect(res.results.filter((r) => r.id === 6)).toHaveLength(1);
  });

  it('fetchAllResourcePages dừng an toàn khi next URL lặp lại hoặc trả về mảng phẳng / null', async () => {
    apiMocks.client.mockRejectedValueOnce(new Error('Network down'));
    expect(await fetchAllResourcePages('/api/resources/categories/', 'categories')).toBeNull();

    apiMocks.client.mockResolvedValueOnce([{ id: 1, ten_tai_lieu: 'Mảng phẳng' }]);
    expect(await fetchAllResourcePages('/api/resources/categories/', 'categories')).toEqual([
      { id: 1, ten_tai_lieu: 'Mảng phẳng' },
    ]);

    apiMocks.client
      .mockResolvedValueOnce({
        count: 999,
        next: 'http://localhost/api/resources/types/?page=2',
        results: [{ id: 2 }],
      })
      .mockResolvedValueOnce({
        count: 999,
        next: 'http://localhost/api/resources/types/?page=2',
        results: [{ id: 1 }],
      });

    const loopGuarded = (await fetchAllResourcePages<{ id: number }>(
      '/api/resources/types/',
      'types'
    )) as { results: Array<{ id: number }> };
    expect(apiMocks.client).toHaveBeenCalledTimes(4);
    expect(loopGuarded.results.map((x) => x.id)).toEqual([2, 1]);
  });

  it('hiển thị đầy đủ >100 danh mục, loại tài liệu, tài liệu và đẩy loại mới tạo lên dòng 1 trang 1', async () => {
    const categories: ResourceCategory[] = Array.from({ length: 105 }, (_, i) => ({
      id: i + 1,
      stt_uu_tien: i + 1,
      ten_tai_lieu: `Thư mục #${i + 1}`,
      nguoi_lap_name: 'Quản trị viên',
      ngay_lap: '2026-01-01',
    }));

    const typesState: ResourceType[] = Array.from({ length: 105 }, (_, i) => ({
      id: 105 - i,
      dm_tai_lieu: 1,
      ten_loai: `Loại tài liệu #${105 - i}`,
      is_public: true,
    }));

    const documents: ResourceItem[] = Array.from({ length: 105 }, (_, i) => ({
      id: 105 - i,
      dm_tai_lieu: 1,
      loai_tai_lieu: [105],
      tieu_de: `Tài liệu mẫu #${105 - i}`,
      ky_hieu: `TL-${105 - i}`,
      ngay_dang: '2026-01-01',
      hieu_luc: 'CON_HIEU_LUC',
      file_dinh_kem: `tai_lieu_${105 - i}.pdf`,
      hien_thi: 'TAT_CA',
    }));

    const paginate = <T,>(items: T[], url: string) => {
      const pageMatch = url.match(/[?&]page=(\d+)/);
      const page = pageMatch ? Number(pageMatch[1]) : 1;
      const pageSize = 100;
      const start = (page - 1) * pageSize;
      const slice = items.slice(start, start + pageSize);
      const hasNext = start + pageSize < items.length;
      const basePath = url.split('?')[0];
      return {
        count: items.length,
        next: hasNext ? `http://localhost${basePath}?page=${page + 1}&page_size=${pageSize}` : null,
        previous: page > 1 ? `http://localhost${basePath}?page=${page - 1}&page_size=${pageSize}` : null,
        results: slice,
      };
    };

    apiMocks.client.mockImplementation(async (endpoint: string) => {
      if (endpoint.startsWith('/api/resources/categories/')) return paginate(categories, endpoint);
      if (endpoint.startsWith('/api/resources/types/')) return paginate(typesState, endpoint);
      if (endpoint.startsWith('/api/resources/documents/')) return paginate(documents, endpoint);
      return { results: [] };
    });

    apiMocks.post.mockImplementation(async (endpoint: string, payload: Record<string, unknown>) => {
      if (endpoint === '/api/resources/types/') {
        const created: ResourceType = {
          id: 106,
          dm_tai_lieu: Number(payload.dm_tai_lieu),
          ten_loai: String(payload.ten_loai),
          is_public: Boolean(payload.is_public),
          ghi_chu: (payload.ghi_chu as string | null) ?? '',
        };
        typesState.unshift(created);
        return created;
      }
      return {};
    });

    render(
      <MemoryRouter>
        <ResourceManagementPage />
      </MemoryRouter>
    );

    // Chờ tải xong cả 2 trang (>= 105 tài liệu, không bị cắt ở mốc 100)
    await waitFor(() => {
      expect(screen.getByText('Tài liệu mẫu #105')).toBeInTheDocument();
    });
    expect(screen.getAllByText('105').length).toBeGreaterThanOrEqual(1);

    // Mở hộp thoại Quản lý Thư mục & Loại Tài liệu
    fireEvent.click(screen.getByRole('button', { name: 'Danh mục' }));
    const dialog = await screen.findByRole('dialog');

    // Bộ đếm trên 2 tab trong modal phải là 105 (không còn kẹt ở 100)
    const catTabBtn = within(dialog).getByRole('button', { name: /Thư mục.*105/i });
    const typeTabBtn = within(dialog).getByRole('button', { name: /Loại tài liệu.*105/i });
    expect(catTabBtn).toBeInTheDocument();
    expect(typeTabBtn).toBeInTheDocument();

    // Chuyển sang tab Loại tài liệu và đi tới trang 2
    fireEvent.click(typeTabBtn);
    expect(within(dialog).getByText('Loại tài liệu #105')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Trang 2' }));
    expect(within(dialog).getByText('Loại tài liệu #100')).toBeInTheDocument();

    // Thêm loại tài liệu thứ 106 khi đang ở trang 2
    fireEvent.click(within(dialog).getByTitle('Thêm mới Loại tài liệu'));
    fireEvent.change(screen.getByPlaceholderText(/VD: Biểu mẫu bảo hiểm, Tờ trình.../i), {
      target: { value: 'Loại tài liệu mới #106' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Lưu loại tài liệu/i }));

    // Kết quả: tổng tăng lên 106 (không mất ở 100) và mục #106 nhảy ngay lên dòng đầu trang 1
    await waitFor(() => {
      expect(within(dialog).getByRole('button', { name: /^Loại tài liệu\s*106$/i })).toBeInTheDocument();
    });
    expect(within(dialog).getByText('1–5')).toBeInTheDocument();
    expect(within(dialog).getByText('Loại tài liệu mới #106')).toBeInTheDocument();
    const modalRows = within(dialog).getAllByRole('row');
    expect(modalRows[1]).toHaveTextContent('Loại tài liệu mới #106');
  }, 15_000);
});
