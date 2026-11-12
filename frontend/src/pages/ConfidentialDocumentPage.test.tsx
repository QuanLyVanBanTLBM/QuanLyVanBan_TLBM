import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ConfidentialDocumentPage from './ConfidentialDocumentPage';
import * as apiClientModule from '@lib/apiClient';
import { DocumentItem } from '@app-types/document';
import { resetPermissionsCache } from '@lib/permissions';

const ALL_DOC_PERMS = [
  'view_vanbanden',
  'add_vanbanden',
  'change_vanbanden',
  'delete_vanbanden',
  'import_vanbanden',
  'export_vanbanden',
  'view_vanbandi',
  'add_vanbandi',
  'change_vanbandi',
  'delete_vanbandi',
  'import_vanbandi',
  'export_vanbandi',
];

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

const mockConfidentialDocuments: DocumentItem[] = [
  {
    id: 301,
    so_hieu: '01/BC-MẬT',
    nam: 2026,
    loai: 'MAT',
    loai_display: 'Văn bản Mật',
    ngay_den: '2026-03-25T08:00:00Z',
    ngay_van_ban: '2026-03-25',
    trich_yeu: 'Báo cáo phương án bảo vệ bí mật công tác tuyển sinh năm 2026',
    noi_ban_hanh: 'Hội đồng tuyển sinh',
    nguoi_ky: 'Chủ tịch Hội đồng',
    hieu_luc: 'CON_HIEU_LUC',
    hieu_luc_display: 'Còn hiệu lực',
    hien_thi: true,
    pham_vi: 'HAN_CHE',
    attachment_count: 2,
    created_at: '2026-03-25T08:00:00Z',
  },
  {
    id: 302,
    so_hieu: '02/KH-MẬT',
    nam: 2026,
    loai: 'MAT',
    loai_display: 'Văn bản Mật',
    ngay_den: '2026-03-26T09:00:00Z',
    ngay_van_ban: '2026-03-26',
    trich_yeu: 'Kế hoạch an ninh mạng trọng yếu nội bộ nhà trường',
    noi_ban_hanh: 'Ban Giám hiệu',
    nguoi_ky: 'Hiệu trưởng',
    hieu_luc: 'HET_HIEU_LUC',
    hieu_luc_display: 'Hết hiệu lực',
    hien_thi: true,
    pham_vi: 'HAN_CHE',
    attachment_count: 1,
    created_at: '2026-03-26T09:00:00Z',
  },
];

describe('ConfidentialDocumentPage Component (Phân hệ Văn bản Mật)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();

    const handleCall = async (url: string) => {
      if (url.includes('/auth/me/permissions/')) {
        return {
          is_superuser: false,
          permissions: ALL_DOC_PERMS,
        };
      }
      if (url.includes('/api/documents/years/')) {
        return [2026, 2025];
      }
      if (url.includes('page_size=1000')) {
        return {
          count: 2,
          results: mockConfidentialDocuments,
        };
      }
      if (url.includes('/api/documents/301/')) {
        return {
          id: 301,
          so_hieu: '01/BC-MẬT',
          nam: 2026,
          loai: 'MAT',
          trich_yeu: 'Báo cáo phương án bảo vệ bí mật công tác tuyển sinh năm 2026',
          hieu_luc: 'CON_HIEU_LUC',
          noi_ban_hanh: 'Hội đồng tuyển sinh',
          nguoi_ky: 'Chủ tịch Hội đồng',
          pham_vi: 'HAN_CHE',
          attachments: [],
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          count: mockConfidentialDocuments.length,
          results: mockConfidentialDocuments,
        };
      }
      if (url.includes('/api/accounts/staffs/')) {
        return [];
      }
      return { count: 0, results: [] };
    };

    mockedApiClient.mockImplementation(handleCall as unknown as typeof apiClientModule.apiClient);
    mockedApiClient.get.mockImplementation(handleCall);
  });

  it('renders header, security notice banner, and document table', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    // Kiểm tra tiêu đề trang
    expect(screen.getByRole('heading', { name: /Quản Lý Văn Bản Mật/i })).toBeInTheDocument();

    // Kiểm tra thẻ cảnh báo bảo mật
    expect(screen.getByText(/Nguyên tắc bảo mật văn bản nội bộ/i)).toBeInTheDocument();

    // Chờ dữ liệu nạp lên bảng
    await waitFor(() => {
      expect(screen.getByText('01/BC-MẬT')).toBeInTheDocument();
      expect(screen.getByText('02/KH-MẬT')).toBeInTheDocument();
    });

    // Kiểm tra nội dung trích yếu
    expect(
      screen.getByText(/Báo cáo phương án bảo vệ bí mật công tác tuyển sinh/i)
    ).toBeInTheDocument();
  });

  it('queries backend with loai=MAT parameter', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockedApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('loai=MAT')
      );
    });
  });

  it('displays active document count in stats card', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      // 1 văn bản còn hiệu lực (301) trong mock
      expect(screen.getByText(/văn bản mật còn hiệu lực/i)).toBeInTheDocument();
    });
  });

  it('opens detail modal when clicking on document link', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('01/BC-MẬT')).toBeInTheDocument();
    });

    const docBtn = screen.getByText('01/BC-MẬT');
    fireEvent.click(docBtn);

    await waitFor(() => {
      expect(screen.getByText(/Chi Tiết Văn Bản Mật/i)).toBeInTheDocument();
    });
  });

  it('opens new document modal when clicking Thêm mới button', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    const addBtn = await screen.findByRole('button', { name: /Thêm mới/i });
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(screen.getByText(/Thêm Mới Văn Bản Mật/i)).toBeInTheDocument();
    });
  });

  it('opens import Excel modal when clicking Nhập Excel button', async () => {
    render(
      <MemoryRouter>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    const importBtn = await screen.findByRole('button', { name: /(Import Excel|Nhập Excel)/i });
    fireEvent.click(importBtn);

    await waitFor(() => {
      expect(screen.getByText(/Nhập Văn Bản Mật Từ File Excel/i)).toBeInTheDocument();
    });
  });

  it('tự động mở modal Chi tiết khi có query param ?detail=301 trên URL', async () => {
    render(
      <MemoryRouter initialEntries={['/documents/confidential?detail=301']}>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Chi Tiết Văn Bản Mật/i)).toBeInTheDocument();
    });
  });

  it('tự động mở modal Thêm mới khi có query param ?action=create trên URL', async () => {
    render(
      <MemoryRouter initialEntries={['/documents/confidential?action=create']}>
        <ConfidentialDocumentPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Thêm Mới Văn Bản Mật/i)).toBeInTheDocument();
    });
  });
});
