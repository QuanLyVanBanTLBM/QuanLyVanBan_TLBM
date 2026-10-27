import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DocumentTable from './DocumentTable';
import { DocumentItem } from '@app-types/document';

describe('DocumentTable Component', () => {
  const mockDocuments: DocumentItem[] = [
    {
      id: 1,
      loai: 'DEN',
      loai_display: 'Văn bản Đến',
      nam: 2026,
      so_hieu: '01/QĐ-TLBM',
      so_thu_tu: 1,
      ngay_den: '2026-09-23T08:30:00Z',
      ngay_ban_hanh: '2026-09-20T00:00:00Z',
      ngay_van_ban: '2026-09-20T00:00:00Z',
      trich_yeu: 'Quyết định ban hành quy chế văn thư lưu trữ',
      noi_ban_hanh: 'Trường CĐ CNTT TP.HCM',
      nguoi_ky: 'Hiệu trưởng',
      hieu_luc: 'CON_HIEU_LUC',
      hieu_luc_display: 'Còn hiệu lực',
      hien_thi: true,
      nguoi_tao_name: 'Quản trị viên',
      attachment_count: 2,
      created_at: '2026-09-23T08:30:00Z',
    },
    {
      id: 2,
      loai: 'DEN',
      loai_display: 'Văn bản Đến',
      nam: 2026,
      so_hieu: '12/CV-UBND',
      so_thu_tu: 2,
      ngay_den: '2026-09-21T09:15:00Z',
      ngay_ban_hanh: '2026-09-19T00:00:00Z',
      ngay_van_ban: '2026-09-19T00:00:00Z',
      trich_yeu: 'Công văn hướng dẫn công tác phòng cháy chữa cháy',
      noi_ban_hanh: 'UBND Quận 5',
      nguoi_ky: 'Chủ tịch UBND',
      hieu_luc: 'HET_HIEU_LUC',
      hieu_luc_display: 'Hết hiệu lực',
      hien_thi: true,
      nguoi_tao_name: 'Văn thư',
      attachment_count: 0,
      created_at: '2026-09-21T09:15:00Z',
    },
  ];

  it('renders document rows and headers correctly', () => {
    render(
      <DocumentTable
        documents={mockDocuments}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    expect(screen.getByText('01/QĐ-TLBM')).toBeInTheDocument();
    expect(screen.getByText('12/CV-UBND')).toBeInTheDocument();
    expect(screen.getByText('Còn hiệu lực')).toBeInTheDocument();
    expect(screen.getByText('Hết hiệu lực')).toBeInTheDocument();
    expect(screen.getByText(/2 tệp đính kèm/i)).toBeInTheDocument();
  });

  it('renders empty state when there are no documents', () => {
    render(
      <DocumentTable
        documents={[]}
        totalCount={0}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    expect(screen.getByText(/Không tìm thấy văn bản đến nào/i)).toBeInTheDocument();
  });

  it('opens action menu on clicking 3 dots and triggers onViewDetail', () => {
    const onViewDetail = vi.fn();
    render(
      <DocumentTable
        documents={mockDocuments}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={onViewDetail}
        onViewHistory={vi.fn()}
      />
    );

    const actionButtons = screen.getAllByTitle('Tác vụ');
    fireEvent.click(actionButtons[0]);

    const viewDetailButton = screen.getByText('Xem chi tiết');
    expect(viewDetailButton).toBeInTheDocument();

    fireEvent.click(viewDetailButton);
    expect(onViewDetail).toHaveBeenCalledWith(1);
  });

  it('renders distinct directional replacement badges (thay_the_cho & bi_thay_boi)', () => {
    const directionalDoc: DocumentItem = {
      id: 8,
      loai: 'DEN',
      loai_display: 'Văn bản Đến',
      nam: 2026,
      so_hieu: '205/QĐ-BTTTT',
      so_thu_tu: 8,
      trich_yeu: 'Quy định tiêu chuẩn kỹ thuật',
      hieu_luc: 'HET_VA_THAY_THE',
      hieu_luc_display: 'Đã thay thế',
      hien_thi: true,
      attachment_count: 0,
      created_at: '2026-09-22T00:00:00Z',
      thay_the_cho: ['102/QĐ-BTTTT'],
      bi_thay_boi: ['127'],
    };

    render(
      <DocumentTable
        documents={[directionalDoc]}
        totalCount={1}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    // Kiểm tra badge xanh: Nó thay thế cho 102
    expect(screen.getByText('102/QĐ-BTTTT')).toBeInTheDocument();
    expect(screen.getByTitle('Văn bản này thay thế cho văn bản cũ: 102/QĐ-BTTTT')).toBeInTheDocument();

    // Kiểm tra badge vàng: Nó bị 127 thay thế
    expect(screen.getByText('127')).toBeInTheDocument();
    expect(screen.getByTitle('Văn bản này đã bị thay thế bởi: 127')).toBeInTheDocument();
  });

  it('hides edit and delete buttons when regular staff user is not the document creator', () => {
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({ username: 'chuyenvien_cntt', role: 'staff' })
    );

    const onEdit = vi.fn();
    const onDelete = vi.fn();

    render(
      <DocumentTable
        documents={mockDocuments}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );

    const actionButtons = screen.getAllByTitle('Tác vụ');
    fireEvent.click(actionButtons[0]);

    // Regular staff user who did not create the document should only see view options
    expect(screen.getByText('Xem chi tiết')).toBeInTheDocument();
    expect(screen.getByText('Lịch sử xem')).toBeInTheDocument();
    expect(screen.queryByText('Chỉnh sửa')).not.toBeInTheDocument();
    expect(screen.queryByText('Xóa văn bản')).not.toBeInTheDocument();

    localStorage.removeItem('tlbm_session');
  });

  it('shows edit and delete buttons for admin user', () => {
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({ username: 'admin', role: 'admin' })
    );

    const onEdit = vi.fn();
    const onDelete = vi.fn();

    render(
      <DocumentTable
        documents={mockDocuments}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );

    const actionButtons = screen.getAllByTitle('Tác vụ');
    fireEvent.click(actionButtons[0]);

    // Admin must see Edit and Delete buttons
    expect(screen.getByText('Chỉnh sửa')).toBeInTheDocument();
    expect(screen.getByText('Xóa văn bản')).toBeInTheDocument();

    localStorage.removeItem('tlbm_session');
  });

  it('shows edit and delete buttons for the creator of the document', () => {
    const docWithCreator: DocumentItem = {
      ...mockDocuments[0],
      nguoi_tao_username: 'canbo_vanthu',
    };

    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({ username: 'canbo_vanthu', role: 'staff' })
    );

    const onEdit = vi.fn();
    const onDelete = vi.fn();

    render(
      <DocumentTable
        documents={[docWithCreator]}
        totalCount={1}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );

    const actionButtons = screen.getAllByTitle('Tác vụ');
    fireEvent.click(actionButtons[0]);

    // Creator must see Edit and Delete buttons for their document
    expect(screen.getByText('Chỉnh sửa')).toBeInTheDocument();
    expect(screen.getByText('Xóa văn bản')).toBeInTheDocument();

    localStorage.removeItem('tlbm_session');
  });

  it('triggers onViewDetail when clicking anywhere on a document row', () => {
    const onViewDetail = vi.fn();
    render(
      <DocumentTable
        documents={mockDocuments}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={onViewDetail}
        onViewHistory={vi.fn()}
      />
    );

    const rows = screen.getAllByTitle('Bấm vào hàng để xem chi tiết văn bản');
    expect(rows.length).toBe(2);

    fireEvent.click(rows[0]);
    expect(onViewDetail).toHaveBeenCalledWith(1);
  });

  it('truncates multiple replacement documents with ... (+X) and shows full tooltip', () => {
    const multiDoc: DocumentItem = {
      id: 99,
      loai: 'DEN',
      loai_display: 'Văn bản Đến',
      nam: 2026,
      so_hieu: '99/QĐ-BTTTT',
      so_thu_tu: 99,
      trich_yeu: 'Văn bản hợp nhất quy chế',
      hieu_luc: 'CON_HIEU_LUC',
      hieu_luc_display: 'Còn hiệu lực',
      hien_thi: true,
      attachment_count: 0,
      created_at: '2026-09-25T00:00:00Z',
      thay_the_cho: ['101/QĐ-BTTTT', '102/QĐ-BTTTT', '103/QĐ-BTTTT'],
      bi_thay_boi: ['201/QĐ-BTTTT', '202/QĐ-BTTTT'],
      pham_vi: 'HAN_CHE',
    };

    render(
      <DocumentTable
        documents={[multiDoc]}
        totalCount={1}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    // Bảng danh sách hiển thị badge [Hạn chế] cạnh số ký hiệu cho văn bản hạn chế
    expect(screen.getByText('Hạn chế')).toBeInTheDocument();

    // Rút gọn thay_the_cho với ... (+2)
    expect(screen.getByText('... (+2)')).toBeInTheDocument();
    expect(
      screen.getByTitle('Văn bản này thay thế cho các văn bản: 101/QĐ-BTTTT, 102/QĐ-BTTTT, 103/QĐ-BTTTT')
    ).toBeInTheDocument();

    // Rút gọn bi_thay_boi với ... (+1)
    expect(screen.getByText('... (+1)')).toBeInTheDocument();
    expect(
      screen.getByTitle('Văn bản này đã bị thay thế bởi các văn bản: 201/QĐ-BTTTT, 202/QĐ-BTTTT')
    ).toBeInTheDocument();
  });

  it('renders STT row index and sub-label for outbound and inbound registered numbers', () => {
    const outboundDoc: DocumentItem = {
      ...mockDocuments[0],
      id: 99,
      so_thu_tu: 4,
      so_hieu: 'QA-OUT-01',
    };

    const { rerender } = render(
      <DocumentTable
        documents={[outboundDoc]}
        totalCount={1}
        page={1}
        pageSize={10}
        loai="DI"
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    // Tiêu đề cột STT
    expect(screen.getByText('STT')).toBeInTheDocument();
    // STT dòng phải là #1 dù so_thu_tu là 4
    expect(screen.getAllByText('#1').length).toBeGreaterThanOrEqual(1);
    // Nhãn phụ số đi
    expect(screen.getAllByText('Số đi: #4').length).toBeGreaterThanOrEqual(1);

    // Rerender với loai="DEN"
    rerender(
      <DocumentTable
        documents={[outboundDoc]}
        totalCount={1}
        page={1}
        pageSize={10}
        loai="DEN"
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    // Tiêu đề cột STT
    expect(screen.getByText('STT')).toBeInTheDocument();
    expect(screen.getAllByText('Số đến: #4').length).toBeGreaterThanOrEqual(1);
  });
});

