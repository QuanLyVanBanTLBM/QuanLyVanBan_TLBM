/**
 * Ký duyệt dùng ảnh chữ ký cá nhân lưu ở máy chủ (#459): trình duyệt không gửi ảnh kèm yêu cầu ký, máy chủ tự
 * chụp snapshot; người dùng chưa có ảnh thì chặn ký.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, NguoiDungHienTai } from '@lib/signing/types';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { ky: vi.fn() } };
});
const api = vi.mocked(signingApi);

const TOI = {
  id: 7, ten: 'Người ký', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  co_anh_chu_ky: true, da_dat_pin: true,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;
const MA_BAM = 'a'.repeat(64);

const hoSo = {
  id: 12, trang_thai: 'CHO_KY', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }, create_by: 3,
  dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Người ký', vai_tro_ky: 'KY_CHINH' }],
  luot_trinh: [{ id: 5, trang_thai: 'CHO_KY', ma_bam_tai_lieu: MA_BAM, cap_ky: [], yeu_cau_sua: [] }],
} as unknown as HoSoChiTiet;

const moHopKy = (nguoi: NguoiDungHienTai = TOI) => {
  render(
    <MemoryRouter>
      <SigningContext.Provider value={{ toi: nguoi, taiLaiToi: () => undefined }}>
        <HanhDong hoSo={hoSo} luot={hoSo.luot_trinh[0]} maBamTepDangXem={MA_BAM} onXong={() => undefined} />
      </SigningContext.Provider>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.ky.mockResolvedValue(hoSo);
});

describe('Ký duyệt dùng ảnh chữ ký ở máy chủ', () => {
  it('không gửi ảnh kèm yêu cầu ký (máy chủ tự áp dụng snapshot)', async () => {
    moHopKy();
    const oPin = await screen.findByLabelText(/Nhập PIN ký/);
    await waitFor(() => expect(oPin).toBeEnabled());
    fireEvent.change(oPin, { target: { value: '482739' } });
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Ký duyệt/ }));
    await waitFor(() => expect(api.ky).toHaveBeenCalledTimes(1));
    expect(api.ky.mock.calls[0][2]).toEqual({
      hash_tai_lieu: MA_BAM, pin: '482739', ghi_chu_ky: '',
    });
  });

  it('chưa có ảnh chữ ký: không gọi API ký', async () => {
    moHopKy({ ...TOI, co_anh_chu_ky: false });
    expect(await screen.findByText('Chưa có ảnh chữ ký cá nhân')).toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: /Ký duyệt/ })).toBeDisabled();
    expect(api.ky).not.toHaveBeenCalled();
  });
});
