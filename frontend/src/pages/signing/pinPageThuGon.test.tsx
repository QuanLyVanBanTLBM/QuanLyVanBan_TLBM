/**
 * Trang PIN: tài khoản đã có PIN thì thu gọn form về nút, bấm nút mới mở form.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { NguoiDungHienTai } from '@lib/signing/types';
import PinPage from './PinPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return {
    ...actual,
    signingApi: {
      pinTrangThai: vi.fn(),
      pinOtpYeuCau: vi.fn(),
      pinOtpXacNhan: vi.fn(),
      pinOtpHuy: vi.fn(),
      taiLenAnhChuKy: vi.fn(),
      xoaAnhChuKy: vi.fn(),
      tepAnhChuKyCaNhan: vi.fn(),
    },
  };
});

const api = vi.mocked(signingApi);
const TOI = {
  id: 7,
  ten: 'Người ký',
  don_vi_id: 1,
  la_quan_tri: false,
  la_lanh_dao_don_vi: false,
  co_anh_chu_ky: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;

const moTrang = () => render(
  <MemoryRouter>
    <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
      <PinPage />
    </SigningContext.Provider>
  </MemoryRouter>,
);

const NUT_MO = 'Đổi hoặc khôi phục PIN';

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.pinTrangThai.mockResolvedValue({ da_dat_pin: true } as never);
});

describe('PinPage: thu gọn form khi đã có PIN', () => {
  it('đã có PIN thì chỉ thấy nút, không thấy ô nhập PIN', async () => {
    moTrang();
    expect(await screen.findByRole('button', { name: NUT_MO })).toBeInTheDocument();
    expect(screen.queryByText('PIN mới (6 chữ số)')).not.toBeInTheDocument();
    expect(screen.queryByText('Nhập lại PIN')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi OTP' })).not.toBeInTheDocument();
  });

  it('bấm nút thì mở form, Hủy bỏ thì thu gọn lại', async () => {
    moTrang();
    fireEvent.click(await screen.findByRole('button', { name: NUT_MO }));
    expect(screen.getByText('PIN mới (6 chữ số)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gửi OTP' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: NUT_MO })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Hủy bỏ' }));
    expect(await screen.findByRole('button', { name: NUT_MO })).toBeInTheDocument();
    expect(screen.queryByText('PIN mới (6 chữ số)')).not.toBeInTheDocument();
  });

  it('chưa có PIN thì hiện form, không có nút đổi hoặc khôi phục', async () => {
    api.pinTrangThai.mockResolvedValue({ da_dat_pin: false } as never);
    moTrang();
    expect(await screen.findByText('PIN mới (6 chữ số)')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: NUT_MO })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hủy bỏ' })).not.toBeInTheDocument();
  });

  it('đang tải trạng thái thì không hiện form', async () => {
    api.pinTrangThai.mockReturnValue(new Promise(() => undefined));
    moTrang();
    expect(screen.queryByText('PIN mới (6 chữ số)')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: NUT_MO })).not.toBeInTheDocument();
  });

  it('lưu PIN thành công thì báo thành công và thu gọn về nút', async () => {
    api.pinOtpYeuCau.mockResolvedValue({ challenge_id: 'c1', kenh: 'SMS', gian_cach_giay: 0 } as never);
    api.pinOtpXacNhan.mockResolvedValue({} as never);
    moTrang();
    fireEvent.click(await screen.findByRole('button', { name: NUT_MO }));
    const o = document.querySelectorAll('input[type="password"]');
    fireEvent.change(o[0], { target: { value: '123456' } });
    fireEvent.change(o[1], { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: 'Gửi OTP' }));
    const maOtp = await screen.findByLabelText(/Mã OTP/);
    fireEvent.change(maOtp, { target: { value: '654321' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận và lưu PIN' }));
    expect(await screen.findByText(/Đã lưu PIN ký/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: NUT_MO })).toBeInTheDocument());
    expect(screen.queryByText('PIN mới (6 chữ số)')).not.toBeInTheDocument();
  });
});
