import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OrganizationsPage from './OrganizationsPage';
import * as apiClientModule from '@lib/apiClient';
import { resetPermissionsCache } from '@lib/permissions';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClientModule>('@lib/apiClient');
  const mockClient = vi.fn() as unknown as typeof apiClientModule.apiClient;
  mockClient.get = vi.fn();
  mockClient.post = vi.fn();
  mockClient.put = vi.fn();
  mockClient.delete = vi.fn();
  mockClient.blob = vi.fn() as unknown as typeof apiClientModule.downloadBlob;

  return {
    ...actual,
    apiClient: mockClient,
    downloadBlob: vi.fn(),
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);

// Tab Khối (Cấp 1) mở đầu tiên; các ca kiểm bảng Đơn vị phải bấm sang tab Đơn vị (Cấp 2)
const openUnitsTab = () => fireEvent.click(screen.getByRole('button', { name: /Đơn vị \/ Phòng ban/i }));

describe('OrganizationsPage Component (Issue #19)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();
  });

  it('renders tabs and title correctly', async () => {
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [{ id: 1, ten: 'Khối Cơ quan', don_vi_count: 2 }];
      }
      if (endpoint.includes('/units/')) {
        return {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              khoi: 1,
              khoi_ten: 'Khối Cơ quan',
              stt_uu_tien: 1,
              ten: 'Phòng Kế toán',
              dien_thoai: '02838123456',
              email: 'ketoan@itc.edu.vn',
              dia_chi: 'Tầng 2',
              is_public: true,
              ghi_chu: '',
            },
          ],
        };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    // Tab Khối (Cấp 1) mở đầu tiên
    await waitFor(() => {
      expect(screen.getByText('Khối Cơ quan')).toBeInTheDocument();
    });

    // Chuyển sang Tab Đơn vị: tên phòng ban hiển thị
    openUnitsTab();
    await waitFor(() => {
      expect(screen.getByText('Phòng Kế toán')).toBeInTheDocument();
    });
  });

  it('renders warning badge for internal non-public units', async () => {
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [];
      }
      if (endpoint.includes('/units/')) {
        return {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 2,
              khoi: 1,
              khoi_ten: 'Khối Cơ quan',
              stt_uu_tien: 2,
              ten: 'Ban Kiểm Soát Nội Bộ',
              dien_thoai: '0987654321',
              email: 'bks@itc.edu.vn',
              dia_chi: 'Tầng 3',
              is_public: false,
              ghi_chu: 'Nội bộ',
            },
          ],
        };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();

    await waitFor(() => {
      expect(screen.getByText('Ban Kiểm Soát Nội Bộ')).toBeInTheDocument();
      expect(screen.getByText('Nội bộ')).toBeInTheDocument();
    });
  });

  describe('RBAC trên giao diện và lỗi xóa đơn vị', () => {
    const UNIT = {
      id: 7,
      khoi: 1,
      khoi_ten: 'Khối Cơ quan',
      stt_uu_tien: 1,
      ten: 'Phòng Kế hoạch',
      dien_thoai: '',
      email: '',
      dia_chi: '',
      is_public: true,
      ghi_chu: '',
    };

    function mockApi(permissions: string[], deleteError?: unknown) {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) {
          return { is_superuser: false, permissions };
        }
        if (endpoint.includes('/regions/')) {
          return [{ id: 1, ten: 'Khối Cơ quan', don_vi_count: 1 }];
        }
        if (endpoint.includes('/units/')) {
          return { count: 1, next: null, previous: null, results: [UNIT] };
        }
        return [];
      });
      vi.mocked(mockedApiClient.delete).mockImplementation((async () => {
        if (deleteError) throw deleteError;
        return undefined;
      }) as unknown as typeof mockedApiClient.delete);
    }

    function renderPage() {
      const view = render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );
      openUnitsTab();
      return view;
    }

    it('người chỉ có quyền xem không thấy nút Xuất danh bạ, Thêm, Sửa, Xóa', async () => {
      mockApi(['view_donvi']);
      renderPage();
      await waitFor(() => expect(screen.getByText('Phòng Kế hoạch')).toBeInTheDocument());

      expect(screen.queryByRole('button', { name: /Xuất danh bạ/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Thêm đơn vị/i })).not.toBeInTheDocument();
      expect(screen.queryByTitle('Chỉnh sửa')).not.toBeInTheDocument();
      expect(screen.queryByTitle('Xóa')).not.toBeInTheDocument();
      expect(screen.queryByRole('columnheader', { name: /Thao tác/i })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /Khối \/ Khu vực/i }));
      await waitFor(() => expect(screen.getByText('Khối Cơ quan')).toBeInTheDocument());
      expect(screen.queryByRole('button', { name: /Thêm khối/i })).not.toBeInTheDocument();
      expect(screen.queryByTitle('Chỉnh sửa')).not.toBeInTheDocument();
    });

    it('người đủ quyền thấy đầy đủ thao tác', async () => {
      mockApi(['view_donvi', 'add_donvi', 'change_donvi', 'delete_donvi', 'export_donvi']);
      renderPage();
      await waitFor(() => expect(screen.getByRole('button', { name: /Xuất danh bạ/i })).toBeInTheDocument());
      expect(screen.getByRole('button', { name: /Thêm đơn vị/i })).toBeInTheDocument();
      expect(screen.getByTitle('Chỉnh sửa')).toBeInTheDocument();
      expect(screen.getByTitle('Xóa')).toBeInTheDocument();
    });

    it('nút Xuất danh bạ tải file danh bạ theo bộ lọc đang chọn', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderPage();
      const button = await screen.findByRole('button', { name: /Xuất danh bạ/i });
      fireEvent.click(button);
      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
      const [endpoint, filename] = vi.mocked(apiClientModule.downloadBlob).mock.calls[0];
      expect(endpoint).toMatch(/^\/api\/organizations\/units\/export\/\?/);
      expect(endpoint).toContain('lang=vi');
      expect(filename).toBe('DanhBa_BAOLONG.xlsx');
      expect(await screen.findByText('Đã xuất danh bạ đơn vị, phòng ban.')).toBeInTheDocument();
    });

    it('ô tìm khối dùng câu tìm kiếm, không dùng câu gợi ý của ô nhập tên', async () => {
      mockApi(['view_donvi']);
      renderPage();
      await waitFor(() => expect(screen.getByText('Phòng Kế hoạch')).toBeInTheDocument());
      fireEvent.click(screen.getByRole('button', { name: /Khối \/ Khu vực/i }));
      expect(await screen.findByPlaceholderText('Tìm khối hoặc khu vực theo tên...')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText(/ví dụ: Khối Cơ quan/i)).not.toBeInTheDocument();
    });

    it('xóa đơn vị bị server từ chối: giữ hộp thoại và nêu đúng lý do, không báo lỗi kết nối mạng', async () => {
      const refused = new apiClientModule.ApiError(400, {
        detail: 'organizations.messages.unitHasEmployees',
        key: 'organizations.messages.unitHasEmployees',
      });
      mockApi(['view_donvi', 'delete_donvi'], refused);
      renderPage();
      await waitFor(() => expect(screen.getByTitle('Xóa')).toBeInTheDocument());

      fireEvent.click(screen.getByTitle('Xóa'));
      await screen.findByText('Xác nhận xóa Đơn vị');
      const deleteButtons = screen.getAllByRole('button', { name: 'Xóa' });
      fireEvent.click(deleteButtons[deleteButtons.length - 1]);

      await waitFor(() => {
        expect(screen.getByText(/vẫn còn cán bộ nhân viên trực thuộc/i)).toBeInTheDocument();
      });
      expect(screen.queryByText(/kết nối mạng/i)).not.toBeInTheDocument();
    });

    it('xóa đơn vị lỗi không rõ nguyên nhân: nêu lỗi xóa chung, không báo lỗi kết nối mạng', async () => {
      mockApi(['view_donvi', 'delete_donvi'], new Error('boom'));
      renderPage();
      await waitFor(() => expect(screen.getByTitle('Xóa')).toBeInTheDocument());

      fireEvent.click(screen.getByTitle('Xóa'));
      await screen.findByText('Xác nhận xóa Đơn vị');
      const deleteButtons = screen.getAllByRole('button', { name: 'Xóa' });
      fireEvent.click(deleteButtons[deleteButtons.length - 1]);

      await waitFor(() => {
        expect(screen.getByText(/Không thể xóa Đơn vị này\. Vui lòng thử lại sau/i)).toBeInTheDocument();
      });
      expect(screen.queryByText(/kết nối mạng/i)).not.toBeInTheDocument();
    });
  });

  it('khóa dropdown Đơn vị cho tới khi chọn Khối và reset khi đổi Khối', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 2, ten: 'Phòng Nhân sự', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [
          { id: 1, ten: 'Khối A', don_vi_count: 2 },
          { id: 2, ten: 'Khối B', don_vi_count: 1 },
        ];
      }
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) {
        return [unitA, unitB, unitC];
      }
      if (endpoint.includes('/units/')) {
        const rows = endpoint.includes('region_id=1')
          ? [unitA, unitB]
          : endpoint.includes('region_id=2')
            ? [unitC]
            : [unitA, unitB, unitC];
        return { count: rows.length, next: null, previous: null, results: rows };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();
    await waitFor(() => expect(screen.getByText('Phòng Kỹ thuật')).toBeInTheDocument());

    // Chưa chọn Khối: dropdown Đơn vị bị khóa
    const unitSelect = screen.getByRole('button', { name: 'Chọn Khối trước' });
    expect(unitSelect).toBeDisabled();

    // Chọn Khối A: mở khóa, chỉ liệt kê đơn vị của Khối A
    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    fireEvent.click(await screen.findByRole('option', { name: /Khối A/ }));
    fireEvent.keyDown(document, { key: 'Escape' });
    const unitSelectOn = await screen.findByRole('button', { name: 'Tất cả đơn vị thuộc Khối' });
    await waitFor(() => expect(unitSelectOn).toBeEnabled());
    fireEvent.click(unitSelectOn);
    expect(await screen.findByRole('option', { name: /Phòng Nhân sự/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Phòng Kỹ thuật/ })).not.toBeInTheDocument();

    // Chọn một đơn vị: bảng chỉ còn đơn vị đó
    fireEvent.click(screen.getByRole('option', { name: /Phòng Nhân sự/ }));
    await waitFor(() => expect(screen.queryByText('Phòng Kế toán')).not.toBeInTheDocument());

    // Đổi Khối: Đơn vị đã chọn bị reset
    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    fireEvent.click(await screen.findByRole('option', { name: /Khối B/ }));
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.getByText('Phòng Kỹ thuật')).toBeInTheDocument());
    expect(screen.queryByText('Phòng Nhân sự')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tất cả đơn vị thuộc Khối' })).toBeInTheDocument();
  });

  it('đã chọn một Đơn vị thì Xuất danh bạ gửi unit_id, file chỉ gồm Đơn vị đó', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 2, ten: 'Phòng Nhân sự', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions: ['view_donvi', 'export_donvi'] };
      if (endpoint.includes('/regions/')) return [{ id: 1, ten: 'Khối A', don_vi_count: 2 }];
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitB];
      if (endpoint.includes('/units/')) return { count: 2, next: null, previous: null, results: [unitA, unitB] };
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();
    await waitFor(() => expect(screen.getByText('Phòng Kế toán')).toBeInTheDocument());

    // Chưa chọn Đơn vị: không gửi unit_id
    fireEvent.click(await screen.findByRole('button', { name: /Xuất danh bạ/i }));
    await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
    expect(vi.mocked(apiClientModule.downloadBlob).mock.calls[0][0]).not.toContain('unit_id=');

    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    fireEvent.click(await screen.findByRole('option', { name: /Khối A/ }));
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.click(await screen.findByRole('button', { name: 'Tất cả đơn vị thuộc Khối' }));
    fireEvent.click(await screen.findByRole('option', { name: /Phòng Nhân sự/ }));
    await waitFor(() => expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Kế toán'));

    fireEvent.click(screen.getByRole('button', { name: /Xuất danh bạ/i }));
    await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(2));
    const endpoint = vi.mocked(apiClientModule.downloadBlob).mock.calls[1][0];
    expect(endpoint).toContain('region_id=1');
    expect(endpoint).toContain('unit_id=2');
  });

  describe('Xuất danh bạ ở tab Khối', () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };

    function mockApi(permissions: string[]) {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions };
        if (endpoint.includes('/regions/')) {
          return [
            { id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 1 },
            { id: 2, ten: 'Khối B', thu_tu_hien_thi: 2, don_vi_count: 1 },
          ];
        }
        if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitC];
        if (endpoint.includes('/units/')) return { count: 2, next: null, previous: null, results: [unitA, unitC] };
        return [];
      });
    }

    const renderRegionsTab = () =>
      render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );

    it('người có quyền xuất thấy nút trên thanh công cụ và trên từng dòng Khối', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderRegionsTab();
      await screen.findByRole('button', { name: 'Khối A' });
      expect(screen.getByRole('button', { name: /^Xuất danh bạ$/ })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: 'Xuất danh bạ Khối này' })).toHaveLength(2);
    });

    it('nút trên thanh công cụ xuất toàn bộ, nút trên dòng xuất đúng Khối đó', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderRegionsTab();
      await screen.findByRole('button', { name: 'Khối A' });

      fireEvent.click(screen.getByRole('button', { name: /^Xuất danh bạ$/ }));
      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
      const all = vi.mocked(apiClientModule.downloadBlob).mock.calls[0][0];
      expect(all).toContain('lang=vi');
      expect(all).not.toContain('region_id=');
      expect(all).not.toContain('unit_id=');

      // Dòng thứ hai là Khối B (id 2); bấm nút xuất không làm sổ danh sách Đơn vị của dòng
      const rowButtons = screen.getAllByRole('button', { name: 'Xuất danh bạ Khối này' });
      fireEvent.click(rowButtons[1]);
      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(2));
      const one = vi.mocked(apiClientModule.downloadBlob).mock.calls[1][0];
      expect(one).toContain('region_id=2');
      expect(one).not.toContain('unit_id=');
      expect(screen.getByRole('button', { name: 'Khối B' })).toHaveAttribute('aria-expanded', 'false');
    });

    it('người không có quyền xuất không thấy nút nào; người chỉ có quyền xuất vẫn thấy nút trên dòng', async () => {
      mockApi(['view_donvi']);
      const first = renderRegionsTab();
      await screen.findByRole('button', { name: 'Khối A' });
      expect(screen.queryByRole('button', { name: /Xuất danh bạ/ })).not.toBeInTheDocument();
      first.unmount();
      resetPermissionsCache();

      mockApi(['view_donvi', 'export_donvi']);
      renderRegionsTab();
      await screen.findByRole('button', { name: 'Khối A' });
      expect(screen.queryByTitle('Chỉnh sửa')).not.toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: 'Xuất danh bạ Khối này' })).toHaveLength(2);
    });
  });

  describe('Chọn nhiều Khối và Đơn vị để xuất chung một file', () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };

    function mockApi(permissions: string[]) {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions };
        if (endpoint.includes('/regions/')) {
          return [
            { id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 1 },
            { id: 2, ten: 'Khối B', thu_tu_hien_thi: 2, don_vi_count: 1 },
          ];
        }
        if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitC];
        if (endpoint.includes('/units/')) return { count: 2, next: null, previous: null, results: [unitA, unitC] };
        return [];
      });
    }

    const renderPage = () =>
      render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );

    it('tích Khối và Đơn vị rồi xuất đã chọn: một file với region_ids và unit_ids', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      expect(screen.queryByRole('button', { name: /Xuất đã chọn/ })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole('checkbox', { name: 'Chọn Khối Khối B để xuất' }));
      fireEvent.click(screen.getByRole('button', { name: 'Khối A' }));
      fireEvent.click(await screen.findByRole('checkbox', { name: 'Chọn đơn vị Phòng Kế toán để xuất' }));

      const exportSelected = screen.getByRole('button', { name: 'Xuất đã chọn (2)' });
      fireEvent.click(exportSelected);
      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
      const url = vi.mocked(apiClientModule.downloadBlob).mock.calls[0][0];
      expect(url).toContain('region_ids=2');
      expect(url).toContain('unit_ids=1');
      expect(url).not.toContain('region_id=');
      expect(url).not.toContain('unit_id=');
    });

    it('tích nhiều Khối bằng ô chọn tất cả và bỏ chọn xóa hết', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });

      fireEvent.click(screen.getByRole('checkbox', { name: 'Chọn tất cả Khối đang hiển thị' }));
      fireEvent.click(screen.getByRole('button', { name: 'Xuất đã chọn (2)' }));
      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
      expect(vi.mocked(apiClientModule.downloadBlob).mock.calls[0][0]).toContain('region_ids=1%2C2');

      fireEvent.click(screen.getByRole('button', { name: 'Bỏ chọn' }));
      expect(screen.queryByRole('button', { name: /Xuất đã chọn/ })).not.toBeInTheDocument();
      expect(screen.getByRole('checkbox', { name: 'Chọn Khối Khối A để xuất' })).not.toBeChecked();
    });

    it('lựa chọn giữ nguyên khi sang tab Đơn vị và gộp chung vào một file', async () => {
      mockApi(['view_donvi', 'export_donvi']);
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      fireEvent.click(screen.getByRole('checkbox', { name: 'Chọn Khối Khối A để xuất' }));

      fireEvent.click(screen.getByRole('button', { name: /Đơn vị \/ Phòng ban/ }));
      fireEvent.click(await screen.findByRole('checkbox', { name: 'Chọn đơn vị Phòng Kỹ thuật để xuất' }));
      fireEvent.click(screen.getByRole('button', { name: 'Xuất đã chọn (2)' }));

      await waitFor(() => expect(apiClientModule.downloadBlob).toHaveBeenCalledTimes(1));
      const url = vi.mocked(apiClientModule.downloadBlob).mock.calls[0][0];
      expect(url).toContain('region_ids=1');
      expect(url).toContain('unit_ids=3');
    });

    it('không có quyền xuất thì không có ô tích nào', async () => {
      mockApi(['view_donvi']);
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });
  });

  it('bấm vào Khối thì lọc theo Khối và mở luôn danh sách Đơn vị của Khối đó', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 2, ten: 'Phòng Nhân sự', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [
          { id: 1, ten: 'Khối A', don_vi_count: 2 },
          { id: 2, ten: 'Khối B', don_vi_count: 1 },
          { id: 3, ten: 'Khối Trống', don_vi_count: 0 },
        ];
      }
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitB, unitC];
      if (endpoint.includes('/units/')) {
        const rows = endpoint.includes('region_id=1')
          ? [unitA, unitB]
          : endpoint.includes('region_id=2')
            ? [unitC]
            : endpoint.includes('region_id=3')
              ? []
              : [unitA, unitB, unitC];
        return { count: rows.length, next: null, previous: null, results: rows };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();
    await waitFor(() => expect(screen.getByText('Phòng Kỹ thuật')).toBeInTheDocument());

    // Bấm (không rê chuột) vào Khối A: bảng lọc theo Khối A, dropdown vẫn mở và hiện Đơn vị của Khối A
    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    fireEvent.click(await screen.findByRole('option', { name: 'Khối A' }));
    await waitFor(() => expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Kỹ thuật'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getAllByRole('option', { name: 'Phòng Kế toán' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('option', { name: 'Phòng Nhân sự' }).length).toBeGreaterThan(0);
    expect(screen.queryAllByRole('option', { name: 'Phòng Kỹ thuật' })).toHaveLength(0);

    // Bấm tiếp một Đơn vị trong danh sách vừa mở: lọc thẳng theo Đơn vị và đóng dropdown
    const unitOptions = screen.getAllByRole('option', { name: 'Phòng Nhân sự' });
    fireEvent.click(unitOptions[unitOptions.length - 1]);
    await waitFor(() => expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Kế toán'));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();

    // Khối không có Đơn vị: bấm vào là chọn Khối và đóng dropdown
    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    fireEvent.click(await screen.findByRole('option', { name: 'Khối Trống' }));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    await waitFor(() => expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Nhân sự'));
  });

  it('màn hình nhỏ: rê chuột không mở danh sách Đơn vị, chỉ bấm vào Khối mới mở', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [
          { id: 1, ten: 'Khối A', don_vi_count: 1 },
          { id: 2, ten: 'Khối B', don_vi_count: 1 },
        ];
      }
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitC];
      if (endpoint.includes('/units/')) {
        const rows = endpoint.includes('region_id=2') ? [unitC] : [unitA, unitC];
        return { count: rows.length, next: null, previous: null, results: rows };
      }
      return [];
    });
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;
    try {
      render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );
      openUnitsTab();
      await waitFor(() => expect(screen.getByText('Phòng Kỹ thuật')).toBeInTheDocument());

      fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
      const regionA = await screen.findByRole('option', { name: 'Khối A' });
      // Rê chuột qua Khối A: không mở danh sách (không đẩy các dòng bên dưới xuống)
      fireEvent.mouseEnter(regionA.parentElement!.parentElement!);
      expect(screen.queryAllByRole('option', { name: 'Phòng Kế toán' })).toHaveLength(0);

      // Bấm Khối B: mở danh sách Đơn vị của Khối B ngay dưới Khối B
      fireEvent.click(screen.getByRole('option', { name: 'Khối B' }));
      expect(screen.getAllByRole('option', { name: 'Phòng Kỹ thuật' }).length).toBeGreaterThan(0);
      // Chuột rời danh sách: danh sách vẫn mở để còn bấm được Đơn vị
      fireEvent.mouseLeave(screen.getByRole('listbox'));
      await new Promise((r) => setTimeout(r, 250));
      expect(screen.getAllByRole('option', { name: 'Phòng Kỹ thuật' }).length).toBeGreaterThan(0);
    } finally {
      window.matchMedia = original;
    }
  });

  it('rê chuột vào Khối thì hiện Đơn vị của Khối, bấm Đơn vị thì lọc thẳng theo Đơn vị', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 2, ten: 'Phòng Nhân sự', is_public: true };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 3, ten: 'Phòng Kỹ thuật', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) {
        return [
          { id: 1, ten: 'Khối A', don_vi_count: 2 },
          { id: 2, ten: 'Khối B', don_vi_count: 1 },
        ];
      }
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitB, unitC];
      if (endpoint.includes('/units/')) {
        const rows = endpoint.includes('region_id=1') ? [unitA, unitB] : endpoint.includes('region_id=2') ? [unitC] : [unitA, unitB, unitC];
        return { count: rows.length, next: null, previous: null, results: rows };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();
    await waitFor(() => expect(screen.getByText('Phòng Kỹ thuật')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    const regionA = await screen.findByRole('option', { name: 'Khối A' });
    // Chưa hover: chưa thấy đơn vị
    expect(screen.queryAllByRole('option', { name: 'Phòng Nhân sự' })).toHaveLength(0);

    // Hover Khối A: hiện đơn vị của Khối A, không hiện đơn vị của Khối B
    fireEvent.mouseEnter(regionA.parentElement!.parentElement!);
    expect(screen.getAllByRole('option', { name: 'Phòng Nhân sự' }).length).toBeGreaterThan(0);
    expect(screen.queryAllByRole('option', { name: 'Phòng Kỹ thuật' })).toHaveLength(0);

    // Bấm đơn vị: chọn luôn Khối A + đơn vị đó, bảng chỉ còn đơn vị đó
    fireEvent.click(screen.getAllByRole('option', { name: 'Phòng Nhân sự' })[0]);
    await waitFor(() => expect(screen.queryByText('Phòng Kế toán')).not.toBeInTheDocument());
    expect(screen.getAllByText('Phòng Nhân sự').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Tất cả đơn vị thuộc Khối' })).toBeEnabled();
  });

  it('danh sách Đơn vị bung ra ngoài khung cuộn của Khối và ô tìm kiếm vẫn lọc đơn vị đã chọn', async () => {
    const unitA = { id: 1, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Kế toán', is_public: true };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 2, ten: 'Phòng Nhân sự', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) return [{ id: 1, ten: 'Khối A', don_vi_count: 2 }];
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitB];
      if (endpoint.includes('/units/')) {
        const rows = endpoint.includes('search=') ? [] : [unitA, unitB];
        return { count: rows.length, next: null, previous: null, results: rows };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    openUnitsTab();
    await waitFor(() => expect(screen.getByText('Phòng Nhân sự')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Tất cả các Khối/Khu vực' }));
    const regionA = await screen.findByRole('option', { name: 'Khối A' });
    fireEvent.mouseEnter(regionA.parentElement!.parentElement!);
    const unitOptions = screen.getAllByRole('option', { name: 'Phòng Nhân sự' });
    const unitOption = unitOptions[unitOptions.length - 1];
    // Panel đơn vị nằm trực tiếp trong body (không nằm trong khung cuộn nên không bị cắt)
    expect(unitOption.closest('.fixed')?.parentElement).toBe(document.body);

    fireEvent.click(unitOption);
    await waitFor(() => expect(screen.queryByText('Phòng Kế toán')).not.toBeInTheDocument());

    // Gõ từ khóa không khớp đơn vị đã chọn: bảng không còn dòng nào
    fireEvent.change(screen.getByPlaceholderText(/Tìm kiếm theo tên/), { target: { value: 'xyz' } });
    // (nhãn của ô chọn Đơn vị vẫn hiện tên đơn vị nên chỉ kiểm phần thân bảng)
    await waitFor(() => expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Nhân sự'));
    expect(document.querySelector('tbody')!.textContent).not.toContain('Phòng Kế toán');
  });

  it('tab Khối (Cấp 1) nằm bên trái và mở đầu tiên, tab Đơn vị (Cấp 2) nằm bên phải', async () => {
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) return [{ id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 0 }];
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [];
      if (endpoint.includes('/units/')) return { count: 0, next: null, previous: null, results: [] };
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    const regionTab = screen.getByRole('button', { name: /Khối \/ Khu vực/i });
    const unitTab = screen.getByRole('button', { name: /Đơn vị \/ Phòng ban/i });
    expect(regionTab.compareDocumentPosition(unitTab) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // Mở trang là thấy bảng Khối
    expect(await screen.findByPlaceholderText('Tìm khối hoặc khu vực theo tên...')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/Tìm kiếm theo tên/)).not.toBeInTheDocument();
    expect(regionTab.className).toContain('border-primary');
    expect(unitTab.className).not.toContain('border-primary');
  });

  it('tab Khối: bấm vào Khối thì sổ ra các Đơn vị trực thuộc, thẳng cột với bảng Khối', async () => {
    const unitA = {
      id: 1,
      khoi: 1,
      khoi_ten: 'Khối A',
      stt_uu_tien: 4,
      ten: 'Phòng Kế toán',
      dien_thoai: '02838123456',
      is_public: true,
    };
    const unitB = { id: 2, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 5, ten: 'Ban Kiểm soát', dien_thoai: '', is_public: false };
    const unitC = { id: 3, khoi: 2, khoi_ten: 'Khối B', stt_uu_tien: 6, ten: 'Phòng Kỹ thuật', is_public: true };
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/auth/me/permissions/')) {
        return { is_superuser: false, permissions: ['view_donvi', 'change_donvi'] };
      }
      if (endpoint.includes('/regions/')) {
        return [
          { id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 2 },
          // Khối B còn một Đơn vị nội bộ mà người dùng này không được xem
          { id: 2, ten: 'Khối B', thu_tu_hien_thi: 2, don_vi_count: 2 },
          { id: 3, ten: 'Khối Trống', thu_tu_hien_thi: 3, don_vi_count: 0 },
        ];
      }
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unitA, unitB, unitC];
      if (endpoint.includes('/units/')) return { count: 3, next: null, previous: null, results: [unitA, unitB, unitC] };
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    const regionA = await screen.findByRole('button', { name: 'Khối A' });
    expect(regionA).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Phòng Kế toán')).not.toBeInTheDocument();
    // Số Đơn vị chỉ tính những Đơn vị người dùng được xem, khớp với các dòng sổ ra
    const rowB = screen.getByRole('button', { name: 'Khối B' }).closest('tr')!;
    expect(rowB.textContent).toContain('1 đơn vị');
    // Khối không có Đơn vị: không có nút mở
    expect(screen.getByText('Khối Trống')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Khối Trống' })).not.toBeInTheDocument();

    // Bấm Khối A: mỗi Đơn vị một dòng, cùng số cột với dòng Khối:
    // cột Thứ tự đánh lại từ 1 trong Khối, cột Tên là tên (kèm điện thoại), cột Số đơn vị là trạng thái
    fireEvent.click(regionA);
    expect(regionA).toHaveAttribute('aria-expanded', 'true');
    const rowA = regionA.closest('tr')!;
    const unitRowA = screen.getByText('Phòng Kế toán').closest('tr')!;
    const unitRowB = screen.getByText('Ban Kiểm soát').closest('tr')!;
    expect(unitRowA.cells).toHaveLength(rowA.cells.length);
    expect(unitRowA.cells[1].textContent).toBe('1');
    expect(unitRowA.cells[2].textContent).toContain('Phòng Kế toán');
    expect(unitRowA.cells[2].textContent).toContain('02838123456');
    expect(unitRowA.cells[3].textContent).toBe('Công khai');
    expect(unitRowB.cells[1].textContent).toBe('2');
    expect(unitRowB.cells[3].textContent).toBe('Nội bộ');
    // Các dòng Đơn vị nằm ngay dưới Khối A
    expect(rowA.nextElementSibling).toBe(unitRowA);
    expect(unitRowA.nextElementSibling).toBe(unitRowB);
    expect(screen.queryByText('Phòng Kỹ thuật')).not.toBeInTheDocument();

    // Bấm vào chỗ khác trên dòng Khối A: đóng lại
    fireEvent.click(rowA.querySelector('td')!);
    expect(regionA).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Phòng Kế toán')).not.toBeInTheDocument();

    // Bấm nút Sửa trên dòng Khối: mở hộp thoại sửa, không sổ danh sách Đơn vị
    fireEvent.click(within(rowA).getByTitle('Chỉnh sửa'));
    expect(await screen.findByText('Cập Nhật Khối / Khu Vực')).toBeInTheDocument();
    expect(regionA).toHaveAttribute('aria-expanded', 'false');
  });

  it('tab Khối: khi đang tải danh sách Đơn vị thì hiện "Đang tải", không hiện "Chưa có dữ liệu" hay "0 đơn vị"', async () => {
    let resolveUnits: (value: unknown) => void = () => {};
    const pendingUnits = new Promise((resolve) => {
      resolveUnits = resolve;
    });
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/regions/')) return [{ id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 1 }];
      if (endpoint.includes('/units/') && endpoint.includes('all=true')) return pendingUnits;
      if (endpoint.includes('/units/')) return { count: 0, next: null, previous: null, results: [] };
      return [];
    });

    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Đang tải dữ liệu...')).toBeInTheDocument();
    expect(screen.queryByText('Chưa có dữ liệu nào.')).not.toBeInTheDocument();
    // Danh sách Khối đã về nhưng danh sách Đơn vị chưa về: vẫn đang tải
    await waitFor(() => expect(mockedApiClient).toHaveBeenCalledWith(expect.stringContaining('/regions/?page=1')));
    await act(async () => {});
    expect(screen.getByText('Đang tải dữ liệu...')).toBeInTheDocument();
    expect(screen.queryByText('0 đơn vị')).not.toBeInTheDocument();

    resolveUnits([{ id: 7, khoi: 1, khoi_ten: 'Khối A', stt_uu_tien: 1, ten: 'Phòng Hành chính', is_public: true }]);
    const regionA = await screen.findByRole('button', { name: 'Khối A' });
    expect(regionA.closest('tr')!.textContent).toContain('1 đơn vị');
    expect(screen.queryByText('Đang tải dữ liệu...')).not.toBeInTheDocument();
  });
  describe('lỗi hiển thị và thao tác (trang Phòng ban)', () => {
    const unit = {
      id: 1,
      khoi: 1,
      khoi_ten: 'Khối A',
      stt_uu_tien: 1,
      ten: 'Phòng Kế toán',
      dien_thoai: '02838123456',
      email: 'ketoan@itc.edu.vn',
      dia_chi: 'Tầng 2',
      is_public: true,
    };

    function mockApi(permissions: string[] = ['view_donvi', 'change_donvi'], regionsPage?: unknown) {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions };
        if (endpoint.includes('/regions/') && endpoint.includes('page=') && regionsPage) return regionsPage;
        if (endpoint.includes('/regions/')) return [{ id: 1, ten: 'Khối A', thu_tu_hien_thi: 1, don_vi_count: 1 }];
        if (endpoint.includes('/units/') && endpoint.includes('all=true')) return [unit];
        if (endpoint.includes('/units/')) return { count: 1, next: null, previous: null, results: [unit] };
        return [];
      });
    }

    function renderPage() {
      return render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );
    }

    it('hủy sửa Khối rồi mở lại cùng Khối: form về tên gốc, không giữ phần đã gõ dở', async () => {
      mockApi();
      renderPage();
      const row = (await screen.findByRole('button', { name: 'Khối A' })).closest('tr')!;

      fireEvent.click(within(row).getByTitle('Chỉnh sửa'));
      const nameInput = await screen.findByPlaceholderText(/Nhập tên khối hoặc khu vực/);
      fireEvent.change(nameInput, { target: { value: 'Khối A đã sửa QA' } });
      fireEvent.click(screen.getByRole('button', { name: 'Hủy bỏ' }));

      fireEvent.click(within(row).getByTitle('Chỉnh sửa'));
      expect(await screen.findByPlaceholderText(/Nhập tên khối hoặc khu vực/)).toHaveValue('Khối A');
    });

    it('hủy sửa Đơn vị rồi mở lại cùng Đơn vị: form về tên gốc, không giữ phần đã gõ dở', async () => {
      mockApi();
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      openUnitsTab();
      const row = (await screen.findByText('Phòng Kế toán')).closest('tr')!;

      fireEvent.click(within(row).getByTitle('Chỉnh sửa'));
      const nameInput = await screen.findByPlaceholderText(/Nhập tên đơn vị hoặc phòng ban/);
      fireEvent.change(nameInput, { target: { value: 'Phòng Kế toán đã sửa QA' } });
      fireEvent.click(screen.getByRole('button', { name: 'Hủy bỏ' }));

      fireEvent.click(within(row).getByTitle('Chỉnh sửa'));
      expect(await screen.findByPlaceholderText(/Nhập tên đơn vị hoặc phòng ban/)).toHaveValue('Phòng Kế toán');
    });

    it('thiếu quyền xem (403): báo thiếu quyền một lần, không báo lỗi mạng, không hiện số 0 hay "chưa có dữ liệu"', async () => {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions: [] };
        throw new apiClientModule.ApiError(403, { detail: 'organizations.messages.permissionDenied' });
      });
      renderPage();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent('Bạn không có quyền thực hiện thao tác này.');
      expect(screen.getAllByText('Bạn không có quyền thực hiện thao tác này.')).toHaveLength(1);
      expect(screen.queryByText(/kết nối mạng/i)).not.toBeInTheDocument();
      expect(screen.queryByText('Chưa có dữ liệu nào.')).not.toBeInTheDocument();
      const tabs = screen.getAllByRole('button').filter((b) => /Khối \/ Khu vực|Đơn vị \/ Phòng ban/i.test(b.textContent || ''));
      expect(tabs.length).toBeGreaterThan(0);
      // Huy hiệu số đếm (span) biến mất khi không có quyền, không hiện số 0 gây hiểu lầm.
      tabs.forEach((tab) => expect(tab.querySelector('span')).toBeNull());
    });

    it('lỗi khác 403 vẫn báo không tải được danh sách', async () => {
      mockedApiClient.mockImplementation(async (endpoint: string) => {
        if (endpoint.includes('/auth/me/permissions/')) return { is_superuser: false, permissions: [] };
        throw new apiClientModule.ApiError(500, { detail: 'server error' });
      });
      renderPage();

      expect((await screen.findAllByText(/Không thể tải danh sách dữ liệu/)).length).toBeGreaterThan(0);
      expect(screen.queryByText('Bạn không có quyền thực hiện thao tác này.')).not.toBeInTheDocument();
    });

    it('nút phân trang chỉ có biểu tượng nên phải có nhãn cho trình đọc màn hình (cả hai tab)', async () => {
      const regions = Array.from({ length: 10 }, (_, i) => ({ id: i + 1, ten: `Khối ${i + 1}`, thu_tu_hien_thi: i + 1, don_vi_count: 0 }));
      mockApi(['view_donvi'], { count: 12, next: null, previous: null, results: regions });
      renderPage();

      expect(await screen.findByRole('button', { name: 'Trang trước' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Trang sau' })).toBeEnabled();
    });

    it('bảng Đơn vị có móc cho dạng thẻ trên điện thoại: nhãn từng ô, ô thao tác, chừa chỗ dưới cho nút AI', async () => {
      mockApi();
      const { container } = renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      openUnitsTab();
      const row = (await screen.findByText('Phòng Kế toán')).closest('tr')!;

      expect(row.className).toContain('units-table__row');
      expect(row.querySelector('.units-table__cell--region')).toHaveAttribute('data-label', 'Khối trực thuộc');
      expect(row.querySelector('.units-table__cell--phone')).toHaveAttribute('data-label', 'Điện thoại');
      expect(row.querySelector('.units-table__cell--email')).toHaveAttribute('data-label', 'Email');
      expect(row.querySelector('.units-table__cell--actions')).toBeInTheDocument();
      expect(container.querySelector('table')!.className).toContain('units-table');
      expect((container.firstElementChild as HTMLElement).className).toContain('pb-24');
    });

    it('địa chỉ Đơn vị ẩn trên điện thoại (dưới md, cùng mốc với dạng thẻ) và hiện từ md trở lên', async () => {
      mockApi();
      renderPage();
      await screen.findByRole('button', { name: 'Khối A' });
      openUnitsTab();
      const row = (await screen.findByText('Phòng Kế toán')).closest('tr')!;

      const address = within(row).getByText('Tầng 2').closest('div')!;
      expect(address.className).toContain('hidden');
      expect(address.className).toContain('md:flex');
      expect(address.querySelector('.fa-location-dot')).toBeInTheDocument();
    });
  });
});
