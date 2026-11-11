import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceFormModal } from './ResourceFormModal';
import { ResourceItem, ResourceCategory, ResourceType } from '@app-types/resource';
import { Unit } from '@app-types/organization';

const mockCategories: ResourceCategory[] = [
  { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục 1' },
];

const mockTypes: ResourceType[] = [
  { id: 1, dm_tai_lieu: 1, ten_loai: 'Loại 1', is_public: true },
];

describe('ResourceFormModal Component', () => {
  it('renders default Active badge and optional expiration date input in Add Mode', () => {
    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
      />
    );

    // Không hiển thị 4 nút chọn trạng thái khi thêm mới
    expect(screen.queryByRole('button', { name: /^Còn hiệu lực$/i })).not.toBeInTheDocument();
    // Hiển thị badge Còn hiệu lực mặc định
    expect(screen.getByText(/Còn hiệu lực \(Mặc định khi tạo mới\)/i)).toBeInTheDocument();
    // Hiển thị nhãn Hẹn ngày tự động hết hiệu lực (Tùy chọn)
    expect(screen.getByText(/Hẹn ngày tự động hết hiệu lực \(Tùy chọn\)/i)).toBeInTheDocument();
    // Hiển thị gợi ý tự động hết hiệu lực
    expect(screen.getByText(/tự động chuyển sang Hết hiệu lực khi tới ngày/i)).toBeInTheDocument();
    // Ô chọn ngày hết hiệu lực có min attribute để không cho chọn ngày trước ngày tạo
    const expDateInput = document.getElementById('field-ngay_het_hieu_luc') as HTMLInputElement;
    expect(expDateInput).toBeInTheDocument();
    expect(expDateInput.min).toBeTruthy();
  });

  it('renders status selector buttons in Edit Mode', () => {
    const editItem: ResourceItem = {
      id: 5,
      dm_tai_lieu: 1,
      loai_tai_lieu: [1],
      tieu_de: 'Tài liệu đang sửa',
      ngay_dang: '2026-01-01',
      hieu_luc: 'CON_HIEU_LUC',
      file_dinh_kem: '/media/test.pdf',
      hien_thi: 'TAT_CA',
    };

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        initialData={editItem}
        categories={mockCategories}
        types={mockTypes}
      />
    );

    // Ở chế độ chỉnh sửa, hiển thị 4 nút chọn trạng thái
    expect(screen.getByRole('button', { name: /^Còn hiệu lực$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Còn hiệu lực 1 phần$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Hết hiệu lực$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Hết hiệu lực và thay thế$/i })).toBeInTheDocument();
  });

  it('allows opening folder dropdown portal and selecting a category', () => {
    const multiCategories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục 1' },
      { id: 2, stt_uu_tien: 2, ten_tai_lieu: 'Thư mục 2' },
    ];
    const multiTypes: ResourceType[] = [
      { id: 1, dm_tai_lieu: 1, ten_loai: 'Loại 1', is_public: true },
      { id: 2, dm_tai_lieu: 2, ten_loai: 'Loại 2', is_public: true },
    ];

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={multiCategories}
        types={multiTypes}
      />
    );

    // Mở dropdown chọn thư mục
    const folderDropdownBtn = screen.getByRole('button', { name: /^Thư mục \*/i });
    fireEvent.click(folderDropdownBtn);

    // Tìm kiếm trong dropdown portal
    const searchInput = screen.getByPlaceholderText('Tìm kiếm thư mục...');
    expect(searchInput).toBeInTheDocument();
    fireEvent.change(searchInput, { target: { value: 'Thư mục 2' } });

    // Chọn "Thư mục 2"
    const option2 = screen.getByRole('button', { name: /Thư mục 2/i });
    fireEvent.click(option2);

    // Dropdown đóng lại và hiển thị Thư mục 2
    expect(folderDropdownBtn).toHaveTextContent('Thư mục 2');
    // Danh sách loại tài liệu tương ứng cũng chuyển sang Loại 2
    expect(screen.getByText('Loại 2')).toBeInTheDocument();
  });

  it('automatically sets expiration date to today when user selects Expired status in Edit Mode', () => {
    const editItem: ResourceItem = {
      id: 5,
      dm_tai_lieu: 1,
      loai_tai_lieu: [1],
      tieu_de: 'Tài liệu đang sửa',
      ngay_dang: '2026-01-01',
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: null,
      file_dinh_kem: '/media/test.pdf',
      hien_thi: 'TAT_CA',
    };

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        initialData={editItem}
        categories={mockCategories}
        types={mockTypes}
      />
    );

    const expDateInput = document.getElementById('field-ngay_het_hieu_luc') as HTMLInputElement;
    expect(expDateInput.value).toBe('');

    // Bấm nút Hết hiệu lực
    const expiredBtn = screen.getByRole('button', { name: /^Hết hiệu lực$/i });
    fireEvent.click(expiredBtn);

    // Ô ngày hết hiệu lực được tự động điền ngày hôm nay
    expect(expDateInput.value).toBeTruthy();
  });

  it('displays department helper notice when Internal Scope is selected with an issuing unit', () => {
    const mockUnits: Unit[] = [
      {
        id: 10,
        khoi: 1,
        ten: 'Ban Kiểm toán nội bộ',
        stt_uu_tien: 1,
        dia_chi: null,
        dien_thoai: null,
        email: null,
        is_public: true,
        ghi_chu: null,
      },
    ];

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
        units={mockUnits}
        initialData={{
          id: 99,
          dm_tai_lieu: 1,
          loai_tai_lieu: [1],
          tieu_de: 'Tài liệu nội bộ',
          ngay_dang: '2026-01-01',
          noi_ban_hanh: 'Ban Kiểm toán nội bộ',
          don_vi_id: 10,
          hieu_luc: 'CON_HIEU_LUC',
          file_dinh_kem: '/media/test.pdf',
          hien_thi: 'NOI_BO_PHONG_BAN',
        }}
      />
    );

    // Kiểm tra thông báo phạm vi nội bộ hiển thị đúng đơn vị ban hành
    expect(screen.getByText(/Tài liệu chỉ hiển thị cho cán bộ nhân viên thuộc đơn vị: Ban Kiểm toán nội bộ/i)).toBeInTheDocument();
  });

  it('formats posted date (ngay_dang) as dd/mm/yyyy in read-only input', () => {
    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
        initialData={{
          id: 100,
          dm_tai_lieu: 1,
          loai_tai_lieu: [1],
          tieu_de: 'Tài liệu test ngày',
          ngay_dang: '2026-10-24',
          hieu_luc: 'CON_HIEU_LUC',
          file_dinh_kem: '/media/test.pdf',
          hien_thi: 'TAT_CA',
        }}
      />
    );

    const postedDateInput = document.getElementById('field-ngay_dang') as HTMLInputElement;
    expect(postedDateInput).toBeInTheDocument();
    expect(postedDateInput.value).toBe('24/10/2026');
  });

  it('preserves and displays custom noi_ban_hanh correctly even when don_vi_id belongs to another department', () => {
    const mockUnits: Unit[] = [
      { id: 24, khoi: 1, stt_uu_tien: 1, ten: 'Ban công nghệ thông tin', dia_chi: null, dien_thoai: null, email: null, is_public: true, ghi_chu: null, khoi_ten: 'Khối Hỗ trợ' },
      { id: 25, khoi: 1, stt_uu_tien: 2, ten: 'Ban Kế toán', dia_chi: null, dien_thoai: null, email: null, is_public: true, ghi_chu: null, khoi_ten: 'Khối Kế toán' },
    ];

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
        units={mockUnits}
        initialData={{
          id: 4,
          dm_tai_lieu: 1,
          loai_tai_lieu: [1],
          ky_hieu: '04/HSDT-TM-2026',
          tieu_de: 'Hồ sơ đề xuất báo giá',
          ngay_dang: '2026-10-24',
          noi_ban_hanh: 'Khối Phát triển Kinh doanh',
          don_vi_id: 24,
          hieu_luc: 'HET_HIEU_LUC',
          file_dinh_kem: '/media/test.pdf',
          hien_thi: 'TAT_CA',
        }}
      />
    );

    // Kiểm tra dropdown Nơi ban hành hiển thị đúng "Khối Phát triển Kinh doanh" chứ không bị đổi thành "Ban công nghệ thông tin"
    expect(screen.getByText('Khối Phát triển Kinh doanh')).toBeInTheDocument();
  });

  it('does not include the placeholder as a selectable option in authority options list', () => {
    const mockUnits: Unit[] = [
      { id: 1, khoi: 1, stt_uu_tien: 1, ten: 'Ban Tổng Giám đốc', dia_chi: null, dien_thoai: null, email: null, is_public: true, ghi_chu: null, khoi_ten: 'Ban Tổng Giám đốc' },
    ];

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
        units={mockUnits}
      />
    );

    // Mở menu dropdown Nơi ban hành
    const authorityBtn = screen.getByRole('button', { name: /Chọn hoặc tìm kiếm phòng ban ban hành/i });
    fireEvent.click(authorityBtn);

    // Dòng placeholder không được hiển thị như một mục chọn bên trong listbox
    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();
    expect(listbox.textContent).not.toContain('-- Chọn hoặc tìm kiếm phòng');
  });
});
