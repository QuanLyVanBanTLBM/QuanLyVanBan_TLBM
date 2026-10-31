import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OutboundDocumentPage from './OutboundDocumentPage';
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

const mockOutboundDocuments: DocumentItem[] = [
  {
    id: 201,
    so_hieu: '201/QĐ-TLBM',
    so_thu_tu: 1,
    nam: 2026,
    loai: 'DI',
    loai_display: 'Văn bản Đi',
    ngay_den: '2026-03-20T08:00:00Z',
    ngay_van_ban: '2026-03-20',
    ngay_ban_hanh: '2026-03-20',
    trich_yeu: 'Quyết định ban hành quy chế làm việc nội bộ',
    noi_ban_hanh: 'Trường Đại học TLBM',
    nguoi_ky: 'Hiệu trưởng',
    hieu_luc: 'CON_HIEU_LUC',
    hieu_luc_display: 'Còn hiệu lực',
    hien_thi: true,
    attachment_count: 1,
    created_at: '2026-03-20T08:00:00Z',
  },
  {
    id: 202,
    so_hieu: '202/TB-TLBM',
    so_thu_tu: 2,
    nam: 2026,
    loai: 'DI',
    loai_display: 'Văn bản Đi',
    ngay_den: '2026-03-21T09:00:00Z',
    ngay_van_ban: '2026-03-21',
    ngay_ban_hanh: '2026-03-21',
    trich_yeu: 'Thông báo lịch nghỉ lễ Giỗ Tổ Hùng Vương',
    noi_ban_hanh: 'Phòng Hành chính - Tổng hợp',
    nguoi_ky: 'Trưởng phòng',
    hieu_luc: 'HET_HIEU_LUC',
    hieu_luc_display: 'Hết hiệu lực',
    hien_thi: true,
    attachment_count: 0,
    created_at: '2026-03-21T09:00:00Z',
  },
];

