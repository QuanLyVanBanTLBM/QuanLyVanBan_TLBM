import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

    // Kiểm tra tên phòng ban hiển thị
    await waitFor(() => {
      expect(screen.getByText('Phòng Kế toán')).toBeInTheDocument();
    });

    // Chuyển sang Tab Khối
    const regionTab = screen.getByRole('button', { name: /Khối \/ Khu vực/i });
    fireEvent.click(regionTab);

    await waitFor(() => {
      expect(screen.getByText('Khối Cơ quan')).toBeInTheDocument();
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
      return render(
        <MemoryRouter>
          <OrganizationsPage />
        </MemoryRouter>
      );
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
      await waitFor(() => expect(screen.getByText('Khối Cơ quan', { selector: 'td' })).toBeInTheDocument());
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
});
