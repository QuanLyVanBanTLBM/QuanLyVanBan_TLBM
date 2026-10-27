import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceTable } from './ResourceTable';
import { ResourceItem } from '@app-types/resource';

const mockItems: ResourceItem[] = [
  {
    id: 1,
    dm_tai_lieu: 1,
    dm_tai_lieu_name: 'Tài liệu chung',
    loai_tai_lieu: [1],
    loai_tai_lieu_names: ['Quy chế'],
    ky_hieu: '15/QĐ-BL',
    tieu_de: 'Quy chế quản lý nội bộ 2026',
    ngay_dang: '2026-01-15',
    noi_ban_hanh: 'Ban Giám Đốc',
    hieu_luc: 'CON_HIEU_LUC',
    file_dinh_kem: '/media/documents/templates/qc2026.pdf',
    hien_thi: 'TAT_CA',
    nguoi_tao_name: 'Admin',
  },
  {
    id: 2,
    dm_tai_lieu: 1,
    dm_tai_lieu_name: 'Tài liệu chung',
    loai_tai_lieu: [2],
    loai_tai_lieu_names: ['Biểu mẫu'],
    ky_hieu: 'BM-01',
    tieu_de: 'Biểu mẫu đề xuất nghỉ phép cũ',
    ngay_dang: '2025-05-10',
    noi_ban_hanh: 'Phòng Hành chính',
    hieu_luc: 'HET_HIEU_LUC',
    ngay_het_hieu_luc: '2026-01-01',
    file_dinh_kem: '/media/documents/templates/bm01.docx',
    hien_thi: 'TAT_CA',
    nguoi_tao_name: 'Admin',
  },
  {
    id: 3,
    dm_tai_lieu: 1,
    dm_tai_lieu_name: 'Tài liệu chung',
    loai_tai_lieu: [1],
    loai_tai_lieu_names: ['Quy chế'],
    ky_hieu: 'HD-03',
    tieu_de: 'Hướng dẫn một phần 2026',
    ngay_dang: '2026-03-01',
    noi_ban_hanh: 'Ban Giám Đốc',
    hieu_luc: 'CON_HIEU_LUC_1_PHAN',
    file_dinh_kem: '/media/documents/templates/hd03.pdf',
    hien_thi: 'TAT_CA',
    nguoi_tao_name: 'Admin',
  },
];

