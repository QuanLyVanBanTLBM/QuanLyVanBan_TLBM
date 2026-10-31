import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import InboundDocumentPage from './InboundDocumentPage';
import * as apiClientModule from '@lib/apiClient';
import { DocumentItem } from '@app-types/document';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClientModule>('@lib/apiClient');
  const mockClient = vi.fn() as unknown as typeof apiClientModule.apiClient;
  mockClient.get = vi.fn();
  mockClient.post = vi.fn();
  mockClient.put = vi.fn();
  mockClient.delete = vi.fn();

  return {
    ...actual,
    default: mockClient,
    apiClient: mockClient,
    downloadBlob: vi.fn(),
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);

const mockDocuments: DocumentItem[] = [
  {
    id: 101,
    so_hieu: '101/QĐ-TLBM',
    so_thu_tu: 1,
    nam: 2026,
    loai: 'DEN',
    loai_display: 'Văn bản Đến',
    ngay_den: '2026-03-15T08:00:00Z',
    ngay_van_ban: '2026-03-10',
    ngay_ban_hanh: '2026-03-10',
    trich_yeu: 'Quyết định triển khai công tác chuyển đổi số',
    noi_ban_hanh: 'Bộ GD&ĐT',
    nguoi_ky: 'Thứ trưởng',
    hieu_luc: 'CON_HIEU_LUC',
    hieu_luc_display: 'Còn hiệu lực',
    hien_thi: true,
    attachment_count: 2,
    created_at: '2026-03-15T08:00:00Z',
  },
  {
    id: 102,
    so_hieu: '102/TB-TLBM',
    so_thu_tu: 2,
    nam: 2026,
    loai: 'DEN',
    loai_display: 'Văn bản Đến',
    ngay_den: '2026-03-16T09:00:00Z',
    ngay_van_ban: '2026-03-12',
    ngay_ban_hanh: '2026-03-12',
    trich_yeu: 'Thông báo kế hoạch kiểm tra',
    noi_ban_hanh: 'Sở GD&ĐT',
    nguoi_ky: 'Giám đốc',
    hieu_luc: 'HET_HIEU_LUC',
    hieu_luc_display: 'Hết hiệu lực',
    hien_thi: true,
    attachment_count: 1,
    created_at: '2026-03-16T09:00:00Z',
  },
];

