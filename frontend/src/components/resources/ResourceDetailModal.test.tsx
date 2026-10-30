import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ResourceDetailModal } from './ResourceDetailModal';
import { ResourceItem } from '@app-types/resource';
import { apiClientBlob, downloadBlob } from '@lib/apiClient';

vi.mock('@lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
  apiClientBlob: vi.fn(),
  downloadBlob: vi.fn(),
}));

const baseDoc: ResourceItem = {
  id: 10,
  dm_tai_lieu: 1,
  dm_tai_lieu_name: 'Thư mục Quy chế',
  loai_tai_lieu: [1],
  loai_tai_lieu_names: ['Quy chế'],
  ky_hieu: 'QC-2026',
  tieu_de: 'Quy chế văn thư lưu trữ điện tử',
  ngay_dang: '2026-01-01',
  noi_ban_hanh: 'Ban Giám Đốc',
  hieu_luc: 'CON_HIEU_LUC',
  file_dinh_kem: '/media/test.pdf',
  hien_thi: 'TAT_CA',
  nguoi_tao_name: 'Quản trị viên',
};

describe('ResourceDetailModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders scheduled expiration notice and active badge when expiration date is in the future', () => {
    const futureDoc: ResourceItem = {
      ...baseDoc,
      hieu_luc: 'HET_HIEU_LUC', // Cài đặt hết hạn trước nhưng ngày ở tương lai
      ngay_het_hieu_luc: '2099-12-31',
    };

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={futureDoc}
      />
    );

    // Vẫn hiển thị Còn hiệu lực kèm ngày hết hạn
    expect(screen.getByText(/Còn hiệu lực/i)).toBeInTheDocument();
    expect(screen.getAllByText(/31\/12\/2099/).length).toBeGreaterThan(0);
    // Hiển thị banner thông báo văn bản đã được lên lịch hết hiệu lực
    expect(
      screen.getByText(/đã được lên lịch hết hiệu lực vào ngày/i)
    ).toBeInTheDocument();
  });

  it('renders expired banner when expiration date has passed', () => {
    const pastDoc: ResourceItem = {
      ...baseDoc,
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: '2020-01-01',
    };

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={pastDoc}
      />
    );

    // Đã hết hạn tự động
    expect(screen.getByText(/Văn bản này hiện đã hết hiệu lực thi hành/i)).toBeInTheDocument();
  });

  it('opens PDF or image attachment in a new tab when clicking preview', async () => {
    const docWithPdf: ResourceItem = {
      ...baseDoc,
      attachments: [
        {
          id: 1,
          name: 'tai_lieu.pdf',
          path: '/api/resources/attachments/1/view/',
          file_size: 1024,
        },
      ],
    };

    const mockBlob = new Blob(['pdf-data'], { type: 'application/pdf' });
    vi.mocked(apiClientBlob).mockResolvedValueOnce(mockBlob);
    const originalCreateObjectURL = window.URL.createObjectURL;
    const originalOpen = window.open;
    window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost:5173/uuid-pdf');
    window.open = vi.fn();

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={docWithPdf}
      />
    );

    const previewBtn = screen.getByRole('button', { name: /Xem trước tệp đính kèm/i });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(apiClientBlob).toHaveBeenCalledWith('/api/resources/attachments/1/view/');
      expect(window.URL.createObjectURL).toHaveBeenCalled();
      expect(window.open).toHaveBeenCalledWith('blob:http://localhost:5173/uuid-pdf', '_blank');
      expect(downloadBlob).not.toHaveBeenCalled();
    });

    window.URL.createObjectURL = originalCreateObjectURL;
    window.open = originalOpen;
  });

  it('downloads ZIP, DOCX, or Excel file directly when clicking preview or card', async () => {
    const docWithDocx: ResourceItem = {
      ...baseDoc,
      attachments: [
        {
          id: 2,
          name: 'bieu_mau.docx',
          path: '/api/resources/attachments/2/view/',
          file_size: 2048,
        },
      ],
    };

    const originalOpen = window.open;
    window.open = vi.fn();

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={docWithDocx}
      />
    );

    // Bấm vào card hoặc nút tải về của tệp docx
    const docxItem = screen.getByText('bieu_mau.docx');
    fireEvent.click(docxItem);

    await waitFor(() => {
      expect(downloadBlob).toHaveBeenCalledWith('/api/resources/attachments/2/download/', 'bieu_mau.docx');
      expect(window.open).not.toHaveBeenCalled();
    });

    window.open = originalOpen;
  });

  it('downloads attachment when clicking the download button', async () => {
    const docWithPdf: ResourceItem = {
      ...baseDoc,
      attachments: [
        {
          id: 3,
          name: 'tai_lieu_2.pdf',
          path: '/api/resources/attachments/3/view/',
          file_size: 1024,
        },
      ],
    };

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={docWithPdf}
      />
    );

    const downloadBtn = screen.getByRole('button', { name: /Tải về tai_lieu_2\.pdf/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(downloadBlob).toHaveBeenCalledWith('/api/resources/attachments/3/download/', 'tai_lieu_2.pdf');
    });
  });
});
