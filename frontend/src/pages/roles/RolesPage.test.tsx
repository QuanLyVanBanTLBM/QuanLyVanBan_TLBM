import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RolesPage from './RolesPage';
import * as apiClientModule from '@lib/apiClient';
import { resetPermissionsCache } from '@lib/permissions';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClientModule>('@lib/apiClient');
  const mockClient = vi.fn() as unknown as typeof apiClientModule.apiClient;
  mockClient.get = vi.fn();
  mockClient.post = vi.fn();
  mockClient.put = vi.fn();
  mockClient.patch = vi.fn();
  mockClient.delete = vi.fn();

  return {
    ...actual,
    apiClient: mockClient,
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);
const { ApiError } = apiClientModule;

const ALL_ROLE_PERMISSIONS = ['view_nhomquyen', 'add_nhomquyen', 'change_nhomquyen', 'delete_nhomquyen'];

const PERMISSIONS = [
  { id: 1, name: 'Xem danh sách chức vụ', codename: 'view_chucvu', module_ten: 'Chức vụ' },
  { id: 2, name: 'Thêm chức vụ', codename: 'add_chucvu', module_ten: 'Chức vụ' },
  { id: 3, name: 'Xuất Excel đơn vị/phòng ban', codename: 'export_donvi', module_ten: 'Đơn vị, phòng ban' },
];

const ROLES = [
  { id: 10, name: 'Văn thư', ma_nhom_quyen: 'VT', user_count: 2, permission_count: 1, permission_ids: [1] },
  { id: 11, name: 'Quản trị hệ thống', ma_nhom_quyen: 'ADMIN', user_count: 1, permission_count: 3, permission_ids: [1, 2, 3] },
  { id: 12, name: 'Nhóm tự tạo', ma_nhom_quyen: null, user_count: 3, permission_count: 0, permission_ids: [] },
];

function mockApi(options: { permissions?: string[]; rolesError?: unknown } = {}) {
  const { permissions = ALL_ROLE_PERMISSIONS, rolesError } = options;
  mockedApiClient.mockImplementation(async (endpoint: string) => {
    if (endpoint.includes('/auth/me/permissions/')) {
      return { is_superuser: false, permissions };
    }
    if (endpoint.startsWith('/api/permissions/')) {
      return PERMISSIONS;
    }
    if (endpoint.startsWith('/api/roles/')) {
      if (rolesError) throw rolesError;
      return ROLES;
    }
    return [];
  });
}

const SEARCH_PLACEHOLDER = 'Tìm quyền theo tên, mã quyền hoặc module...';

function renderPage() {
  return render(<RolesPage />);
}

async function selectRole(name: string) {
  fireEvent.click(await screen.findByRole('button', { name }));
}

