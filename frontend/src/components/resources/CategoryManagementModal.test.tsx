import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { CategoryManagementModal } from './CategoryManagementModal';
import { ResourceCategory, ResourceType } from '@app-types/resource';

vi.mock('@lib/authService', () => ({
  authService: {
    getSession: () => ({
      username: 'admin',
      fullName: 'Quản trị viên',
      role: 'admin',
    }),
  },
}));

const permissionState = vi.hoisted(() => ({ isSystemAdmin: true }));
vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({ loaded: true, isSuperuser: false, isSystemAdmin: permissionState.isSystemAdmin, can: () => false }),
}));

const mockCategories: ResourceCategory[] = [
  {
    id: 1,
    stt_uu_tien: 1,
    ky_hieu: 'BM-CHUNG',
    ten_tai_lieu: 'Biểu mẫu chung',
    nguoi_lap_name: 'Quản trị viên',
    ngay_lap: '2026-01-01',
    ghi_chu: 'Thư mục chung',
  },
];

const mockTypes: ResourceType[] = [
  {
    id: 10,
    dm_tai_lieu: 1,
    ten_loai: 'Hợp đồng mẫu',
    is_public: true,
    ghi_chu: 'Các loại hợp đồng',
  },
];

describe('CategoryManagementModal Component (Issue #233)', () => {
  const onSaveCategory = vi.fn();
  const onDeleteCategory = vi.fn();
  const onSaveType = vi.fn();
  const onDeleteType = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    permissionState.isSystemAdmin = true;
  });

  it('does not grant admin rights from the session role or the username "admin"', () => {
    // Session giả lập role 'admin', username 'admin' nhưng không phải quản trị hệ thống và không có quyền nào.
    permissionState.isSystemAdmin = false;
    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    expect(screen.getByText('Biểu mẫu chung')).toBeInTheDocument();
    expect(screen.getAllByText(/Chế độ chỉ xem/).length).toBeGreaterThan(0);
  });

  it('renders modal when isOpen is true', () => {
    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    expect(screen.getByText('Biểu mẫu chung')).toBeInTheDocument();
  });

  it('formats category creation date (ngay_lap) as dd/mm/yyyy in the category table', () => {
    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // mockCategories[0].ngay_lap is '2026-01-01', which should be formatted as '01/01/2026'
    expect(screen.getByText('01/01/2026')).toBeInTheDocument();
  });

  it('submits category creation and awaits onSaveCategory', async () => {
    onSaveCategory.mockResolvedValueOnce(undefined);

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Bấm nút "Thêm mới" trên tab Thư mục
    const addBtn = screen.getByTitle('Thêm mới');
    fireEvent.click(addBtn);

    // Nhập STT và Tên thư mục
    const nameInput = screen.getByPlaceholderText(/VD: Tài liệu, Biểu mẫu chung/i);
    fireEvent.change(nameInput, { target: { value: 'Thư mục Tài chính' } });

    const orderInput = screen.getByPlaceholderText('VD: 1, 2, 3...');
    fireEvent.change(orderInput, { target: { value: '2' } });

    // Submit form
    const saveBtn = screen.getByRole('button', { name: /Lưu thư mục/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(onSaveCategory).toHaveBeenCalledTimes(1);
    });

    expect(onSaveCategory).toHaveBeenCalledWith(
      expect.objectContaining({
        ten_tai_lieu: 'Thư mục Tài chính',
        stt_uu_tien: 2,
      }),
      false,
      0,
      []
    );
  });

  it('keeps sub-modal open and shows error if onSaveCategory fails', async () => {
    onSaveCategory.mockRejectedValueOnce(new Error('Lỗi trùng mã số hoặc mất kết nối'));

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    const addBtn = screen.getByTitle('Thêm mới');
    fireEvent.click(addBtn);

    const nameInput = screen.getByPlaceholderText(/VD: Tài liệu, Biểu mẫu chung/i);
    fireEvent.change(nameInput, { target: { value: 'Thư mục Test Lỗi' } });

    const orderInput = screen.getByPlaceholderText('VD: 1, 2, 3...');
    fireEvent.change(orderInput, { target: { value: '3' } });

    const saveBtn = screen.getByRole('button', { name: /Lưu thư mục/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText('Lỗi trùng mã số hoặc mất kết nối')).toBeInTheDocument();
    });
  });

  it('submits type creation and awaits onSaveType', async () => {
    onSaveType.mockResolvedValueOnce(undefined);

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Chuyển sang tab Loại tài liệu
    const typeTabBtn = screen.getByRole('button', { name: /Loại tài liệu/i });
    fireEvent.click(typeTabBtn);

    // Bấm nút "Thêm mới Loại tài liệu" trên tab Loại tài liệu
    const addTypeBtn = screen.getByTitle('Thêm mới Loại tài liệu');
    fireEvent.click(addTypeBtn);

    const typeNameInput = screen.getByPlaceholderText(/VD: Biểu mẫu bảo hiểm, Tờ trình.../i);
    fireEvent.change(typeNameInput, { target: { value: 'Phiếu thanh toán' } });

    const saveBtn = screen.getByRole('button', { name: /Lưu loại tài liệu/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(onSaveType).toHaveBeenCalledTimes(1);
    });

    expect(onSaveType).toHaveBeenCalledWith(
      expect.objectContaining({
        ten_loai: 'Phiếu thanh toán',
        dm_tai_lieu: 1,
      }),
      false
    );
  });

  it('paginates categories properly and supports page switching & changing page size', () => {
    const manyCategories: ResourceCategory[] = Array.from({ length: 8 }, (_, i) => ({
      id: i + 1,
      stt_uu_tien: i + 1,
      ky_hieu: `CAT-0${i + 1}`,
      ten_tai_lieu: `Thư mục ${i + 1}`,
      nguoi_lap_name: 'Quản trị viên',
      ngay_lap: '2026-01-01',
      ghi_chu: `Ghi chú ${i + 1}`,
    }));

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={manyCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Mặc định pageSize = 5: hiển thị Thư mục 1..5, không hiển thị Thư mục 6
    expect(screen.getByText('Thư mục 1')).toBeInTheDocument();
    expect(screen.getByText('Thư mục 5')).toBeInTheDocument();
    expect(screen.queryByText('Thư mục 6')).not.toBeInTheDocument();

    // Thông tin phân trang
    expect(screen.getAllByText(/Hiển thị/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('1–5')).toBeInTheDocument();
    expect(screen.getByText('5 dòng')).toBeInTheDocument();

    // Chuyển sang trang 2
    const page2Btn = screen.getByRole('button', { name: 'Trang 2' });
    fireEvent.click(page2Btn);

    expect(screen.getByText('Thư mục 6')).toBeInTheDocument();
    expect(screen.getByText('Thư mục 8')).toBeInTheDocument();
    expect(screen.queryByText('Thư mục 1')).not.toBeInTheDocument();

    // Đổi page size lên 10 dòng
    const pageSizeSelect = screen.getByLabelText('Chọn số thư mục hiển thị trên mỗi trang');
    fireEvent.change(pageSizeSelect, { target: { value: '10' } });

    // Trang 1 lúc này hiển thị đầy đủ cả 8 mục
    expect(screen.getByText('Thư mục 1')).toBeInTheDocument();
    expect(screen.getByText('Thư mục 8')).toBeInTheDocument();
  });

  it('paginates document types properly and resets page on filtering', () => {
    const manyTypes: ResourceType[] = Array.from({ length: 8 }, (_, i) => ({
      id: i + 10,
      dm_tai_lieu: 1,
      ten_loai: `Loại tài liệu ${i + 1}`,
      is_public: true,
      ghi_chu: `Ghi chú loại ${i + 1}`,
    }));

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={manyTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Chuyển sang tab Loại tài liệu
    const typeTabBtn = screen.getByRole('button', { name: /Loại tài liệu/i });
    fireEvent.click(typeTabBtn);

    // Trang 1: hiển thị Loại 1..5, không hiển thị Loại 6
    expect(screen.getByText('Loại tài liệu 1')).toBeInTheDocument();
    expect(screen.getByText('Loại tài liệu 5')).toBeInTheDocument();
    expect(screen.queryByText('Loại tài liệu 6')).not.toBeInTheDocument();

    // Bấm sang trang 2
    const page2Btn = screen.getByRole('button', { name: 'Trang 2' });
    fireEvent.click(page2Btn);

    expect(screen.getByText('Loại tài liệu 6')).toBeInTheDocument();
    expect(screen.queryByText('Loại tài liệu 1')).not.toBeInTheDocument();

    // Gõ tìm kiếm loại tài liệu -> tự động reset về trang 1
    const searchInput = screen.getByPlaceholderText('Tìm tên loại tài liệu...');
    fireEvent.change(searchInput, { target: { value: 'Loại tài liệu 1' } });

    expect(screen.getByText('Loại tài liệu 1')).toBeInTheDocument();
    expect(screen.queryByText('Loại tài liệu 6')).not.toBeInTheDocument();
  });

  it('allows selecting a parent folder via the custom dropdown portal when creating a document type', async () => {
    onSaveType.mockResolvedValueOnce(undefined);

    const multiCategories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục A' },
      { id: 2, stt_uu_tien: 2, ten_tai_lieu: 'Thư mục B' },
    ];

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={multiCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Chuyển sang tab Loại tài liệu
    const typeTabBtn = screen.getByRole('button', { name: /Loại tài liệu/i });
    fireEvent.click(typeTabBtn);

    // Mở modal thêm mới loại tài liệu
    const addTypeBtn = screen.getByTitle('Thêm mới Loại tài liệu');
    fireEvent.click(addTypeBtn);

    // Click nút dropdown "Thư mục cha"
    const catDropdownBtn = screen.getByRole('button', { name: /Thư mục A/i });
    fireEvent.click(catDropdownBtn);

    // Tìm kiếm thư mục trong dropdown popup portal
    const searchInput = screen.getByPlaceholderText('Tìm kiếm thư mục...');
    expect(searchInput).toBeInTheDocument();
    fireEvent.change(searchInput, { target: { value: 'Thư mục B' } });

    // Chọn "Thư mục B"
    const optionB = screen.getByRole('button', { name: /Thư mục B/i });
    fireEvent.click(optionB);

    // Nhập tên loại tài liệu
    const typeNameInput = screen.getByPlaceholderText(/VD: Biểu mẫu bảo hiểm, Tờ trình.../i);
    fireEvent.change(typeNameInput, { target: { value: 'Loại trong Thư mục B' } });

    // Lưu loại tài liệu
    const saveBtn = screen.getByRole('button', { name: /Lưu loại tài liệu/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(onSaveType).toHaveBeenCalledTimes(1);
    });

    expect(onSaveType).toHaveBeenCalledWith(
      expect.objectContaining({
        ten_loai: 'Loại trong Thư mục B',
        dm_tai_lieu: 2,
      }),
      false
    );
  });

  it('filters document types via the filter parent folder dropdown portal', () => {
    const multiCategories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục A' },
      { id: 2, stt_uu_tien: 2, ten_tai_lieu: 'Thư mục B' },
    ];

    const typesWithDifferentParents: ResourceType[] = [
      { id: 101, dm_tai_lieu: 1, ten_loai: 'Hợp đồng A', is_public: true },
      { id: 102, dm_tai_lieu: 2, ten_loai: 'Báo cáo B', is_public: true },
    ];

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={multiCategories}
        types={typesWithDifferentParents}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Chuyển sang tab Loại tài liệu
    const typeTabBtn = screen.getByRole('button', { name: /Loại tài liệu/i });
    fireEvent.click(typeTabBtn);

    // Ban đầu thấy cả 2 loại
    expect(screen.getByText('Hợp đồng A')).toBeInTheDocument();
    expect(screen.getByText('Báo cáo B')).toBeInTheDocument();

    // Mở dropdown lọc thư mục cha
    const filterBtn = screen.getAllByLabelText('Lọc theo thư mục cha')[0];
    fireEvent.click(filterBtn);

    // Chọn "Thư mục B" từ dropdown portal
    const optionB = screen.getAllByRole('button', { name: /Thư mục B/i })[0];
    fireEvent.click(optionB);

    // Chỉ thấy "Báo cáo B", "Hợp đồng A" bị lọc ẩn đi
    expect(screen.getByText('Báo cáo B')).toBeInTheDocument();
    expect(screen.queryByText('Hợp đồng A')).not.toBeInTheDocument();
  });

  it('supports scrolling and selecting when there are more than 5 categories in add type modal', () => {
    const eightCategories: ResourceCategory[] = Array.from({ length: 8 }, (_, i) => ({
      id: i + 1,
      stt_uu_tien: i + 1,
      ten_tai_lieu: `Thư mục ${i + 1}`,
    }));

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={eightCategories}
        types={[]}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Mở modal Thêm mới
    const addBtn = screen.getByRole('button', { name: /Thêm mới/i });
    fireEvent.click(addBtn);

    // Chuyển sang tab Loại tài liệu
    const typeTabBtn = screen.getByRole('button', { name: /Loại tài liệu \(Cấp 2\)/i });
    fireEvent.click(typeTabBtn);

    // Mở dropdown chọn Thư mục cha
    const catDropdownBtn = document.querySelector('button[aria-haspopup="listbox"]') as HTMLElement;
    expect(catDropdownBtn).toBeInTheDocument();
    fireEvent.click(catDropdownBtn);

    // Dropdown list container phải có max-h-[185px] và overflow-y-auto
    const dropdownList = document.querySelector('[role="listbox"] .overflow-y-auto');
    expect(dropdownList).toBeInTheDocument();
    expect(dropdownList?.className).toContain('max-h-[185px]');
    expect(dropdownList?.className).toContain('overflow-y-auto');

    // Chọn Thư mục 8 (mục thứ 8, vượt quá 5 mục đầu)
    const option8 = screen.getByRole('button', { name: /Thư mục 8/i });
    expect(option8).toBeInTheDocument();
    fireEvent.click(option8);

    // Nút dropdown hiển thị Thư mục 8 đã chọn
    expect(screen.getByRole('button', { name: /Thư mục 8/i })).toBeInTheDocument();
  });

  it('displays fixed and read-only creation date with tooltip in category form', () => {
    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={mockCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Mở modal Thêm mới
    const addBtn = screen.getByTitle('Thêm mới');
    fireEvent.click(addBtn);

    // Kiểm tra nhãn Ngày lập (Cố định theo ngày tạo)
    expect(screen.getByText('Ngày lập (Cố định theo ngày tạo)')).toBeInTheDocument();

    // Ô input ngày lập phải là readOnly và disabled
    const dateInput = screen.getByTitle('Cố định theo ngày tạo của thư mục');
    expect(dateInput).toBeInTheDocument();
    expect(dateInput).toHaveAttribute('readonly');
    expect(dateInput).toBeDisabled();
  });

  it('displays continuous sequential row numbers in STT column even when categories have gap in stt_uu_tien, and suggests lowest missing integer for new category', () => {
    const gapCategories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục 1' },
      { id: 2, stt_uu_tien: 2, ten_tai_lieu: 'Thư mục 2' },
      { id: 3, stt_uu_tien: 3, ten_tai_lieu: 'Thư mục 3' },
      { id: 8, stt_uu_tien: 8, ten_tai_lieu: 'Thư mục 8' },
      { id: 9, stt_uu_tien: 9, ten_tai_lieu: 'Thư mục 9' },
    ];

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={onClose}
        categories={gapCategories}
        types={mockTypes}
        onSaveCategory={onSaveCategory}
        onDeleteCategory={onDeleteCategory}
        onSaveType={onSaveType}
        onDeleteType={onDeleteType}
      />
    );

    // Các dòng trên bảng phải hiển thị STT liên tục 1, 2, 3, 4, 5 thay vì 1, 2, 3, 8, 9
    const rows = screen.getAllByRole('row');
    // rows[0] is thead, rows[1..5] are the 5 category rows
    expect(rows[1]).toHaveTextContent('1');
    expect(rows[1]).toHaveTextContent('Thư mục 1');
    expect(rows[2]).toHaveTextContent('2');
    expect(rows[2]).toHaveTextContent('Thư mục 2');
    expect(rows[3]).toHaveTextContent('3');
    expect(rows[3]).toHaveTextContent('Thư mục 3');
    expect(rows[4]).toHaveTextContent('4');
    expect(rows[4]).toHaveTextContent('Thư mục 8');
    expect(rows[5]).toHaveTextContent('5');
    expect(rows[5]).toHaveTextContent('Thư mục 9');

    // Mở popup Thêm mới: stt_uu_tien gợi ý phải là 4 (lấp đầy khoảng trống nhỏ nhất chưa dùng)
    const addBtn = screen.getByTitle('Thêm mới');
    fireEvent.click(addBtn);

    const orderInput = screen.getByPlaceholderText('VD: 1, 2, 3...') as HTMLInputElement;
    expect(orderInput.value).toBe('4');
  });
});