describe('ResourceTable Component', () => {
  it('renders table headers and rows correctly', () => {
    render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={2}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    expect(screen.getByText('Quy chế quản lý nội bộ 2026')).toBeInTheDocument();
    expect(screen.getByText('Biểu mẫu đề xuất nghỉ phép cũ')).toBeInTheDocument();
    expect(screen.getByText('15/QĐ-BL')).toBeInTheDocument();
    expect(screen.getByText('BM-01')).toBeInTheDocument();
    expect(screen.getByText('Còn hiệu lực')).toBeInTheDocument();
    expect(screen.getByText('Hết hiệu lực')).toBeInTheDocument();
  });

  it('applies dimmed background class to expired rows as required by project spec', () => {
    const { container } = render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={2}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBe(3);

    // Dòng 1: Còn hiệu lực -> không chứa class tối màu
    expect(rows[0].className).not.toContain('bg-slate-100/70');

    // Dòng 2: Hết hiệu lực -> PHẢI chứa class đổi màu tối theo quy chuẩn
    expect(rows[1].className).toContain('bg-slate-100/70');
    expect(rows[1].className).toContain('dark:bg-slate-800/60');

    // Dòng 3: Còn hiệu lực 1 phần -> không chứa class tối màu
    expect(rows[2].className).not.toContain('bg-slate-100/70');
  });

  it('calls onViewDetail via action menu Xem chi tiết button', () => {
    const handleViewDetail = vi.fn();
    render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={2}
        onPageChange={vi.fn()}
        onViewDetail={handleViewDetail}
      />
    );

    // Mở menu ⋯ trên dòng đầu tiên
    const menuButtons = screen.getAllByTitle('Thao tác');
    fireEvent.click(menuButtons[0]);

    // Bấm "Xem chi tiết" trong menu
    const viewBtn = screen.getByRole('button', { name: 'Xem chi tiết tài liệu' });
    fireEvent.click(viewBtn);
    expect(handleViewDetail).toHaveBeenCalledWith(mockItems[0]);
  });

  it('renders empty state when items is empty', () => {
    render(
      <ResourceTable
        items={[]}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={0}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    expect(screen.getByText('Không có tài liệu phù hợp')).toBeInTheDocument();
  });

  it('renders CON_HIEU_LUC_1_PHAN badge correctly', () => {
    render(
      <ResourceTable
        items={[mockItems[2]]}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={1}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    expect(screen.getByText('Còn hiệu lực 1 phần')).toBeInTheDocument();
  });

  it('handles multi-page pagination controls correctly', () => {
    const handlePageChange = vi.fn();
    render(
      <ResourceTable
        items={mockItems}
        currentPage={2}
        totalPages={10}
        pageSize={5}
        totalCount={50}
        onPageChange={handlePageChange}
        onViewDetail={vi.fn()}
      />
    );

    // Kiểm tra nút chuyển trang
    const prevBtn = screen.getByTitle('Trang trước');
    fireEvent.click(prevBtn);
    expect(handlePageChange).toHaveBeenCalledWith(1);

    const nextBtn = screen.getByTitle('Trang sau');
    fireEvent.click(nextBtn);
    expect(handlePageChange).toHaveBeenCalledWith(3);

    // Kiểm tra nút Về trang đầu và Đến trang cuối
    const firstBtn = screen.getByTitle('Về trang đầu (Trang 1)');
    fireEvent.click(firstBtn);
    expect(handlePageChange).toHaveBeenCalledWith(1);

    const lastBtn = screen.getByTitle('Đến trang cuối (Trang 10)');
    fireEvent.click(lastBtn);
    expect(handlePageChange).toHaveBeenCalledWith(10);
  });

  it('supports quick jumping to page via input with Enter key and filters non-digits', () => {
    const handlePageChange = vi.fn();
    render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={20}
        pageSize={5}
        totalCount={100}
        onPageChange={handlePageChange}
        onViewDetail={vi.fn()}
      />
    );

    const jumpInput = screen.getByLabelText('Nhập số trang muốn chuyển tới') as HTMLInputElement;

    // Không còn nút "Đi"
    expect(screen.queryByTitle('Chuyển đến trang đã nhập')).not.toBeInTheDocument();

    // Nhập chữ và ký tự đặc biệt -> chỉ giữ lại số
    fireEvent.change(jumpInput, { target: { value: 'abc!@#8' } });
    expect(jumpInput.value).toBe('8');

    // Nhấn phím Enter để chuyển trang
    fireEvent.keyDown(jumpInput, { key: 'Enter', code: 'Enter' });
    expect(handlePageChange).toHaveBeenCalledWith(8);
  });

  it('renders only 2 page numbers (1, 2) and last page (9) on page 1 of 9 pages (<< < 1 2 ... 9 > >>)', () => {
    render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={9}
        pageSize={5}
        totalCount={42}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    // Kiểm tra có các nút trang 1, 2 và trang cuối 9
    expect(screen.getByRole('button', { name: 'Trang 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Trang 2' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Trang 9' })).toBeInTheDocument();

    // Tuyệt đối không hiển thị nút trang 3, 4, 5
    expect(screen.queryByRole('button', { name: 'Trang 3' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Trang 4' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Trang 5' })).not.toBeInTheDocument();

    // Có đầy đủ các nút << < > >>
    expect(screen.getByLabelText('Về trang đầu')).toBeInTheDocument();
    expect(screen.getByLabelText('Trang trước')).toBeInTheDocument();
    expect(screen.getByLabelText('Trang sau')).toBeInTheDocument();
    expect(screen.getByLabelText('Đến trang cuối')).toBeInTheDocument();
  });

  it('renders only first page (1) and last 2 page numbers (8, 9) on page 9 of 9 pages (<< < 1 ... 8 9 > >>)', () => {
    render(
      <ResourceTable
        items={[mockItems[0], mockItems[1]]}
        currentPage={9}
        totalPages={9}
        pageSize={5}
        totalCount={42}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    // Kiểm tra có các nút trang 1, 8, 9
    expect(screen.getByRole('button', { name: 'Trang 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Trang 8' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Trang 9' })).toBeInTheDocument();

    // Không hiển thị 6 hay 7
    expect(screen.queryByRole('button', { name: 'Trang 6' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Trang 7' })).not.toBeInTheDocument();
  });

  it('renders spacer rows on the last page to stabilize table height', () => {
    const { container } = render(
      <ResourceTable
        items={[mockItems[0], mockItems[1]]}
        currentPage={9}
        totalPages={9}
        pageSize={5}
        totalCount={42}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    // Có 2 dòng thực tế + 3 dòng spacer = 5 dòng
    const allRows = container.querySelectorAll('tbody tr');
    expect(allRows.length).toBe(5);

    const spacerRows = container.querySelectorAll('tbody tr[data-spacer="true"]');
    expect(spacerRows.length).toBe(3);
  });

  it('renders safe extension (PDF) and prevents blob URL/IP leakage', () => {
    const blobItem: ResourceItem = {
      id: 99,
      dm_tai_lieu: 1,
      tieu_de: 'Tài liệu thử nghiệm tải lên tệp blob',
      ngay_dang: '2026-10-07',
      hieu_luc: 'CON_HIEU_LUC',
      hien_thi: 'TAT_CA',
      loai_tai_lieu: [1],
      file_dinh_kem: 'blob:http://127.0.0.1:5173/d881270d-8705-4415-a3e4-d514c4dae5ff',
    };

    render(
      <ResourceTable
        items={[blobItem]}
        currentPage={1}
        totalPages={1}
        pageSize={5}
        totalCount={1}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    // Không bao giờ được hiển thị IP port hoặc guid trong nhãn extension
    expect(screen.queryByText(/1:5173/)).not.toBeInTheDocument();
    expect(screen.queryByText(/d881270d/i)).not.toBeInTheDocument();
    expect(screen.getByText('PDF')).toBeInTheDocument();
  });

  it('calls onViewDetail and does NOT call onDrillDown when clicking on row or file badge', () => {
    const handleViewDetail = vi.fn();
    const handleDrillDown = vi.fn();
    render(
      <ResourceTable
        items={mockItems}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={3}
        onPageChange={vi.fn()}
        onViewDetail={handleViewDetail}
        onDrillDown={handleDrillDown}
      />
    );

    // Bấm vào badge Tệp
    const fileBadges = screen.getAllByText('PDF');
    fireEvent.click(fileBadges[0]);
    expect(handleViewDetail).toHaveBeenCalledWith(mockItems[0]);
    expect(handleDrillDown).not.toHaveBeenCalled();

    // Bấm vào dòng
    const rowTitle = screen.getByText('Quy chế quản lý nội bộ 2026');
    fireEvent.click(rowTitle);
    expect(handleViewDetail).toHaveBeenCalledWith(mockItems[0]);
    expect(handleDrillDown).not.toHaveBeenCalled();
  });

  it('keeps scheduled document active with expiry date badge when expiration date is in the future', () => {
    const futureItem: ResourceItem = {
      id: 99,
      dm_tai_lieu: 1,
      loai_tai_lieu: [1],
      tieu_de: 'Tài liệu hết hạn tương lai',
      ngay_dang: '2026-01-01',
      hieu_luc: 'HET_HIEU_LUC',
      ngay_het_hieu_luc: '2099-12-31',
      file_dinh_kem: '/media/test.pdf',
      hien_thi: 'TAT_CA',
    };

    const { container } = render(
      <ResourceTable
        items={[futureItem]}
        currentPage={1}
        totalPages={1}
        pageSize={10}
        totalCount={1}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
      />
    );

    const row = container.querySelector('tbody tr');
    expect(row?.className).not.toContain('bg-slate-100/70');
    expect(screen.getByText('Còn hiệu lực')).toBeInTheDocument();
    expect(screen.getByText(/31\/12\/2099/)).toBeInTheDocument();
  });
});
