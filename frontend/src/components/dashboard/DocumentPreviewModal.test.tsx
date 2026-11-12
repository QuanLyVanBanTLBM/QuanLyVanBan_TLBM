import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DocumentPreviewModal from './DocumentPreviewModal';
import { DocumentItem } from './ModernDashboardView';

describe('DocumentPreviewModal Component (Group 2 Detail & PDF Reader View)', () => {
  const mockDoc: DocumentItem = {
    code: '56/NQ-HĐND',
    title: 'Nghị quyết quy định chính sách hỗ trợ phát triển giáo dục mầm non',
    date: '29/09/2026',
    arrivalNumber: '#8',
    bookYear: '2026',
    arrivalDate: '30/09/2026',
    issuingPlace: 'Hội đồng Nhân dân TP. Hồ Chí Minh',
    signer: 'Nguyễn Thị Lệ',
    signerRole: 'Chủ tịch HĐND',
    validityStatus: 'expired',
    validityStatusLabel: 'Hết hiệu lực và thay thế',
    replacedBy: '15/CV-BGDĐT',
    note: 'Đã được thay thế bởi văn bản hướng dẫn 15/CV-BGDĐT',
    creator: 'Trí Kiệt Lê',
    createdAt: '30/09/2026 21:49:59',
  };

  it('does not render when isOpen is false', () => {
    render(
      <DocumentPreviewModal
        isOpen={false}
        onClose={vi.fn()}
        document={mockDoc}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders modal with full Group 2 document details layout when isOpen is true', () => {
    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDoc}
        docType="incoming"
      />
    );

    // Modal dialog is present
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // Header elements: title, badge code, and subtitle
    expect(screen.getByText('Chi Tiết Văn Bản Đến')).toBeInTheDocument();
    expect(screen.getByText('56/NQ-HĐND')).toBeInTheDocument();
    expect(screen.getByText('Xem toàn bộ thông tin chi tiết và danh sách tệp đính kèm.')).toBeInTheDocument();

    // Expired warning banner
    expect(screen.getByText('VĂN BẢN ĐÃ HẾT HIỆU LỰC (ĐÃ THAY THẾ)')).toBeInTheDocument();
    expect(screen.getAllByText('15/CV-BGDĐT').length).toBeGreaterThan(0);

    // Excerpt / Summary block
    expect(screen.getByText('TRÍCH YẾU NỘI DUNG')).toBeInTheDocument();
    expect(screen.getByText('Nghị quyết quy định chính sách hỗ trợ phát triển giáo dục mầm non')).toBeInTheDocument();

    // Column 1: Incoming specifications
    expect(screen.getByText('THÔNG SỐ ĐẾN')).toBeInTheDocument();
    expect(screen.getByText('#8')).toBeInTheDocument();

    // Column 2: Issuing Agency & Validity
    expect(screen.getByText('CƠ QUAN BAN HÀNH & HIỆU LỰC')).toBeInTheDocument();
    expect(screen.getByText('Hội đồng Nhân dân TP. Hồ Chí Minh')).toBeInTheDocument();
    expect(screen.getByText('Hết hiệu lực và thay thế')).toBeInTheDocument();

    // Note block
    expect(screen.getByText(/Đã được thay thế bởi văn bản hướng dẫn 15\/CV-BGDĐT/i)).toBeInTheDocument();

    // Attachments section
    expect(screen.getAllByText(/TỆP ĐÍNH KÈM/i).length).toBeGreaterThan(0);

    // Footer creator info
    expect(screen.getByText('Trí Kiệt Lê')).toBeInTheDocument();
  });

  it('renders download button and handles download action', () => {
    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDoc}
        docType="incoming"
      />
    );

    const downloadBtn = screen.getByTitle('Tải xuống');
    expect(downloadBtn).toBeInTheDocument();
  });

  it('triggers onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={handleClose}
        document={mockDoc}
      />
    );

    const closeBtn = screen.getByLabelText('Đóng (ESC)');
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('closes on Escape key press', () => {
    const handleClose = vi.fn();
    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={handleClose}
        document={mockDoc}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('navigates next and previous documents when buttons are clicked', () => {
    const handleNext = vi.fn();
    const handlePrev = vi.fn();

    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDoc}
        onNext={handleNext}
        onPrev={handlePrev}
        hasNext={true}
        hasPrev={true}
        currentIndex={1}
        totalDocs={3}
      />
    );

    const nextBtn = screen.getByLabelText('Văn bản tiếp theo');
    fireEvent.click(nextBtn);
    expect(handleNext).toHaveBeenCalledTimes(1);

    const prevBtn = screen.getByLabelText('Văn bản trước');
    fireEvent.click(prevBtn);
    expect(handlePrev).toHaveBeenCalledTimes(1);
  });

  it('displays exactly one attachment per document', () => {
    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDoc}
        docType="incoming"
      />
    );

    // Section title shows exactly (1) attachment
    expect(screen.getByText('TỆP ĐÍNH KÈM (1)')).toBeInTheDocument();
    expect(screen.getByText(/0\. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026\.pdf/i)).toBeInTheDocument();
  });

  it('opens preview in a new window for PDF attachment', () => {
    const originalOpen = window.open;
    const windowOpenSpy = vi.fn();
    window.open = windowOpenSpy;

    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockDoc}
        docType="incoming"
      />
    );

    const pdfAttachment = screen.getByText(/0\. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026\.pdf/i);
    expect(pdfAttachment).toBeInTheDocument();
    fireEvent.click(pdfAttachment);

    expect(windowOpenSpy).toHaveBeenCalledWith(
      '/demo_files/0. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026.pdf',
      '_blank',
      'noopener,noreferrer'
    );

    window.open = originalOpen;
  });

  it('auto-downloads DOCX attachment when clicked', () => {
    const mockWordDoc: DocumentItem = {
      ...mockDoc,
      code: '45/CV-STTTT',
      title: 'Công văn hướng dẫn chuyển đổi số',
    };

    const linkClickSpy = vi.fn();
    const originalCreateElement = window.document.createElement.bind(window.document);
    vi.spyOn(window.document, 'createElement').mockImplementation((tagName: string) => {
      const el = originalCreateElement(tagName);
      if (tagName.toLowerCase() === 'a') {
        el.click = linkClickSpy;
      }
      return el;
    });

    render(
      <DocumentPreviewModal
        isOpen={true}
        onClose={vi.fn()}
        document={mockWordDoc}
        docType="incoming"
      />
    );

    const docxAttachment = screen.getByText(/BaiTap_Buoi06_506250495\.docx/i);
    expect(docxAttachment).toBeInTheDocument();
    fireEvent.click(docxAttachment);

    expect(linkClickSpy).toHaveBeenCalled();

    vi.restoreAllMocks();
  });
});

