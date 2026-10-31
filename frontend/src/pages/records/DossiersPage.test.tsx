import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@lib/apiClient';
import { recordsService } from '@lib/recordsService';
import { setLanguage } from '@i18n/translate';
import DossiersPage from './DossiersPage';


vi.mock('@lib/recordsService', () => ({
  recordsService: {
    listDossiers: vi.fn(),
    getDossier: vi.fn(),
    createDossier: vi.fn(),
    updateDossier: vi.fn(),
    deleteDossier: vi.fn(),
    listDocumentTypes: vi.fn(),
    createDocumentType: vi.fn(),
    updateDocumentType: vi.fn(),
    deleteDocumentType: vi.fn(),
  },
}));


describe('DossiersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setLanguage('vi');
  });

  afterEach(() => {
    cleanup();
    setLanguage('vi');
  });

  it('keeps the table and confirmation open when a referenced dossier cannot be deleted', async () => {
    vi.mocked(recordsService.listDossiers).mockResolvedValue({ items: [
      { id: 2, so_ky_hieu: 'HS', ten_ho_so: 'Hồ sơ liên kết', is_he_thong: false },
    ], count: 1, next: null, previous: null });
    const reason = 'Không thể xóa hồ sơ vì vẫn còn loại văn bản, văn bản hoặc tài liệu đang tham chiếu hồ sơ này.';
    vi.mocked(recordsService.deleteDossier).mockRejectedValue(new ApiError(409, { detail: reason }));
    render(<MemoryRouter><DossiersPage /></MemoryRouter>);
    fireEvent.click(await screen.findByLabelText('Xóa Hồ sơ liên kết'));
    fireEvent.click(screen.getByRole('button', { name: 'Xóa' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(reason);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveTextContent('Hồ sơ liên kết');
    expect(screen.queryByText('Không thể tải dữ liệu')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Hủy' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveTextContent('Hồ sơ liên kết');
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);
  });

  it('does not offer deletion for the system dossier', async () => {
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [
        {
          id: 1,
          stt_uu_tien: 2,
          so_ky_hieu: 'HSC',
          ten_ho_so: 'Tên hệ thống có thể thay đổi',
          is_he_thong: true,
        },
        {
          id: 2,
          stt_uu_tien: 1,
          so_ky_hieu: 'HS-001',
          ten_ho_so: 'Hồ sơ thường',
          is_he_thong: false,
        },
      ],
      count: 2,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Tên hệ thống có thể thay đổi')).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText('Xóa Tên hệ thống có thể thay đổi')
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('Xóa Hồ sơ thường')).toBeInTheDocument();
  });

  it('renders the dossier page in English', async () => {
    act(() => setLanguage('en'));
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [],
      count: 0,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    expect(
      await screen.findByRole('heading', { name: 'Dossier catalog' })
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add dossier' })).toBeInTheDocument();
    expect(await screen.findByText('No matching dossiers')).toBeInTheDocument();
  });

  it('debounces search input by 250ms and queries dossiers', async () => {
    vi.useFakeTimers();
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [
        {
          id: 1,
          stt_uu_tien: 1,
          so_ky_hieu: 'HS-01',
          ten_ho_so: 'Hồ sơ pháp lý',
          is_he_thong: false,
        },
      ],
      count: 1,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Tìm theo tên hoặc số/ký hiệu hồ sơ...');
    act(() => {
      input.focus();
    });
    fireEvent.change(input, { target: { value: 'pháp lý' } });

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(200);
      await Promise.resolve();
    });

    expect(recordsService.listDossiers).toHaveBeenCalledTimes(2);
    expect(recordsService.listDossiers).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: 'pháp lý', page: 1 })
    );

    vi.useRealTimers();
  });

  it('does not enter loading state or initiate extra request when clearing search before debounce', async () => {
    vi.useFakeTimers();
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [
        {
          id: 1,
          stt_uu_tien: 1,
          so_ky_hieu: 'HS-01',
          ten_ho_so: 'Hồ sơ ban đầu',
          is_he_thong: false,
        },
      ],
      count: 1,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Tìm theo tên hoặc số/ký hiệu hồ sơ...');
    fireEvent.change(input, { target: { value: 'từ khóa' } });

    const clearBtn = screen.getByLabelText('Đặt lại');
    act(() => {
      fireEvent.click(clearBtn);
    });

    expect(input).toHaveValue('');
    expect(screen.queryByLabelText('Đang tải danh sách hồ sơ')).not.toBeInTheDocument();
    expect(screen.getByText('Hồ sơ ban đầu')).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });

    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);
    expect(screen.queryByLabelText('Đang tải danh sách hồ sơ')).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it('does not enter loading state when typing only whitespace and clearing', async () => {
    vi.useFakeTimers();
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [
        {
          id: 1,
          stt_uu_tien: 1,
          so_ky_hieu: 'HS-01',
          ten_ho_so: 'Hồ sơ test',
          is_he_thong: false,
        },
      ],
      count: 1,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Tìm theo tên hoặc số/ký hiệu hồ sơ...');
    fireEvent.change(input, { target: { value: '    ' } });

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    const clearBtn = screen.getByLabelText('Đặt lại');
    act(() => {
      fireEvent.click(clearBtn);
    });

    expect(input).toHaveValue('');
    expect(screen.queryByLabelText('Đang tải danh sách hồ sơ')).not.toBeInTheDocument();
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('reloads with empty search and resets to page 1 when clearing active search', async () => {
    vi.useFakeTimers();
    vi.mocked(recordsService.listDossiers).mockResolvedValue({
      items: [
        {
          id: 1,
          stt_uu_tien: 1,
          so_ky_hieu: 'HS-01',
          ten_ho_so: 'Hồ sơ kiểm thử',
          is_he_thong: false,
        },
      ],
      count: 1,
      next: null,
      previous: null,
    });

    render(
      <MemoryRouter>
        <DossiersPage />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });

    const input = screen.getByPlaceholderText('Tìm theo tên hoặc số/ký hiệu hồ sơ...');
    fireEvent.change(input, { target: { value: 'kiểm thử' } });

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });

    expect(recordsService.listDossiers).toHaveBeenCalledTimes(2);

    const clearBtn = screen.getByLabelText('Đặt lại');
    await act(async () => {
      fireEvent.click(clearBtn);
      await Promise.resolve();
    });

    expect(input).toHaveValue('');
    expect(recordsService.listDossiers).toHaveBeenCalledTimes(3);
    expect(recordsService.listDossiers).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: '', page: 1 })
    );
    expect(screen.queryByLabelText('Đang tải danh sách hồ sơ')).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