describe('InboundDocumentPage Component (Phân hệ Văn bản Đến)', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockedApiClient.get.mockImplementation(async (url: string) => {
      if (url.includes('/api/documents/years/')) {
        return [2026, 2025];
      }
      if (url.includes('page_size=1000')) {
        return {
          count: 2,
          results: mockDocuments,
        };
      }
      if (url.includes('/api/documents/101/')) {
        return {
          id: 101,
          so_hieu: '101/QĐ-TLBM',
          so_thu_tu: 1,
          nam: 2026,
          loai: 'DEN',
          trich_yeu: 'Quyết định triển khai công tác chuyển đổi số',
          hieu_luc: 'CON_HIEU_LUC',
          noi_ban_hanh: 'Bộ GD&ĐT',
          nguoi_ky: 'Thứ trưởng',
          attachments: [],
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          count: mockDocuments.length,
          results: mockDocuments,
        };
      }
      return { count: 0, results: [] };
    });
  });

  const renderComponent = () =>
    render(
      <MemoryRouter>
        <InboundDocumentPage />
      </MemoryRouter>
    );

  describe('Happy Path (Kịch bản phổ thông)', () => {
    it('render tiêu đề trang, thanh công cụ và danh sách văn bản ban đầu', async () => {
      renderComponent();

      expect(screen.getByText('Quản Lý Văn Bản Đến')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Thêm mới/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /(Import Excel|Nhập Excel)/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Xuất Excel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Làm mới/i })).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('101/QĐ-TLBM')).toBeInTheDocument();
        expect(screen.getByText('Quyết định triển khai công tác chuyển đổi số')).toBeInTheDocument();
        expect(screen.getByText('102/TB-TLBM')).toBeInTheDocument();
      });
    });

    it('hiển thị số lượng văn bản còn hiệu lực trên card thống kê', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Tổng số văn bản đến')).toBeInTheDocument();
        // 1 văn bản CON_HIEU_LUC
        const activeBadges = screen.getAllByText('1');
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it('mở modal Thêm mới khi bấm nút Thêm mới', async () => {
      renderComponent();

      const addButton = screen.getByRole('button', { name: /Thêm mới/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/Thêm Mới Văn Bản/i)).toBeInTheDocument();
      });
    });

    it('mở modal Nhập Excel khi bấm nút Nhập Excel và chọn tác vụ', async () => {
      renderComponent();

      const importButton = screen.getByRole('button', { name: /(Import Excel|Nhập Excel)/i });
      fireEvent.click(importButton);

      // Menu dropdown sổ ra lựa chọn: Nhập văn bản thường hoặc Nhập văn bản hạn chế
      const normalOption = screen.getByText('Nhập văn bản thường');
      expect(screen.getByText('Nhập văn bản hạn chế')).toBeInTheDocument();

      fireEvent.click(normalOption);

      await waitFor(() => {
        expect(screen.getByText(/Nhập Văn Bản.*Từ File Excel/i)).toBeInTheDocument();
      });
    });

    it('làm mới danh sách khi bấm nút Làm mới', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('101/QĐ-TLBM')).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /Làm mới/i });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('/api/documents/'));
      });
    });
  });

  describe('Edge Cases & Error Handling', () => {
    it('hiển thị trạng thái rỗng (Empty State) khi không có văn bản nào', async () => {
      mockedApiClient.get.mockImplementation(async (url: string) => {
        if (url.includes('/api/documents/years/')) return [];
        if (url.includes('page_size=1000')) return { count: 0, results: [] };
        return { count: 0, results: [] };
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/Không tìm thấy văn bản đến nào/i)).toBeInTheDocument();
      });
    });

    it('hiển thị thông báo lỗi và nút Thử lại khi API gặp sự cố (Network Error)', async () => {
      mockedApiClient.get.mockImplementation(async (url: string) => {
        if (url.includes('page_size=1000') || url.includes('/api/documents/years/')) {
          return [];
        }
        throw new Error('Lỗi kết nối máy chủ backend');
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/Lỗi kết nối máy chủ backend/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Thử lại/i })).toBeInTheDocument();
      });
    });

    it('hỗ trợ toggle bộ lọc nhanh trạng thái Còn hiệu lực', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('101/QĐ-TLBM')).toBeInTheDocument();
      });

      const activeFilterBtn = screen.getByTitle(/Lọc danh sách theo văn bản còn hiệu lực/i);
      fireEvent.click(activeFilterBtn);

      await waitFor(() => {
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('hieu_luc=HIEU_LUC'));
      });
    });

    it('mở ConfirmModal khi yêu cầu xóa và hủy thao tác an toàn', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('101/QĐ-TLBM')).toBeInTheDocument();
      });

      // Mở menu thao tác của dòng đầu tiên
      const actionMenus = screen.getAllByTitle('Tác vụ');
      fireEvent.click(actionMenus[0]);

      const deleteOption = await screen.findByText('Xóa văn bản');
      fireEvent.click(deleteOption);

      await waitFor(() => {
        expect(screen.getByText('Xác nhận xóa văn bản đến')).toBeInTheDocument();
        expect(screen.getByText(/Bạn có chắc chắn muốn xóa văn bản "101\/QĐ-TLBM" không/i)).toBeInTheDocument();
      });

      // Bấm nút Hủy bỏ
      const cancelBtn = screen.getByRole('button', { name: /Hủy bỏ/i });
      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(screen.queryByText('Xác nhận xóa văn bản đến')).not.toBeInTheDocument();
      });
    });

    it('thực hiện xóa văn bản khi xác nhận và hiển thị thông báo thành công', async () => {
      mockedApiClient.delete.mockResolvedValueOnce({ success: true });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('101/QĐ-TLBM')).toBeInTheDocument();
      });

      const actionMenus = screen.getAllByTitle('Tác vụ');
      fireEvent.click(actionMenus[0]);

      const deleteOption = await screen.findByText('Xóa văn bản');
      fireEvent.click(deleteOption);

      await waitFor(() => {
        expect(screen.getByText('Xác nhận xóa văn bản đến')).toBeInTheDocument();
      });

      const confirmBtn = screen.getByRole('button', { name: 'Xóa văn bản' });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(mockedApiClient.delete).toHaveBeenCalledWith('/api/documents/101/?loai=DEN');
        expect(screen.getByText(/Đã xóa văn bản "101\/QĐ-TLBM" thành công/i)).toBeInTheDocument();
      });
    });

    it('hiển thị badge lọc và gửi param loai_van_ban khi có trên URL, và cho phép bỏ lọc', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/incoming?loai_van_ban=5']}>
          <InboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Đang lọc danh sách theo Loại văn bản/i)).toBeInTheDocument();
        expect(screen.getByText('#5')).toBeInTheDocument();
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('loai_van_ban=5'));
      });

      const clearBtn = screen.getByRole('button', { name: /Bỏ lọc/i });
      fireEvent.click(clearBtn);

      await waitFor(() => {
        expect(screen.queryByText(/Đang lọc danh sách theo Loại văn bản/i)).not.toBeInTheDocument();
      });
    });

    it('hiển thị badge lọc và gửi param pham_vi khi có trên URL, và cho phép bỏ lọc', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/incoming?loai_van_ban=5&pham_vi=HAN_CHE']}>
          <InboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Đang lọc danh sách theo phạm vi/i)).toBeInTheDocument();
        expect(screen.getByText(/Văn bản hạn chế \(Mật\)/i)).toBeInTheDocument();
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('pham_vi=HAN_CHE'));
      });

      const clearPhamViBtn = screen.getByTitle('Xóa bộ lọc phạm vi');
      fireEvent.click(clearPhamViBtn);

      await waitFor(() => {
        expect(screen.queryByText(/Đang lọc danh sách theo phạm vi/i)).not.toBeInTheDocument();
      });
    });
  });
});

