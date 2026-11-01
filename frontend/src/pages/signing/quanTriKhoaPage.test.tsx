/**
 * Tab quản lý khóa ký và quyền ký (quản trị viên, phân vùng 3 của #447): danh sách, khóa/bật lại quyền ký,
 * thu hồi khóa, lý do bắt buộc, thông báo khóa cho người dùng bị khóa.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@lib/apiClient';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { NguoiDungHienTai, QuanTriNguoiDung } from '@lib/signing/types';
import QuanTriKhoaPage from './QuanTriKhoaPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    quanTriNguoiDung: vi.fn(), quanTriKhoaQuyenKy: vi.fn(), quanTriBatLaiQuyenKy: vi.fn(), quanTriThuHoiKhoa: vi.fn(),
  } };
});
const api = vi.mocked(signingApi);

const QUAN_TRI: NguoiDungHienTai = {
  id: 1, ten: 'Quản trị', don_vi_id: 1, la_quan_tri: true, la_lanh_dao_don_vi: false, quyen: { sign_trinhky: true },
};

function nguoi(sua: Partial<QuanTriNguoiDung> = {}): QuanTriNguoiDung {
  return {
    id: 7, ten: 'Người ký A', ten_dang_nhap: 'nguoi_ky_a', chuc_vu: 'Chuyên viên', don_vi: 'Phòng A', co_quyen_ky: true,
    khoa_ky: { id: 3, ma_khoa: 'KHOA-A', trang_thai: 'HOAT_DONG' }, pin: null, khoa_quyen_ky: null, ...sua,
  };
}

const boc = (toi: NguoiDungHienTai = QUAN_TRI) => render(
  <MemoryRouter><SigningContext.Provider value={{ toi, taiLaiToi: () => undefined }}><QuanTriKhoaPage /></SigningContext.Provider></MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.quanTriNguoiDung.mockResolvedValue([nguoi()]);
});

describe('QuanTriKhoaPage', () => {
  it('shows notice instead of the table for non-admin accounts', () => {
    boc({ ...QUAN_TRI, la_quan_tri: false });
    expect(screen.getByText('Chỉ quản trị viên được dùng chức năng này.')).toBeInTheDocument();
  });

  it('lists accounts with key, PIN and signing right state', async () => {
    api.quanTriNguoiDung.mockResolvedValue([
      nguoi(),
      nguoi({ id: 8, ten: 'Người ký B', ten_dang_nhap: 'nguoi_ky_b', khoa_ky: null,
        pin: { so_lan_sai: 10, khoa_den: null, khoa_cung: true, dang_khoa: false },
        khoa_quyen_ky: { id: 1, khoa_tu: '2026-11-01T01:00:00Z', khoa_den: null, ly_do: 'Nghi ngờ lộ khóa', nguoi_khoa_id: 1 } }),
    ]);
    boc();
    expect(await screen.findByText('Người ký A')).toBeInTheDocument();
    expect(screen.getByText('KHOA-A')).toBeInTheDocument();
    expect(screen.getByText('Khóa cứng')).toBeInTheDocument();
    expect(screen.getByText('Đang bị khóa đến khi được bật lại')).toBeInTheDocument();
    expect(screen.getByText('Nghi ngờ lộ khóa')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Bật lại quyền ký/ })).toHaveLength(1);
  });

  it('requires a reason before locking and sends duration and reason', async () => {
    api.quanTriKhoaQuyenKy.mockResolvedValue(nguoi());
    boc();
    fireEvent.click(await screen.findByRole('button', { name: /Khóa quyền ký/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận' }));
    expect(await screen.findByText('Phải nhập lý do.')).toBeInTheDocument();
    expect(api.quanTriKhoaQuyenKy).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(/Thời hạn khóa/), { target: { value: '24_gio' } });
    fireEvent.change(screen.getByLabelText(/Lý do/), { target: { value: 'Kiểm tra bảo mật' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận' }));
    await waitFor(() => expect(api.quanTriKhoaQuyenKy).toHaveBeenCalledWith(7, '24_gio', 'Kiểm tra bảo mật'));
    expect(await screen.findByText('Đã khóa quyền ký của Người ký A.')).toBeInTheDocument();
    expect(api.quanTriNguoiDung).toHaveBeenCalledTimes(2);
  });

  it('restores the signing right with a reason', async () => {
    api.quanTriNguoiDung.mockResolvedValue([nguoi({
      khoa_quyen_ky: { id: 1, khoa_tu: '2026-11-01T01:00:00Z', khoa_den: '2026-11-02T01:00:00Z', ly_do: 'x', nguoi_khoa_id: 1 } })]);
    api.quanTriBatLaiQuyenKy.mockResolvedValue(nguoi());
    boc();
    fireEvent.click(await screen.findByRole('button', { name: /Bật lại quyền ký/ }));
    fireEvent.change(screen.getByLabelText(/Lý do/), { target: { value: 'Đã xác minh danh tính' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận' }));
    await waitFor(() => expect(api.quanTriBatLaiQuyenKy).toHaveBeenCalledWith(7, 'Đã xác minh danh tính'));
    expect(await screen.findByText('Đã bật lại quyền ký của Người ký A.')).toBeInTheDocument();
  });

  it('revokes the key and shows API errors by code', async () => {
    api.quanTriThuHoiKhoa.mockRejectedValue(new ApiError(409, { code: 'khong_co_khoa_de_thu_hoi', detail: 'x' }));
    boc();
    fireEvent.click(await screen.findByRole('button', { name: /Thu hồi khóa ký/ }));
    fireEvent.change(screen.getByLabelText(/Lý do/), { target: { value: 'Mất thiết bị' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận' }));
    await waitFor(() => expect(api.quanTriThuHoiKhoa).toHaveBeenCalledWith(7, 'Mất thiết bị'));
    expect(await screen.findByText('Tài khoản không có khóa ký nào để thu hồi.')).toBeInTheDocument();
  });
});
