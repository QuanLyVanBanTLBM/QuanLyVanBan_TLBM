/**
 * Lối "Quên PIN?" trong hộp thoại ký (#487): đặt PIN mới qua email, giữ khóa hiện tại và mở lại hộp thoại ký.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, KhoaKy, NguoiDungHienTai } from '@lib/signing/types';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { khoa: vi.fn(), ky: vi.fn(), datLaiPinYeuCau: vi.fn(), datLaiPinXacNhan: vi.fn() } };
});
const api = vi.mocked(signingApi);

const TOI = {
  id: 7, ten: 'Người ký', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  co_anh_chu_ky: true,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;
const KHOA = { id: 4, ma_khoa: 'TB-7-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
  khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
const MA_BAM = 'a'.repeat(64);

const hoSo = {
  id: 12, trang_thai: 'CHO_KY', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }, create_by: 3,
  dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Người ký', vai_tro_ky: 'KY_CHINH' }],
  luot_trinh: [{ id: 5, trang_thai: 'CHO_KY', ma_bam_tai_lieu: MA_BAM, cap_ky: [], yeu_cau_sua: [] }],
} as unknown as HoSoChiTiet;

const moHopKy = () => {
  render(
    <MemoryRouter initialEntries={['/approvals/12']}>
      <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
        <Routes>
          <Route path="/approvals/khoa" element={<div>Trang khóa ký</div>} />
          <Route
            path="*"
            element={<HanhDong hoSo={hoSo} luot={hoSo.luot_trinh[0]} maBamTepDangXem={MA_BAM} onXong={() => undefined} />}
          />
        </Routes>
      </SigningContext.Provider>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.khoa.mockResolvedValue([KHOA]);
});

describe('Quên PIN trong hộp thoại ký', () => {
  it('đóng hộp thoại ký, đặt lại PIN giữ khóa hiện tại rồi mở lại ký', async () => {
    api.datLaiPinYeuCau.mockResolvedValue({ het_han: '2026-11-02T03:00:00Z', gian_cach_giay: 120 });
    api.datLaiPinXacNhan.mockResolvedValue({ da_dat_lai_pin: true, khoa: 4 });
    moHopKy();
    fireEvent.click(await screen.findByRole('button', { name: 'Quên PIN?' }));
    const hop = await screen.findByRole('dialog', { name: /Đặt lại PIN/ });
    expect(screen.queryByLabelText(/Nhập PIN ký/)).not.toBeInTheDocument();
    fireEvent.click(within(hop).getByRole('button', { name: 'Gửi mã xác thực' }));
    fireEvent.change(await screen.findByLabelText(/Mã xác thực/), { target: { value: '123456' } });
    fireEvent.change(screen.getByLabelText(/^PIN mới/), { target: { value: '482739' } });
    fireEvent.change(screen.getByLabelText(/^Nhập lại PIN mới/), { target: { value: '482739' } });
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận và cập nhật PIN' }));
    await waitFor(() => expect(api.datLaiPinXacNhan).toHaveBeenCalledWith('123456', '482739'));
    expect(await screen.findByText('Đã cập nhật PIN. Khóa ký và định danh được giữ nguyên.')).toBeInTheDocument();
    expect(await screen.findByLabelText(/Nhập PIN ký/)).toHaveValue('482739');
    await waitFor(() => expect(api.khoa).toHaveBeenCalledTimes(2));
    expect(api.ky).not.toHaveBeenCalled();
  });

  it('đóng hộp thoại đặt lại mà không xác nhận thì ở lại hồ sơ và không thu hồi khóa', async () => {
    moHopKy();
    fireEvent.click(await screen.findByRole('button', { name: 'Quên PIN?' }));
    const hop = await screen.findByRole('dialog', { name: /Đặt lại PIN/ });
    fireEvent.click(within(hop).getAllByRole('button', { name: 'Đóng' }).at(-1)!);
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /Đặt lại PIN/ })).not.toBeInTheDocument());
    expect(screen.queryByText('Trang khóa ký')).not.toBeInTheDocument();
    expect(api.datLaiPinXacNhan).not.toHaveBeenCalled();
  });
});
