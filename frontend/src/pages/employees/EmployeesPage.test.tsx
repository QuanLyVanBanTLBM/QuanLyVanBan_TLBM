import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EmployeesPage from './EmployeesPage';
import * as apiClientModule from '@lib/apiClient';
import { resetPermissionsCache } from '@lib/permissions';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClientModule>('@lib/apiClient');
  const mockClient = vi.fn() as unknown as typeof apiClientModule.apiClient;
  mockClient.get = vi.fn();
  mockClient.post = vi.fn();
  mockClient.patch = vi.fn();
  mockClient.put = vi.fn();
  mockClient.delete = vi.fn();

  return {
    ...actual,
    apiClient: mockClient,
    downloadBlob: vi.fn(),
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);

const mockEmployeeData = [
  {
    id: 1,
    username: 'binhnv',
    email: 'binhnv@donvi.gov.vn',
    ho_ten: 'Nguyễn Văn Bình',
    ngay_sinh: '20/05/19xx',
    is_birthday_masked: true,
    don_vi_id: 1,
    don_vi_ten: 'Văn phòng Viện',
    khoi_ten: 'Khối Cơ quan',
    chuc_vu_id: 1,
    chuc_vu_ten: 'Chuyên viên',
    chuc_danh: 'Chuyên viên tổng hợp',
    sdt: '0912345678',
    trang_thai: 'LAM_VIEC' as const,
    trang_thai_display: 'Đang làm việc',
    is_active: true,
    is_public: true,
    ghi_chu: 'Ghi chú nhân viên',
    nhom_quyen: [],
    has_sensitive_permission: false,
    assignments: [
      {
        id: 10,
        don_vi_id: 2,
        don_vi_ten: 'Phòng Kế toán',
        chuc_vu_id: 2,
        chuc_vu_ten: 'Phó phòng',
        chuc_danh: 'Phó phòng kiêm nhiệm',
      },
    ],
    created_at: '2026-01-15T08:00:00Z',
    updated_at: '2026-01-15T08:00:00Z',
  },
  {
    id: 2,
    username: 'hungtv',
    email: 'hungtv@donvi.gov.vn',
    ho_ten: 'Trần Văn Hùng',
    ngay_sinh: '15/10/1988',
    is_birthday_masked: false,
    don_vi_id: 2,
    don_vi_ten: 'Phòng Kế toán',
    khoi_ten: 'Khối Cơ quan',
    chuc_vu_id: 2,
    chuc_vu_ten: 'Trưởng phòng',
    chuc_danh: 'Trưởng phòng Kế toán',
    sdt: '0987654321',
    trang_thai: 'NGHI_VIEC' as const,
    trang_thai_display: 'Nghỉ việc',
    is_active: false,
    is_public: true,
    ghi_chu: '',
    nhom_quyen: [{ id: 1, name: 'Lãnh đạo đơn vị' }],
    has_sensitive_permission: true,
    assignments: [],
    created_at: '2026-01-10T08:00:00Z',
    updated_at: '2026-01-10T08:00:00Z',
  },
];

