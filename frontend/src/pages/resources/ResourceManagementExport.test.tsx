import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLanguage } from '@i18n/translate';
import ResourceManagementPage from './ResourceManagementPage';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof import('@lib/apiClient')>('@lib/apiClient');
  const client = vi.fn(async () => ({ results: [] })) as unknown as typeof actual.apiClient;
  return { ...actual, apiClient: client, default: client };
});

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({
    loaded: true,
    isSuperuser: false,
    isSystemAdmin: false,
    can: (code: string) => code === 'view_tailieu',
  }),
}));

function mockExportResponse(status: number, body: unknown) {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
}

describe('ResourceManagementPage xuất Excel', () => {
  beforeEach(() => {
    setLanguage('vi');
    window.URL.createObjectURL = vi.fn(() => 'blob:test');
    window.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('khi API trả 403 thì báo lỗi, không báo thành công và không tải file', async () => {
    const fetchMock = mockExportResponse(403, { detail: 'Bạn không có quyền thực hiện thao tác này.' });
    vi.stubGlobal('fetch', fetchMock);
    render(<MemoryRouter><ResourceManagementPage /></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', { name: /Xuất danh sách theo bộ lọc hiện tại/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(await screen.findByText('Từ chối quyền hạn')).toBeInTheDocument();
    expect(screen.queryByText(/xuất thành công/i)).not.toBeInTheDocument();
    expect(window.URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('khi API trả 200 thì tải file và báo thành công', async () => {
    const fetchMock = vi.fn(async () => new Response('xlsx', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    render(<MemoryRouter><ResourceManagementPage /></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', { name: /Xuất danh sách theo bộ lọc hiện tại/ }));

    expect(await screen.findByText(/Đã xuất thành công/)).toBeInTheDocument();
    expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1);
  });
});
