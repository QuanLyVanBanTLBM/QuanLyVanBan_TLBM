import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PositionsPage from './PositionsPage';
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
  mockClient.blob = vi.fn() as unknown as typeof apiClientModule.downloadBlob;

  return {
    ...actual,
    apiClient: mockClient,
    downloadBlob: vi.fn(),
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);
const mockedDownload = vi.mocked(apiClientModule.downloadBlob);
const { ApiError } = apiClientModule;

const ALL_PERMISSIONS = ['view_chucvu', 'add_chucvu', 'change_chucvu', 'delete_chucvu', 'import_chucvu'];

const POSITIONS = [
  { id: 1, display_order: 1, name: 'Tổng Giám đốc', is_public: true, note: 'Cấp cao nhất' },
  { id: 2, display_order: 2, name: 'Cộng tác viên', is_public: false, note: '' },
];

function mockApi(options: { permissions?: string[]; list?: unknown; listError?: unknown } = {}) {
  const { permissions = ALL_PERMISSIONS, listError } = options;
  const list = options.list ?? { count: POSITIONS.length, next: null, previous: null, results: POSITIONS };
  mockedApiClient.mockImplementation(async (endpoint: string) => {
    if (endpoint.includes('/auth/me/permissions/')) {
      return { is_superuser: false, permissions };
    }
    if (endpoint.startsWith('/api/positions/')) {
      if (listError) throw listError;
      return list;
    }
    return [];
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PositionsPage />
    </MemoryRouter>,
  );
}

function listCalls() {
  return mockedApiClient.mock.calls.map((call) => String(call[0])).filter((url) => url.startsWith('/api/positions/?'));
}

describe('PositionsPage (Issue #20)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();
  });

  it('lists positions with priority, status badge and highlights internal ones', async () => {
    mockApi();
    renderPage();

    expect(await screen.findByText('Tổng Giám đốc')).toBeInTheDocument();
    expect(screen.getByText('Cấp cao nhất')).toBeInTheDocument();
    expect(screen.getByText('Công khai')).toBeInTheDocument();
    expect(screen.getByText('Nội bộ')).toBeInTheDocument();
    expect(screen.getByTestId('position-row-2').className).toContain('border-l-warning');
    expect(screen.getByTestId('position-row-1').className).not.toContain('border-l-warning');
  });

  it('hides write actions when the user only has view permission', async () => {
    mockApi({ permissions: ['view_chucvu'] });
    renderPage();

    await screen.findByText('Tổng Giám đốc');
    await waitFor(() => expect(mockedApiClient).toHaveBeenCalledWith('/api/auth/me/permissions/'));
    expect(screen.queryByRole('button', { name: /Thêm Chức vụ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Import Excel/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Chỉnh sửa Tổng Giám đốc/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xóa Tổng Giám đốc/ })).not.toBeInTheDocument();
    // C1: không còn cột Thao tác trống
    expect(screen.queryByRole('columnheader', { name: /Thao tác/i })).not.toBeInTheDocument();
  });

  it('shows write actions when the user has the permissions', async () => {
    mockApi();
    renderPage();

    expect(await screen.findByRole('button', { name: /Thêm Chức vụ/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Import Excel/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Chỉnh sửa Tổng Giám đốc/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xóa Tổng Giám đốc/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Thao tác/i })).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    mockApi({ list: { count: 0, next: null, previous: null, results: [] } });
    renderPage();
    expect(await screen.findByText('Chưa có chức vụ nào.')).toBeInTheDocument();
  });

  it('shows the permission denied state when the API returns 403', async () => {
    mockApi({ listError: new ApiError(403, { detail: 'positions.messages.permissionDenied' }) });
    renderPage();
    expect(await screen.findByText('Bạn không có quyền thực hiện thao tác này.')).toBeInTheDocument();
    // Thử lại cũng vẫn bị chặn nên không hiện nút
    expect(screen.queryByRole('button', { name: /Thử lại/ })).not.toBeInTheDocument();
  });

  it('shows an error state with retry that reloads the list', async () => {
    mockApi({ listError: new ApiError(500, {}) });
    renderPage();
    expect(await screen.findByText('Không thể tải danh sách chức vụ. Vui lòng thử lại.')).toBeInTheDocument();

    mockApi();
    fireEvent.click(screen.getByRole('button', { name: /Thử lại/ }));
    expect(await screen.findByText('Tổng Giám đốc')).toBeInTheDocument();
  });

  it('searches on the server and resets to page 1', async () => {
    mockApi();
    renderPage();
    await screen.findByText('Tổng Giám đốc');

    fireEvent.change(screen.getByLabelText('Tìm kiếm theo tên chức vụ...'), { target: { value: 'giám' } });
    await waitFor(() => expect(listCalls().some((url) => url.includes('search=gi%C3%A1m') && url.includes('page=1'))).toBe(true));
  });

  it('paginates through the server pages', async () => {
    mockApi({ list: { count: 25, next: '?page=2', previous: null, results: POSITIONS } });
    renderPage();
    await screen.findByText('Tổng Giám đốc');
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
    expect(screen.getByText('Hiển thị 1 - 10 trên tổng số 25')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Trang sau' }));
    await waitFor(() => expect(listCalls().some((url) => url.includes('page=2'))).toBe(true));
    expect(await screen.findByText('2 / 3')).toBeInTheDocument();
  });

  it('creates a position and sends trimmed values, leaving STT empty for auto-assign', async () => {
    mockApi();
    vi.mocked(mockedApiClient.post).mockResolvedValue({});
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm Chức vụ/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: '  Phó phòng  ' } });
    fireEvent.change(within(dialog).getByLabelText('Ghi chú'), { target: { value: ' ghi chú ' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tạo mới' }));

    await waitFor(() =>
      expect(mockedApiClient.post).toHaveBeenCalledWith('/api/positions/', {
        display_order: undefined,
        name: 'Phó phòng',
        is_public: true,
        note: 'ghi chú',
      }),
    );
    expect(await screen.findByText('Đã thêm chức vụ thành công.')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('validates the name on the client without calling the API', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm Chức vụ/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: '    ' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tạo mới' }));

    expect(await within(dialog).findByText('Tên chức vụ không được để trống hoặc chỉ chứa khoảng trắng.')).toBeInTheDocument();
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it('rejects an invalid STT on the client', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm Chức vụ/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: 'Hợp lệ' } });
    fireEvent.change(within(dialog).getByLabelText('STT Ưu tiên'), { target: { value: '0' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tạo mới' }));

    expect(await within(dialog).findByText('STT ưu tiên phải là số nguyên dương.')).toBeInTheDocument();
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it('rejects an STT above the database limit on the client', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm Chức vụ/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: 'Hợp lệ' } });
    fireEvent.change(within(dialog).getByLabelText('STT Ưu tiên'), { target: { value: '2147483648' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tạo mới' }));

    expect(await within(dialog).findByText('STT ưu tiên tối đa 2147483647.')).toBeInTheDocument();
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it('shows server field errors and keeps the modal open', async () => {
    mockApi();
    vi.mocked(mockedApiClient.post).mockRejectedValue(
      new ApiError(400, { name: ['positions.messages.nameExists'], display_order: ['positions.messages.sttExists'] }),
    );
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Thêm Chức vụ/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: 'Tổng Giám đốc' } });
    fireEvent.change(within(dialog).getByLabelText('STT Ưu tiên'), { target: { value: '1' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tạo mới' }));

    expect(await within(dialog).findByText('Tên chức vụ này đã tồn tại.')).toBeInTheDocument();
    expect(within(dialog).getByText('STT ưu tiên này đã được sử dụng. Vui lòng chọn số khác.')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('edits a position with prefilled values via PUT', async () => {
    mockApi();
    vi.mocked(mockedApiClient.put).mockResolvedValue({});
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Chỉnh sửa Tổng Giám đốc/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByLabelText(/Tên chức vụ/)).toHaveValue('Tổng Giám đốc');
    expect(within(dialog).getByLabelText('STT Ưu tiên')).toHaveValue('1');

    fireEvent.change(within(dialog).getByLabelText(/Tên chức vụ/), { target: { value: 'Tổng Giám đốc điều hành' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Lưu thay đổi' }));

    await waitFor(() =>
      expect(mockedApiClient.put).toHaveBeenCalledWith('/api/positions/1/', {
        display_order: 1,
        name: 'Tổng Giám đốc điều hành',
        is_public: true,
        note: 'Cấp cao nhất',
      }),
    );
    expect(await screen.findByText('Đã cập nhật chức vụ thành công.')).toBeInTheDocument();
  });

  it('deletes after confirmation', async () => {
    mockApi();
    vi.mocked(mockedApiClient.delete).mockResolvedValue(undefined);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Xóa Cộng tác viên/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/Cộng tác viên/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Xóa' }));

    await waitFor(() => expect(mockedApiClient.delete).toHaveBeenCalledWith('/api/positions/2/'));
    expect(await screen.findByText('Đã xóa chức vụ thành công.')).toBeInTheDocument();
  });

  it('explains why a position in use cannot be deleted', async () => {
    mockApi();
    vi.mocked(mockedApiClient.delete).mockRejectedValue(new ApiError(400, { detail: 'positions.messages.inUse' }));
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Xóa Tổng Giám đốc/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Xóa' }));

    expect(
      await within(dialog).findByText('Không thể xóa chức vụ này vì đang được gán cho cán bộ nhân viên.'),
    ).toBeInTheDocument();
  });

  it('downloads the import template', async () => {
    mockApi();
    mockedDownload.mockResolvedValue(undefined);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Import Excel/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: /Tải file mẫu/ }));

    await waitFor(() =>
      expect(mockedDownload).toHaveBeenCalledWith('/api/positions/import-template/', 'mau_import_chuc_vu.xlsx'),
    );
  });

  it('imports a file and lists each failed row with its reason', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Import Excel/ }));
    const dialog = await screen.findByRole('dialog');

    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint === '/api/positions/import/') {
        return {
          total: 3,
          imported: 1,
          failed: 2,
          errors: [
            { row: 3, field: 'name', code: 'positions.messages.nameExists', value: 'Tổng Giám đốc' },
            { row: 4, field: 'display_order', code: 'positions.import.errors.invalidStt', value: 'abc' },
          ],
        };
      }
      return { count: 0, next: null, previous: null, results: [] };
    });

    const file = new File(['x'], 'chuc_vu.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(within(dialog).getByTestId('position-import-file'), { target: { files: [file] } });
    expect(within(dialog).getByText('chuc_vu.xlsx')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: /Tải lên và import/ }));

    const result = await within(dialog).findByTestId('position-import-result');
    expect(within(result).getByText('Tổng số dòng: 3')).toBeInTheDocument();
    expect(within(result).getByText('Thành công: 1')).toBeInTheDocument();
    expect(within(result).getByText('Lỗi: 2')).toBeInTheDocument();
    expect(within(result).getByText('Dòng 3')).toBeInTheDocument();
    expect(within(result).getByText('Tên chức vụ này đã tồn tại.')).toBeInTheDocument();
    expect(within(result).getByText('Dòng 4')).toBeInTheDocument();
    expect(within(result).getByText('STT ưu tiên phải là số nguyên dương.')).toBeInTheDocument();
    expect(within(result).getByText('Giá trị: abc')).toBeInTheDocument();

    const importCall = mockedApiClient.mock.calls.find((call) => call[0] === '/api/positions/import/');
    expect((importCall?.[1] as RequestInit).body).toBeInstanceOf(FormData);
  });

  it('reports a whole-file error from the server', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Import Excel/ }));
    const dialog = await screen.findByRole('dialog');

    mockedApiClient.mockImplementation(async (endpoint: string) => {
      if (endpoint === '/api/positions/import/') {
        throw new ApiError(400, { detail: 'positions.import.errors.invalidTemplate' });
      }
      return [];
    });

    const file = new File(['x'], 'sai_mau.xlsx');
    fireEvent.change(within(dialog).getByTestId('position-import-file'), { target: { files: [file] } });
    fireEvent.click(within(dialog).getByRole('button', { name: /Tải lên và import/ }));

    expect(
      await within(dialog).findByText('File không đúng mẫu. Vui lòng tải file mẫu và giữ nguyên các cột ở dòng đầu.'),
    ).toBeInTheDocument();
  });

  it('asks for a file before uploading', async () => {
    mockApi();
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: /Import Excel/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: /Tải lên và import/ }));

    expect(await within(dialog).findByText('Vui lòng chọn file Excel để import.')).toBeInTheDocument();
    expect(mockedApiClient.mock.calls.some((call) => call[0] === '/api/positions/import/')).toBe(false);
  });
});
