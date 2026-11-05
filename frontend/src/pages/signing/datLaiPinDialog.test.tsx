/**
 * Đặt lại PIN bằng mã xác thực qua email (#478): gửi mã, đếm ngược gửi lại, nhập mã, báo lỗi theo mã lỗi.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@lib/apiClient';
import { signingApi } from '@lib/signing/api';
import DatLaiPinDialog from '@components/signing/DatLaiPinDialog';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { datLaiPinYeuCau: vi.fn(), datLaiPinXacNhan: vi.fn() } };
});
const api = vi.mocked(signingApi);

const loiApi = (status: number, code: string) => new ApiError(status, { code, detail: 'x' });

function hien(onXong = vi.fn(), onDong = vi.fn()) {
  render(<DatLaiPinDialog mo onDong={onDong} onXong={onXong} />);
  return { onXong, onDong };
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
});
afterEach(() => vi.useRealTimers());

describe('DatLaiPinDialog', () => {
  it('sends the code, then enables confirm only for a 6-digit code and reports success', async () => {
    api.datLaiPinYeuCau.mockResolvedValue({ het_han: '2026-11-02T03:00:00Z', gian_cach_giay: 120 });
    api.datLaiPinXacNhan.mockResolvedValue({ da_dat_lai_pin: true, khoa: 1 });
    const { onXong } = hien();
    expect(screen.queryByRole('button', { name: 'Xác nhận và cập nhật PIN' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' }));
    const o = await screen.findByLabelText(/Mã xác thực/);
    const xacNhan = screen.getByRole('button', { name: 'Xác nhận và cập nhật PIN' });
    expect(xacNhan).toBeDisabled();
    fireEvent.change(o, { target: { value: '12ab34' } });
    expect(o).toHaveValue('1234');
    fireEvent.change(o, { target: { value: '123456' } });
    fireEvent.change(screen.getByLabelText(/^PIN mới/), { target: { value: '482739' } });
    expect(xacNhan).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/^Nhập lại PIN mới/), { target: { value: '482738' } });
    expect(xacNhan).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/^Nhập lại PIN mới/), { target: { value: '482739' } });
    expect(xacNhan).toBeEnabled();
    fireEvent.click(xacNhan);
    await waitFor(() => expect(api.datLaiPinXacNhan).toHaveBeenCalledWith('123456', '482739'));
    await waitFor(() => expect(onXong).toHaveBeenCalledWith('482739'));
  });

  it('counts down before allowing a resend', async () => {
    vi.useFakeTimers();
    api.datLaiPinYeuCau.mockResolvedValue({ het_han: '2026-11-02T03:00:00Z', gian_cach_giay: 2 });
    hien();
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' })); });
    const guiLai = screen.getByRole('button', { name: /Gửi lại sau 2 giây/ });
    expect(guiLai).toBeDisabled();
    await act(async () => { vi.advanceTimersByTime(1000); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('button', { name: 'Gửi lại mã' })).toBeEnabled();
  });

  it.each([
    ['tai_khoan_chua_co_email', 400, 'Tài khoản chưa cập nhật email công vụ để nhận mã xác thực. Liên hệ quản trị viên.'],
    ['gui_ma_qua_nhanh', 429, 'Vừa gửi mã xác thực. Chờ 2 phút trước khi gửi lại.'],
  ])('shows the message for send error %s', async (code, status, thongDiep) => {
    api.datLaiPinYeuCau.mockRejectedValue(loiApi(status, code));
    hien();
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' }));
    expect(await screen.findByText(thongDiep)).toBeInTheDocument();
  });

  it('locks the send button with a countdown when the server returns a short retry time (HTTP 429)', async () => {
    const thuLai = new Date(Date.now() + 45_000).toISOString();
    api.datLaiPinYeuCau.mockRejectedValue(
      new ApiError(429, { code: 'gui_ma_qua_nhanh', detail: 'x', fields: { thu_lai_sau: [thuLai] } }),
    );
    hien();
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' }));
    const nut = await screen.findByRole('button', { name: /Gửi lại sau \d+ giây/ });
    expect(nut).toBeDisabled();
  });

  it('does not start a countdown for a long daily limit but names the retry time', async () => {
    const thuLai = new Date(Date.now() + 5 * 3600_000).toISOString();
    api.datLaiPinYeuCau.mockRejectedValue(
      new ApiError(429, { code: 'gioi_han_khac', detail: 'x', fields: { thu_lai_sau: [thuLai] } }),
    );
    hien();
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' }));
    expect(await screen.findByText(/Đã chạm giới hạn thao tác\. Thử lại sau/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gửi mã xác thực' })).toBeEnabled();
  });

  it('shows the message for a wrong code and keeps the dialog open', async () => {
    api.datLaiPinYeuCau.mockResolvedValue({ het_han: '2026-11-02T03:00:00Z', gian_cach_giay: 120 });
    api.datLaiPinXacNhan.mockRejectedValue(loiApi(400, 'ma_khong_dung'));
    const { onXong } = hien();
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã xác thực' }));
    fireEvent.change(await screen.findByLabelText(/Mã xác thực/), { target: { value: '654321' } });
    fireEvent.change(screen.getByLabelText(/^PIN mới/), { target: { value: '482739' } });
    fireEvent.change(screen.getByLabelText(/^Nhập lại PIN mới/), { target: { value: '482739' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận và cập nhật PIN' }));
    expect(await screen.findByText('Mã xác thực không đúng.')).toBeInTheDocument();
    expect(onXong).not.toHaveBeenCalled();
  });
});