describe('OutboundDocumentPage Component (Phân hệ Văn bản Đi)', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockedApiClient.get.mockImplementation(async (url: string) => {
      if (url.includes('/api/documents/years/')) {
        return [2026, 2025];
      }
      if (url.includes('page_size=1000')) {
        return {
          count: 2,
          results: mockOutboundDocuments,
        };
      }
      if (url.includes('/api/documents/201/')) {
        return {
          id: 201,
          so_hieu: '201/QĐ-TLBM',
          so_thu_tu: 1,
          nam: 2026,
          loai: 'DI',
          trich_yeu: 'Quyết định ban hành quy chế làm việc nội bộ',
          hieu_luc: 'CON_HIEU_LUC',
          noi_ban_hanh: 'Trường Đại học TLBM',
          nguoi_ky: 'Hiệu trưởng',
          attachments: [],
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          count: mockOutboundDocuments.length,
          results: mockOutboundDocuments,
        };
      }
      return { count: 0, results: [] };
    });
  });

  const renderComponent = () =>
    render(
      <MemoryRouter>
        <OutboundDocumentPage />
      </MemoryRouter>
    );

  describe('Happy Path (Kịch bản phổ thông)', () => {
    it('render tiêu đề trang, thanh công cụ và danh sách văn bản đi', async () => {
      renderComponent();

      expect(screen.getByText('Quản Lý Văn Bản Đi')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Thêm mới/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /(Import Excel|Nhập Excel)/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Xuất Excel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Làm mới/i })).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('201/QĐ-TLBM')).toBeInTheDocument();
        expect(screen.getByText('Quyết định ban hành quy chế làm việc nội bộ')).toBeInTheDocument();
        expect(screen.getByText('202/TB-TLBM')).toBeInTheDocument();
        expect(screen.getAllByText(/Số đi/i).length).toBeGreaterThan(0);
      });
    });

    it('gọi API backend với tham số loai=DI', async () => {
      renderComponent();

      await waitFor(() => {
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('loai=DI'));
      });
    });

    it('hiển thị số lượng văn bản đi còn hiệu lực trên card thống kê', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Tổng số văn bản đi')).toBeInTheDocument();
        const activeBadges = screen.getAllByText('1');
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it('mở modal Thêm mới khi bấm nút Thêm mới', async () => {
      renderComponent();

      const addButton = screen.getByRole('button', { name: /Thêm mới/i });
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/Thêm Mới Văn Bản Đi/i)).toBeInTheDocument();
      });
    });

    it('làm mới danh sách khi bấm nút Làm mới', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('201/QĐ-TLBM')).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /Làm mới/i });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('loai=DI'));
      });
    });
  });

  describe('Edge Cases & Filtering', () => {
    it('hiển thị trạng thái rỗng khi không có văn bản đi nào', async () => {
      mockedApiClient.get.mockImplementation(async (url: string) => {
        if (url.includes('/api/documents/years/')) return [];
        if (url.includes('page_size=1000')) return { count: 0, results: [] };
        return { count: 0, results: [] };
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/Không tìm thấy văn bản đi nào/i)).toBeInTheDocument();
      });
    });

    it('hiển thị thông báo lỗi và nút Thử lại khi API gặp sự cố', async () => {
      mockedApiClient.get.mockImplementation(async (url: string) => {
        if (url.includes('page_size=1000') || url.includes('/api/documents/years/')) {
          return [];
        }
        throw new Error('Lỗi kết nối máy chủ');
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText(/Lỗi kết nối máy chủ/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Thử lại/i })).toBeInTheDocument();
      });
    });

    it('hiển thị badge lọc Loại văn bản khi nhận param từ URL và cho phép bấm Bỏ lọc', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/outgoing?loai_van_ban=3']}>
          <OutboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Đang lọc danh sách theo Loại văn bản/i)).toBeInTheDocument();
        expect(screen.getByText('#3')).toBeInTheDocument();
        expect(mockedApiClient.get).toHaveBeenCalledWith(expect.stringContaining('loai_van_ban=3'));
      });

      const clearBtn = screen.getByRole('button', { name: /Bỏ lọc/i });
      fireEvent.click(clearBtn);

      await waitFor(() => {
        expect(screen.queryByText(/Đang lọc danh sách theo Loại văn bản/i)).not.toBeInTheDocument();
      });
    });

    it('hiển thị badge lọc và gửi param pham_vi khi có trên URL cho văn bản đi', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/outgoing?loai_van_ban=8&pham_vi=HAN_CHE']}>
          <OutboundDocumentPage />
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

    it('mở ConfirmModal khi yêu cầu xóa và thực hiện xóa thành công', async () => {
      mockedApiClient.delete.mockResolvedValueOnce({ success: true });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('201/QĐ-TLBM')).toBeInTheDocument();
      });

      const actionMenus = screen.getAllByTitle('Tác vụ');
      fireEvent.click(actionMenus[0]);

      const deleteOption = await screen.findByText('Xóa văn bản');
      fireEvent.click(deleteOption);

      await waitFor(() => {
        expect(screen.getByText('Xác nhận xóa văn bản đi')).toBeInTheDocument();
      });

      const confirmBtn = screen.getByRole('button', { name: 'Xóa văn bản' });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(mockedApiClient.delete).toHaveBeenCalledWith('/api/documents/201/?loai=DI');
        expect(screen.getByText(/Đã xóa văn bản "201\/QĐ-TLBM" thành công/i)).toBeInTheDocument();
      });
    });

    it('tự động mở modal Chi tiết khi có query param ?detail=201 trên URL', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/outgoing?detail=201']}>
          <OutboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Chi Tiết Văn Bản Đi/i)).toBeInTheDocument();
      });
    });

    it('tự động mở modal Thêm mới khi có query param ?action=create trên URL', async () => {
      render(
        <MemoryRouter initialEntries={['/documents/outgoing?action=create']}>
          <OutboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Thêm Mới Văn Bản Đi/i)).toBeInTheDocument();
      });
    });

    it('hiển thị số lượng văn bản theo kết quả tham chiếu hồ sơ trên Top Card', async () => {
      mockedApiClient.get.mockImplementation(async (url: string) => {
        if (url.includes('/api/documents/years/')) {
          return [2026];
        }
        if (url.includes('/api/records/')) {
          return [];
        }
        if (url.includes('page_size=1000')) {
          return {
            count: 12,
            results: Array.from({ length: 12 }, (_, i) => ({
              ...mockOutboundDocuments[0],
              id: 300 + i,
            })),
          };
        }
        return {
          count: 1,
          results: [mockOutboundDocuments[0]],
        };
      });

      render(
        <MemoryRouter initialEntries={['/documents/outgoing?ho_so=1&loai_van_ban=5']}>
          <OutboundDocumentPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('201/QĐ-TLBM')).toBeInTheDocument();
      });

      const ones = screen.getAllByText('1');
      expect(ones.length).toBeGreaterThanOrEqual(1);
      expect(screen.queryByText('12')).not.toBeInTheDocument();
    });
  });
});
