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
});
