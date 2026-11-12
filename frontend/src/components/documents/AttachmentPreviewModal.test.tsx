import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { AttachmentPreviewModal } from './AttachmentPreviewModal';

vi.mock('@lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
  apiClientBlob: vi.fn().mockResolvedValue(new Blob(['test-blob'], { type: 'application/pdf' })),
  downloadBlob: vi.fn(),
}));

describe('AttachmentPreviewModal Component', () => {
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-preview-url');
    window.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
    vi.clearAllMocks();
  });

  it('không hiển thị khi isOpen = false', () => {
    render(
      <AttachmentPreviewModal
        isOpen={false}
        onClose={vi.fn()}
        target={{ name: 'document.pdf', size: 1024 }}
      />
    );
    expect(screen.queryByText('document.pdf')).not.toBeInTheDocument();
  });

  it('hiển thị xem trước file PDF khi truyền target hợp lệ', async () => {
    const handleClose = vi.fn();
    render(
      <AttachmentPreviewModal
        isOpen={true}
        onClose={handleClose}
        target={{
          name: 'KeHoach2026.pdf',
          size: 204800,
          url: '/media/documents/KeHoach2026.pdf',
        }}
      />
    );

    // Header hiển thị tên tệp và kích thước
    expect(screen.getAllByText('KeHoach2026.pdf').length).toBeGreaterThan(0);
    expect(screen.getByText(/200.*KB/i)).toBeInTheDocument();
    expect(screen.getByText('PDF')).toBeInTheDocument();

    // Nút đóng modal
    const closeBtn = screen.getByLabelText('Đóng popup xem trước');
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('hiển thị ảnh khi target là tệp hình ảnh (.png / .jpg)', async () => {
    const fakeImageFile = new File(['fake-png-content'], 'screenshot.png', { type: 'image/png' });
    render(
      <AttachmentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        target={{
          name: 'screenshot.png',
          size: 51200,
          file: fakeImageFile,
        }}
      />
    );

    expect(screen.getAllByText('screenshot.png').length).toBeGreaterThan(0);
    expect(screen.getByText('PNG')).toBeInTheDocument();
    const imageElement = await screen.findByAltText('screenshot.png');
    expect(imageElement).toBeInTheDocument();
    expect(imageElement).toHaveAttribute('src', 'blob:mock-preview-url');
  });

  it('hiển thị thông báo tải về đối với tệp định dạng cũ .doc hoặc không hỗ trợ xem trực tiếp', () => {
    render(
      <AttachmentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        target={{
          name: 'CongVanCu.doc',
          size: 153600,
          url: '/media/documents/CongVanCu.doc',
        }}
      />
    );

    expect(screen.getAllByText('CongVanCu.doc').length).toBeGreaterThan(0);
    expect(screen.getByText(/không hỗ trợ trình chiếu trực tiếp trên nền web/i)).toBeInTheDocument();
  });

  it('đóng modal khi nhấn phím Escape', () => {
    const handleClose = vi.fn();
    render(
      <AttachmentPreviewModal
        isOpen={true}
        onClose={handleClose}
        target={{ name: 'BaoCao.pdf', size: 1024 }}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