describe('RolesPage (Issue #21)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();
  });

  it('lists roles and shows the permission matrix of the selected role', async () => {
    mockApi();
    renderPage();

    expect(await screen.findByRole('button', { name: 'Văn thư' })).toBeInTheDocument();
    expect(screen.getByText('Chức năng phân quyền sử dụng theo nhóm')).toBeInTheDocument();

    await selectRole('Văn thư');

    const checkboxes = await screen.findAllByRole('checkbox');
    expect(checkboxes).toHaveLength(PERMISSIONS.length);
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).not.toBeChecked();
  });

  it('shows the error state with a retry button when roles cannot be loaded', async () => {
    mockApi({ rolesError: new ApiError(500, { detail: 'roles.messages.fetchError' }) });
    renderPage();

    expect(await screen.findAllByText(/Không thể tải danh sách nhóm quyền/)).not.toHaveLength(0);
    expect(screen.getByRole('button', { name: /Thử lại/ })).toBeInTheDocument();
  });

  it('shows no retry button when the user has no permission to view roles (B7)', async () => {
    mockApi({ rolesError: new ApiError(403, { detail: 'roles.messages.permissionDenied' }) });
    renderPage();

    expect(await screen.findAllByText('Bạn không có quyền thực hiện thao tác này.')).not.toHaveLength(0);
    expect(screen.queryByRole('button', { name: /Thử lại/ })).not.toBeInTheDocument();
  });

  it('select all / deselect all only change the permissions visible in the search (B2)', async () => {
    mockApi();
    renderPage();

    await selectRole('Văn thư');
    const search = await screen.findByPlaceholderText(SEARCH_PLACEHOLDER);

    fireEvent.change(search, { target: { value: 'excel' } });
    expect(await screen.findAllByRole('checkbox')).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: /Chọn tất cả/ }));

    fireEvent.change(search, { target: { value: '' } });
    let checkboxes = await screen.findAllByRole('checkbox');
    expect(checkboxes.map((c) => (c as HTMLInputElement).checked)).toEqual([true, false, true]);

    fireEvent.change(search, { target: { value: 'chuc vu' } });
    expect(await screen.findAllByRole('checkbox')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: /Bỏ chọn/ }));

    fireEvent.change(search, { target: { value: '' } });
    checkboxes = await screen.findAllByRole('checkbox');
    expect(checkboxes.map((c) => (c as HTMLInputElement).checked)).toEqual([false, false, true]);
  });

  it('asks before switching role when there are unsaved permission changes (B5)', async () => {
    mockApi();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderPage();

    await selectRole('Văn thư');
    fireEvent.click((await screen.findAllByRole('checkbox'))[1]);

    await selectRole('Nhóm tự tạo');
    expect(confirmSpy).toHaveBeenCalledWith('Bạn có thay đổi quyền chưa lưu. Bỏ các thay đổi này?');
    // Người dùng bấm Hủy: vẫn ở nhóm cũ và giữ ô vừa tick
    expect((await screen.findAllByRole('checkbox'))[1]).toBeChecked();

    confirmSpy.mockReturnValue(true);
    await selectRole('Nhóm tự tạo');
    (await screen.findAllByRole('checkbox')).forEach((checkbox) => expect(checkbox).not.toBeChecked());
    confirmSpy.mockRestore();
  });

  it('switches role without asking when nothing was changed', async () => {
    mockApi();
    const confirmSpy = vi.spyOn(window, 'confirm');
    renderPage();

    await selectRole('Văn thư');
    await selectRole('Nhóm tự tạo');
    expect(confirmSpy).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('hides write actions and makes the matrix read-only when the user only has view permission', async () => {
    mockApi({ permissions: ['view_nhomquyen'] });
    renderPage();

    await selectRole('Văn thư');
    await waitFor(() => expect(mockedApiClient).toHaveBeenCalledWith('/api/auth/me/permissions/'));

    expect(screen.queryByRole('button', { name: /Thêm nhóm/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Sửa$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Xóa$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Lưu$/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Chọn tất cả/ })).not.toBeInTheDocument();

    const checkboxes = await screen.findAllByRole('checkbox');
    checkboxes.forEach((checkbox) => expect(checkbox).toBeDisabled());
  });

  it('shows every write action when the user can add, change and delete roles', async () => {
    mockApi();
    renderPage();

    await selectRole('Văn thư');

    expect(await screen.findByRole('button', { name: /Thêm nhóm/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Sửa$/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Xóa$/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Lưu$/ })).toBeInTheDocument();
    (await screen.findAllByRole('checkbox')).forEach((checkbox) => expect(checkbox).toBeEnabled());
  });

  it('saves the changed permissions of the selected role', async () => {
    mockApi();
    (mockedApiClient.put as ReturnType<typeof vi.fn>).mockResolvedValue({});
    renderPage();

    await selectRole('Văn thư');
    const checkboxes = await screen.findAllByRole('checkbox');
    fireEvent.click(checkboxes[1]);
    fireEvent.click(await screen.findByRole('button', { name: /^Lưu$/ }));

    await waitFor(() =>
      expect(mockedApiClient.put).toHaveBeenCalledWith('/api/roles/10/', {
        name: 'Văn thư',
        permission_ids: expect.arrayContaining([1, 2]),
      }),
    );
    expect(await screen.findByText('Cập nhật nhóm quyền thành công!')).toBeInTheDocument();
  });

  it('creates a role with only its name', async () => {
    mockApi();
    (mockedApiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 12,
      name: 'Nhóm mới',
      user_count: 0,
      permission_ids: [],
    });
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm nhóm/ }));
    fireEvent.change(screen.getByPlaceholderText('Nhập tên nhóm quyền...'), { target: { value: 'Nhóm mới' } });
    fireEvent.click(screen.getByRole('button', { name: /Tạo mới/ }));

    await waitFor(() => expect(mockedApiClient.post).toHaveBeenCalledWith('/api/roles/', { name: 'Nhóm mới' }));
    expect(await screen.findByText('Tạo nhóm quyền thành công!')).toBeInTheDocument();
  });

  it('does not allow renaming or deleting a standard role but still lets its permissions be edited', async () => {
    mockApi();
    renderPage();

    await selectRole('Văn thư');
    expect(await screen.findByRole('button', { name: /^Sửa$/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^Xóa$/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^Lưu$/ })).toBeEnabled();

    await selectRole('Nhóm tự tạo');
    expect(screen.getByRole('button', { name: /^Sửa$/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /^Xóa$/ })).toBeEnabled();
  });

  it('shows the backend reason when saving permissions is rejected for the admin role', async () => {
    mockApi();
    (mockedApiClient.put as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(400, { permission_ids: ['roles.messages.adminPermissionsRequired'] }),
    );
    renderPage();

    await selectRole('Quản trị hệ thống');
    fireEvent.click((await screen.findAllByRole('checkbox'))[0]);
    fireEvent.click(await screen.findByRole('button', { name: /^Lưu$/ }));

    expect(
      await screen.findByText(/Nhóm Quản trị hệ thống phải luôn giữ các quyền quản lý nhóm quyền/),
    ).toBeInTheDocument();
  });

  it('shows the backend reason when a role that still has users cannot be deleted', async () => {
    mockApi();
    (mockedApiClient.delete as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(400, { detail: 'roles.messages.groupHasUsers' }),
    );
    renderPage();

    await selectRole('Nhóm tự tạo');
    fireEvent.click(await screen.findByRole('button', { name: /^Xóa$/ }));
    const deleteButtons = await screen.findAllByRole('button', { name: /^Xóa$/ });
    fireEvent.click(deleteButtons[deleteButtons.length - 1]);

    await waitFor(() => expect(mockedApiClient.delete).toHaveBeenCalledWith('/api/roles/12/'));
    expect(
      await screen.findByText('Không thể xóa vì nhóm quyền này vẫn đang được gán cho một hoặc nhiều người dùng.'),
    ).toBeInTheDocument();
  });
});
