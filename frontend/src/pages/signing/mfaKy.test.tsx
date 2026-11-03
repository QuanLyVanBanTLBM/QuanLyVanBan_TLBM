/**
 * MFA qua email khi ký (#510): bước nhập mã trong hộp thoại ký chỉ hiện khi máy chủ báo MFA bật và phiên chưa xác
 * thực; gửi mã, 6 ô nhập, gửi lại có đếm ngược, HTTP 429, mã sai.
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, KhoaKy, NguoiDungHienTai } from '@lib/signing/types';
import { ApiError } from '@lib/apiClient';
import { setLanguage } from '@i18n/translate';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { khoa: vi.fn(), ky: vi.fn(), mfaKyYeuCau: vi.fn(), mfaKyXacMinh: vi.fn() } };
});
vi.mock('@lib/signing/luongKhoa', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/luongKhoa')>('@lib/signing/luongKhoa');
  return { ...actual, kyBangPin: vi.fn().mockResolvedValue('chu-ky-so') };
});
const api = vi.mocked(signingApi);

const MFA_CHUA = { bat: true, da_xac_thuc: false, het_han: null };
const toi = (mfa?: NguoiDungHienTai['mfa_ky']) => ({
  id: 7, ten: 'Người ký', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false, co_anh_chu_ky: true,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
  ...(mfa ? { mfa_ky: mfa } : {}),
}) as NguoiDungHienTai;
const KHOA = { id: 4, ma_khoa: 'TB-7-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
  khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
const MA_BAM = 'a'.repeat(64);
const hoSo = {
  id: 12, trang_thai: 'CHO_KY', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }, create_by: 3,
  dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Người ký', vai_tro_ky: 'KY_CHINH' }],
  luot_trinh: [{ id: 5, trang_thai: 'CHO_KY', ma_bam_tai_lieu: MA_BAM, cap_ky: [], yeu_cau_sua: [] }],
} as unknown as HoSoChiTiet;

const taiLaiToi = vi.fn();
const moHopKy = (nguoi: NguoiDungHienTai) => {
  render(
    <MemoryRouter>
      <SigningContext.Provider value={{ toi: nguoi, taiLaiToi }}>
        <HanhDong hoSo={hoSo} luot={hoSo.luot_trinh[0]} maBamTepDangXem={MA_BAM} onXong={() => undefined} />
      </SigningContext.Provider>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: /Ký duyệt|Sign and approve/ }));
};
const hopKy = () => screen.getByRole('dialog');
const nutKy = () => within(hopKy()).getByRole('button', { name: /^Ký duyệt$/ });
const guiMa = async () => fireEvent.click(await screen.findByRole('button', { name: 'Gửi mã xác thực' }));
const dan6So = async (ma: string) => {
  const o1 = await screen.findByLabelText('Chữ số 1 của mã xác thực');
  fireEvent.change(o1, { target: { value: ma } });
};

beforeEach(() => {
  vi.clearAllMocks();
  setLanguage('vi');
  api.khoa.mockResolvedValue([KHOA]);
  api.mfaKyYeuCau.mockResolvedValue({ het_han: new Date(Date.now() + 600_000).toISOString(), gian_cach_giay: 120 });
});
afterEach(() => {
  vi.useRealTimers();
  setLanguage('vi');
});

describe('MFA khi ký: cờ tắt', () => {
  it.each([
    ['máy chủ cũ không trả mfa_ky', undefined],
    ['mfa_ky.bat = false', { bat: false, da_xac_thuc: false, het_han: null }],
    ['phiên đã xác thực', { bat: true, da_xac_thuc: true, het_han: '2026-11-03T20:00:00Z' }],
  ])('không hiện bước nhập mã khi %s', async (_ten, mfa) => {
    moHopKy(toi(mfa));
    const oPin = await screen.findByLabelText(/Nhập PIN ký/);
    await waitFor(() => expect(oPin).toBeEnabled());
    expect(screen.queryByText('Xác thực qua email')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi mã xác thực' })).not.toBeInTheDocument();
  });
});

describe('MFA khi ký: cờ bật, phiên chưa xác thực', () => {
  it('hiện bước nhập mã, khóa ký đến khi xác thực, rồi tải lại trạng thái người dùng', async () => {
    api.mfaKyXacMinh.mockResolvedValue({ da_xac_thuc: true, het_han: '2026-11-03T20:00:00Z' });
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    expect(api.mfaKyYeuCau).toHaveBeenCalledTimes(1);
    expect(nutKy()).toBeDisabled();
    expect(screen.getByLabelText(/Nhập PIN ký/)).toBeDisabled();
    expect(await screen.findByRole('button', { name: 'Xác nhận mã' })).toBeDisabled();
    expect(await screen.findAllByLabelText(/^Chữ số \d của mã xác thực$/)).toHaveLength(6);
    await dan6So('123456');
    for (let i = 1; i <= 6; i += 1) {
      expect(screen.getByLabelText(`Chữ số ${i} của mã xác thực`)).toHaveValue(String(i));
    }
    fireEvent.click(await screen.findByRole('button', { name: 'Xác nhận mã' }));
    await waitFor(() => expect(api.mfaKyXacMinh).toHaveBeenCalledWith('123456'));
    await waitFor(() => expect(taiLaiToi).toHaveBeenCalled());
    expect(screen.getByText('Đã xác thực. Có thể ký.')).toBeInTheDocument();
    expect(api.ky).not.toHaveBeenCalled();
  });

  it('nhập từng ô tự chuyển ô; ký lại được sau khi trạng thái người dùng báo đã xác thực', async () => {
    api.ky.mockResolvedValue(hoSo);
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    const o1 = await screen.findByLabelText('Chữ số 1 của mã xác thực');
    fireEvent.change(o1, { target: { value: '9' } });
    expect(screen.getByLabelText('Chữ số 2 của mã xác thực')).toHaveFocus();
    fireEvent.change(screen.getByLabelText('Chữ số 2 của mã xác thực'), { target: { value: 'a' } });
    expect(screen.getByLabelText('Chữ số 2 của mã xác thực')).toHaveValue('');
  });

  it('nút gửi lại bị khóa và đếm ngược theo giãn cách máy chủ trả', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    const nutLai = await screen.findByRole('button', { name: 'Gửi lại sau 120 giây' });
    expect(nutLai).toBeDisabled();
    expect(screen.getByRole('timer')).toHaveTextContent('Mã hết hạn sau 10:00');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(screen.getByRole('button', { name: /^Gửi lại sau 11[5-8] giây$/ })).toBeDisabled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120_000);
    });
    expect(screen.getByRole('button', { name: 'Gửi lại mã' })).toBeEnabled();
  });

  it('HTTP 429 khi gửi mã: hiện thông báo riêng và đếm ngược theo thời điểm máy chủ trả', async () => {
    const thuLai = new Date(Date.now() + 90_000).toISOString();
    api.mfaKyYeuCau.mockRejectedValue(
      new ApiError(429, { code: 'gui_ma_qua_nhanh', detail: 'x', fields: { thu_lai_sau: [thuLai] } } as never),
    );
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    expect(await screen.findByText(/Chờ 2 phút trước khi gửi lại/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Gửi lại sau (89|90) giây$/ })).toBeDisabled();
  });

  it('mã sai: nêu số lần còn lại và xóa các ô', async () => {
    api.mfaKyXacMinh.mockRejectedValue(
      new ApiError(400, { code: 'mfa_ma_sai', detail: 'x', fields: { so_lan_con_lai: [3] } } as never),
    );
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    await dan6So('654321');
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận mã' }));
    expect(await screen.findByText('Mã xác thực không đúng. Còn 3 lần thử.')).toBeInTheDocument();
    expect(screen.getByLabelText('Chữ số 1 của mã xác thực')).toHaveValue('');
    expect(taiLaiToi).not.toHaveBeenCalled();
  });

  it('mã bị hủy sau quá số lần nhập: quay lại bước gửi mã mới', async () => {
    api.mfaKyXacMinh.mockRejectedValue(new ApiError(400, { code: 'mfa_vuot_gioi_han_nhap', detail: 'x' } as never));
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    await dan6So('111111');
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận mã' }));
    expect(await screen.findByText(/Nhập sai quá 5 lần, mã đã bị hủy/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Chữ số 1 của mã xác thực')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Gửi (lại sau \d+ giây|mã xác thực)$/ })).toBeInTheDocument();
  });

  it('HTTP 429 khi nhập mã: khóa ô nhập 60 giây kèm đếm ngược', async () => {
    api.mfaKyXacMinh.mockRejectedValue(new ApiError(429, { detail: 'x' } as never));
    moHopKy(toi(MFA_CHUA));
    await guiMa();
    await dan6So('222222');
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận mã' }));
    expect(await screen.findByText('Quá nhiều lần thử. Nhập lại sau 60 giây.')).toBeInTheDocument();
    expect(screen.getByLabelText('Chữ số 1 của mã xác thực')).toBeDisabled();
  });

  it('tiếng Anh: hiện nhãn và thông báo lỗi bản en', async () => {
    setLanguage('en');
    api.mfaKyXacMinh.mockRejectedValue(new ApiError(400, { code: 'mfa_ma_het_han', detail: 'x' } as never));
    moHopKy(toi(MFA_CHUA));
    fireEvent.click(await screen.findByRole('button', { name: 'Send verification code' }));
    const o1 = await screen.findByLabelText('Digit 1 of the verification code');
    fireEvent.change(o1, { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm code' }));
    expect(await screen.findByText('The code has expired. Send a new code.')).toBeInTheDocument();
  });
});