describe('EmployeesPage Component (Issue #24)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();
    mockedApiClient.mockImplementation(async (endpoint: string, options?: RequestInit) => {
      if (options?.method === 'POST') {
        return mockedApiClient.post(endpoint, options.body, options);
      }
      if (endpoint.includes('/api/accounts/employees/import-jobs/')) {
        return mockedApiClient.get(endpoint);
      }
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return {
          is_superuser: true,
          permissions: [
            'view_list_cbnv',
            'export_cbnv',
            'add_cbnv',
            'change_full_cbnv',
            'change_self_cbnv',
            'delete_cbnv',
            'import_cbnv',
            'view_nhomquyen',
          ],
        };
      }
      if (endpoint.includes('/organizations/units/')) {
        return [
          { id: 1, ten: 'Văn phòng Viện', khoi: 1, khoi_ten: 'Khối Cơ quan', stt_uu_tien: 1, dia_chi: '', dien_thoai: '', email: '', is_public: true, ghi_chu: '' },
          { id: 2, ten: 'Phòng Kế toán', khoi: 1, khoi_ten: 'Khối Cơ quan', stt_uu_tien: 2, dia_chi: '', dien_thoai: '', email: '', is_public: true, ghi_chu: '' },
        ];
      }
      if (endpoint.includes('/api/positions/')) {
        return [
          { id: 1, name: 'Quản trị viên', display_order: 1, is_public: true, note: '' },
          { id: 2, name: 'Chuyên viên', display_order: 2, is_public: true, note: '' },
          { id: 3, name: 'Trưởng phòng', display_order: 3, is_public: true, note: '' },
        ];
      }
      if (endpoint.includes('/accounts/groups/')) {
        return [
          { id: 1, name: 'Lãnh đạo đơn vị' },
          { id: 2, name: 'Văn thư' },
        ];
      }
      if (endpoint.includes('/accounts/employees/')) {
        return {
          count: 2,
          next: null,
          previous: null,
          results: mockEmployeeData,
        };
      }
      return [];
    });
  });

  it('renders employee management title, action buttons, and table rows', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
      expect(screen.getByText('Trần Văn Hùng')).toBeInTheDocument();
    });

    expect(screen.getByText('Văn phòng Viện')).toBeInTheDocument();
    expect(screen.getByText('Phòng Kế toán')).toBeInTheDocument();
  });

  it('renders masked birthday indicator for privacy-protected employee', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('20/05/19xx')).toBeInTheDocument();
      expect(screen.getByText('15/10/1988')).toBeInTheDocument();
    });
  });

  it('opens employee modal on clicking Add Employee button', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const addBtn = screen.getByRole('button', { name: /Thêm nhân viên/i });
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(screen.getByText('Thêm Mới Cán Bộ Nhân Viên')).toBeInTheDocument();
    });
  });

  it('requires an explicit position instead of defaulting a new employee to the first position', async () => {
    const { container } = render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /Thêm nhân viên/i }));
    await screen.findByText('Thêm Mới Cán Bộ Nhân Viên');

    expect(container.querySelector('input[name="chuc_vu_id"]')).toHaveValue('');

    fireEvent.change(container.querySelector('input[name="ho_ten"]')!, {
      target: { value: 'Nhân viên kiểm tra chức vụ' },
    });
    fireEvent.change(container.querySelector('input[name="email"]')!, {
      target: { value: 'position-required@donvi.gov.vn' },
    });
    fireEvent.change(container.querySelector('input[name="ngay_sinh"]')!, {
      target: { value: '01/01/1990' },
    });
    fireEvent.submit(container.querySelector('form')!);

    expect(await screen.findByText('Vui lòng chọn chức vụ cho cán bộ nhân viên.')).toBeInTheDocument();
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it('opens import modal on clicking Import Excel button', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const importBtn = screen.getByRole('button', { name: /Nhập từ Excel/i });
    fireEvent.click(importBtn);

    await waitFor(() => {
      expect(screen.getByText('Nhập Danh Sách CBNV Từ Excel')).toBeInTheDocument();
    });
  });

  it('opens detail modal on clicking employee name', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const viewBtns = screen.getAllByTitle('Xem chi tiết');
    fireEvent.click(viewBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Thông Tin Chi Tiết Cán Bộ Nhân Viên')).toBeInTheDocument();
    });
  });

  it('hides add, import, edit, and delete buttons when user only has view_list_cbnv permission', async () => {
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return {
          is_superuser: false,
          permissions: ['view_list_cbnv'],
        };
      }
      if (endpoint.includes('/organizations/units/')) return [];
      if (endpoint.includes('/api/positions/')) return [];
      if (endpoint.includes('/accounts/groups/')) return [];
      if (endpoint.includes('/accounts/employees/')) {
        return {
          count: 2,
          next: null,
          previous: null,
          results: mockEmployeeData,
        };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    // Header administrative buttons should be hidden
    expect(screen.queryByRole('button', { name: /Thêm nhân viên/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Nhập từ Excel/i })).not.toBeInTheDocument();
    // Export Excel is gated by export_cbnv and must be hidden
    expect(screen.queryByRole('button', { name: /Xuất Excel/i })).not.toBeInTheDocument();

    // Row edit and delete buttons should be hidden
    expect(screen.queryByTitle('Chỉnh sửa')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Xóa')).not.toBeInTheDocument();

    // View detail button should still be visible
    expect(screen.getAllByTitle('Xem chi tiết').length).toBeGreaterThan(0);
  });

  it('allows self-edit for own record with change_self_cbnv and disables administrative fields', async () => {
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({
        username: 'binhnv',
        fullName: 'Nguyễn Văn Bình',
        role: 'staff',
      })
    );

    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return {
          is_superuser: false,
          permissions: ['view_list_cbnv', 'change_self_cbnv'],
        };
      }
      if (endpoint.includes('/organizations/units/')) return [];
      if (endpoint.includes('/api/positions/')) return [];
      if (endpoint.includes('/accounts/groups/')) return [];
      if (endpoint.includes('/accounts/employees/')) {
        return {
          count: 2,
          next: null,
          previous: null,
          results: mockEmployeeData,
        };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByTitle('Xem chi tiết');
    fireEvent.click(detailButtons[1]);
    const detailDialog = await screen.findByRole('dialog', { name: 'Thông Tin Chi Tiết Cán Bộ Nhân Viên' });
    expect(within(detailDialog).queryByRole('button', { name: 'Chỉnh sửa' })).not.toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(detailDialog).toContainElement(document.activeElement as HTMLElement);
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(detailDialog).toContainElement(document.activeElement as HTMLElement);

    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Thông Tin Chi Tiết Cán Bộ Nhân Viên' })).not.toBeInTheDocument();
    });
    await waitFor(() => expect(document.activeElement).toBe(detailButtons[1]));

    // Sửa button should appear for binhnv row (only 1 edit button on the page)
    const editBtns = screen.getAllByTitle('Chỉnh sửa');
    expect(editBtns.length).toBe(1);

    fireEvent.click(editBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Chỉnh Sửa Hồ Sơ Nhân Viên')).toBeInTheDocument();
    });

    // Check that selfEditNotice is displayed
    expect(screen.getByText(/Bạn đang cập nhật hồ sơ của chính mình/i)).toBeInTheDocument();

    // Check that administrative fields (e.g., name or note) are disabled
    const nameInput = document.querySelector<HTMLInputElement>('input[name="ho_ten"]')!;
    expect(nameInput).not.toBeNull();
    expect(nameInput).toBeDisabled();

    // Clean up
    localStorage.removeItem('tlbm_session');
  });

  it('opens the birthday picker and writes a selected date in DD/MM/YYYY format', async () => {
    const { container } = render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await screen.findByText('Nguyễn Văn Bình');
    fireEvent.click(screen.getByRole('button', { name: /Thêm nhân viên/i }));
    await screen.findByText('Thêm Mới Cán Bộ Nhân Viên');

    const datePicker = container.querySelector<HTMLInputElement>('input[type="date"]');
    expect(datePicker).not.toBeNull();
    expect(datePicker!).not.toHaveClass('sr-only');
    const showPicker = vi.fn();
    Object.defineProperty(datePicker!, 'showPicker', { configurable: true, value: showPicker });
    fireEvent.click(screen.getByRole('button', { name: 'Ngày sinh' }));
    expect(showPicker).toHaveBeenCalledOnce();
    fireEvent.change(datePicker!, { target: { value: '1990-01-02' } });

    expect(container.querySelector<HTMLInputElement>('input[name="ngay_sinh"]')).toHaveValue('02/01/1990');
  });

  it('displays error message from backend when delete fails', async () => {
    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return {
          is_superuser: true,
          permissions: ['view_list_cbnv', 'delete_cbnv'],
        };
      }
      if (endpoint.includes('/organizations/units/')) return [];
      if (endpoint.includes('/api/positions/')) return [];
      if (endpoint.includes('/accounts/groups/')) return [];
      if (endpoint.includes('/accounts/employees/')) {
        return {
          count: 2,
          next: null,
          previous: null,
          results: mockEmployeeData,
        };
      }
      return [];
    });

    mockedApiClient.delete.mockRejectedValueOnce({
      status: 400,
      data: {
        detail: 'employees.messages.cannotDeleteSelf',
      },
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const deleteBtns = screen.getAllByTitle('Xóa');
    fireEvent.click(deleteBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Xác nhận xóa cán bộ nhân viên')).toBeInTheDocument();
    });

    const passwordInput = screen.getByPlaceholderText(/Nhập mật khẩu/i);
    fireEvent.change(passwordInput, { target: { value: 'Admin@123' } });

    const confirmCheck = screen.getByRole('checkbox');
    fireEvent.click(confirmCheck);

    // The modal's confirm button is the last button with text "Xóa"
    const deleteActionBtns = screen.getAllByRole('button', { name: /^Xóa$/i });
    const confirmBtn = deleteActionBtns[deleteActionBtns.length - 1];
    expect(confirmBtn).not.toBeDisabled();
    fireEvent.click(confirmBtn);

    expect(mockedApiClient.delete).toHaveBeenCalledWith(
      '/api/accounts/employees/1/',
      expect.objectContaining({
        body: JSON.stringify({ password: 'Admin@123' }),
      })
    );

    await waitFor(() => {
      expect(screen.getByText('Bạn không thể tự xóa tài khoản của chính mình.')).toBeInTheDocument();
    });
  });

  it('requires password and confirmation checkbox to delete employee', async () => {
    const targetEmployee = {
      ...mockEmployeeData[0],
      id: 99,
      ho_ten: 'Lê Văn Thử',
      don_vi_id: 1,
      don_vi_ten: 'Văn phòng Viện',
    };

    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return {
          is_superuser: true,
          permissions: ['view_list_cbnv', 'delete_cbnv'],
        };
      }
      if (endpoint.includes('/accounts/employees/')) {
        return {
          count: 1,
          next: null,
          previous: null,
          results: [targetEmployee],
        };
      }
      return [];
    });

    mockedApiClient.delete.mockResolvedValueOnce({});

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Lê Văn Thử')).toBeInTheDocument();
    });

    // 1. Bấm nút xóa cán bộ
    const deleteBtn = screen.getByTitle('Xóa');
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(screen.getByText('Xác nhận xóa cán bộ nhân viên')).toBeInTheDocument();
    });

    // 2. Nút Xóa phải bị vô hiệu hóa khi chưa nhập mật khẩu và chưa tick checkbox xác nhận
    const deleteActionBtns = screen.getAllByRole('button', { name: /^Xóa$/i });
    const confirmBtn = deleteActionBtns[deleteActionBtns.length - 1];
    expect(confirmBtn).toBeDisabled();

    // Nhập mật khẩu
    const passwordInput = screen.getByPlaceholderText(/Nhập mật khẩu/i);
    fireEvent.change(passwordInput, { target: { value: 'Admin@123' } });

    // Tick vào checkbox
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    // 4. Nút Xóa được kích hoạt
    expect(confirmBtn).not.toBeDisabled();
    fireEvent.click(confirmBtn);

    // 5. API DELETE được gọi với body chứa password
    expect(mockedApiClient.delete).toHaveBeenCalledWith(
      '/api/accounts/employees/99/',
      expect.objectContaining({
        body: JSON.stringify({ password: 'Admin@123' }),
      })
    );
  });

  it('displays localized row errors when excel import fails with error codes', async () => {
    mockedApiClient.post.mockRejectedValueOnce({
      status: 400,
      data: {
        success: false,
        message: 'employees.messages.importHasErrors',
        errors: [
          {
            row: 3,
            field: 'email',
            code: 'employees.messages.emailExists',
            value: 'trung@donvi.gov.vn',
            message: "Email 'trung@donvi.gov.vn' đã tồn tại trên hệ thống.",
          },
          {
            row: 4,
            field: 'don_vi',
            code: 'employees.messages.unitNotFound',
            value: 'Phòng Ảo',
            message: "Không tìm thấy Đơn vị có tên 'Phòng Ảo' trong hệ thống.",
          },
        ],
      },
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const importBtn = screen.getByRole('button', { name: /Nhập từ Excel/i });
    fireEvent.click(importBtn);

    await waitFor(() => {
      expect(screen.getByText('Nhập Danh Sách CBNV Từ Excel')).toBeInTheDocument();
    });

    const file = new File(['dummy content'], 'danh_sach.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitBtn = screen.getByRole('button', { name: /Tiến hành nạp dữ liệu/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Dữ liệu tệp Excel chứa lỗi. Vui lòng kiểm tra lại theo danh sách bên dưới.')).toBeInTheDocument();
      expect(screen.getByText(/Địa chỉ email.*đã tồn tại/i)).toBeInTheDocument();
      expect(screen.getByText(/Không tìm thấy Đơn vị có tên 'Phòng Ảo' trong hệ thống/i)).toBeInTheDocument();
    });
  });

  it('clears file and error cache when clicking remove file or close button (x)', async () => {
    mockedApiClient.post.mockRejectedValue({
      status: 400,
      data: {
        success: false,
        message: 'employees.messages.importHasErrors',
        errors: [
          {
            row: 4,
            field: 'email',
            code: 'employees.messages.emailExists',
            value: 'dup@donvi.gov.vn',
            message: "Email 'dup@donvi.gov.vn' đã tồn tại trong hệ thống.",
          },
        ],
      },
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    // 1. Mở modal nhập Excel
    const importBtn = screen.getByRole('button', { name: /Nhập từ Excel/i });
    fireEvent.click(importBtn);

    await waitFor(() => {
      expect(screen.getByText('Nhập Danh Sách CBNV Từ Excel')).toBeInTheDocument();
    });

    // 2. Chọn file lỗi và nhấn nạp
    const file = new File(['error content'], 'mau_danh_sach_cbnv (1).xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText('mau_danh_sach_cbnv (1).xlsx')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Tiến hành nạp dữ liệu/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Dữ liệu tệp Excel chứa lỗi. Vui lòng kiểm tra lại theo danh sách bên dưới.')).toBeInTheDocument();
      expect(screen.getByText(/Địa chỉ email.*đã tồn tại/i)).toBeInTheDocument();
    });

    // 3. Bấm nút "Xóa tệp đã chọn" (nút x tại preview file) -> xóa cache dữ liệu cũ ngay trên màn hình
    const removeFileBtn = screen.getByTitle('Xóa tệp đã chọn');
    fireEvent.click(removeFileBtn);

    expect(screen.queryByText('mau_danh_sach_cbnv (1).xlsx')).not.toBeInTheDocument();
    expect(screen.queryByText('Dữ liệu tệp Excel chứa lỗi. Vui lòng kiểm tra lại theo danh sách bên dưới.')).not.toBeInTheDocument();
    expect(screen.queryByText(/Địa chỉ email.*đã tồn tại/i)).not.toBeInTheDocument();

    // 4. Chọn lại file và nạp lại để có lỗi
    const newFileInput = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    fireEvent.change(newFileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Tiến hành nạp dữ liệu/i }));

    await waitFor(() => {
      expect(screen.getByText(/Địa chỉ email.*đã tồn tại/i)).toBeInTheDocument();
    });

    // 5. Bấm nút "x" ở góc trên bên phải modal để đóng
    const closeHeaderBtn = screen.getByTitle('Đóng');
    fireEvent.click(closeHeaderBtn);

    // Modal đã đóng
    await waitFor(() => {
      expect(screen.queryByText('Nhập Danh Sách CBNV Từ Excel')).not.toBeInTheDocument();
    });

    // 6. Mở lại modal -> toàn bộ dữ liệu lỗi và file cũ đã bị xóa sạch (cache clear)
    fireEvent.click(screen.getByRole('button', { name: /Nhập từ Excel/i }));

    await waitFor(() => {
      expect(screen.getByText('Nhập Danh Sách CBNV Từ Excel')).toBeInTheDocument();
    });

    expect(screen.queryByText('mau_danh_sach_cbnv (1).xlsx')).not.toBeInTheDocument();
    expect(screen.queryByText('Dữ liệu tệp Excel chứa lỗi. Vui lòng kiểm tra lại theo danh sách bên dưới.')).not.toBeInTheDocument();
    expect(screen.queryByText(/Địa chỉ email.*đã tồn tại/i)).not.toBeInTheDocument();
    expect(screen.getByText('Kéo thả tệp .xlsx vào đây hoặc bấm để chọn tệp')).toBeInTheDocument();
  });

  it('shows upload progress while the server accepts the file', async () => {
    let resolveUpload: ((value: { job_id: string }) => void) | undefined;
    mockedApiClient.post.mockReturnValue(new Promise((resolve) => {
      resolveUpload = resolve;
    }));
    mockedApiClient.get.mockResolvedValue({
      job_id: 'pending-upload-job',
      status: 'done',
      phase: 'complete',
      processed: 0,
      total: 0,
      created_count: 0,
      errors: [],
      message: 'employees.import.importSuccess',
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );
    await screen.findByText('Nguyễn Văn Bình');
    fireEvent.click(screen.getByRole('button', { name: /Nhập từ Excel/i }));
    await screen.findByText('Nhập Danh Sách CBNV Từ Excel');

    const file = new File(['xlsx'], 'danh_sach.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(document.querySelector<HTMLInputElement>('input[type="file"]')!, {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole('button', { name: /Tiến hành nạp dữ liệu/i }));

    expect(await screen.findByText('Đang tải tệp lên máy chủ...')).toBeInTheDocument();
    resolveUpload?.({ job_id: 'pending-upload-job' });
    await waitFor(() => {
      expect(screen.queryByText('Nhập Danh Sách CBNV Từ Excel')).not.toBeInTheDocument();
    });
  });

  it('supports selecting and importing valid .xlsx Excel files', async () => {
    mockedApiClient.post.mockResolvedValue({
      job_id: 'test-import-job',
    });
    mockedApiClient.get
      .mockResolvedValueOnce({
        job_id: 'test-import-job',
        status: 'processing',
        phase: 'validation',
        processed: 10,
        total: 20,
        created_count: 0,
        errors: [],
        message: 'employees.import.jobValidating',
      })
      .mockResolvedValueOnce({
      job_id: 'test-import-job',
      status: 'done',
      phase: 'complete',
      processed: 2,
      total: 2,
      created_count: 2,
      errors: [],
      message: 'employees.import.importSuccess',
      });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Nhập từ Excel/i }));

    await waitFor(() => {
      expect(screen.getByText('Nhập Danh Sách CBNV Từ Excel')).toBeInTheDocument();
    });

    const file = new File(['xls dummy content'], 'danh_sach.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText('danh_sach.xlsx')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Tiến hành nạp dữ liệu/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText('Đang kiểm tra dữ liệu trong tệp...')).toBeInTheDocument();
    expect(screen.getByText('Đã xử lý 10/20 dòng')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Nhập thành công cán bộ nhân viên từ Excel!')).toBeInTheDocument();
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith(
      '/api/accounts/employees/import-async/',
      expect.any(FormData),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(mockedApiClient.get).toHaveBeenCalledWith(
      '/api/accounts/employees/import-jobs/test-import-job/',
    );
  });

  it('renders concurrent assignments badge on employee unit cell', async () => {
    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    // Cán bộ 1 có 1 phòng ban kiêm nhiệm -> hiển thị badge '+1 kiêm nhiệm'
    expect(screen.getByText('+1 kiêm nhiệm')).toBeInTheDocument();
  });

  it('triggers export excel download on clicking Export Excel button', async () => {
    const mockBlob = new Blob(['test-excel-content'], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    vi.mocked(apiClientModule.downloadBlob).mockReturnValue(undefined);

    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint.includes('/accounts/employees/export/')) {
        return mockBlob;
      }
      if (endpoint.includes('/api/auth/me/permissions/')) {
        return { is_superuser: false, permissions: ['view_list_cbnv', 'export_cbnv'] };
      }
      if (endpoint.includes('/accounts/employees/')) {
        return { count: 2, next: null, previous: null, results: mockEmployeeData };
      }
      return [];
    });

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Nguyễn Văn Bình')).toBeInTheDocument();
    });

    const exportBtn = screen.getByRole('button', { name: /Xuất Excel/i });
    expect(exportBtn).toBeInTheDocument();
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(apiClientModule.downloadBlob).toHaveBeenCalledWith(
        expect.stringContaining('/api/accounts/employees/export/'),
        'danh_sach_cbnv.xlsx'
      );
    });
  });
});
