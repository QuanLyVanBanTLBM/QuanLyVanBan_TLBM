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

    it('người chỉ có quyền xem không thấy nút Xuất Excel, Thêm, Sửa, Xóa', async () => {
      mockApi(['view_donvi']);
      renderPage();
      await waitFor(() => expect(screen.getByText('Phòng Kế hoạch')).toBeInTheDocument());

      expect(screen.queryByRole('button', { name: /Xuất Excel/i })).not.toBeInTheDocument();
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
      await waitFor(() => expect(screen.getByRole('button', { name: /Xuất Excel/i })).toBeInTheDocument());
      expect(screen.getByRole('button', { name: /Thêm đơn vị/i })).toBeInTheDocument();
      expect(screen.getByTitle('Chỉnh sửa')).toBeInTheDocument();
      expect(screen.getByTitle('Xóa')).toBeInTheDocument();
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
});
