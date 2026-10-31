/**
 * Ký duyệt gửi kèm ảnh chữ ký cá nhân (#420): ảnh đọc từ nơi lưu của trình duyệt đi cùng yêu cầu ký để
 * server chụp snapshot; thiếu ảnh thì chặn ký như trước.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, KhoaKy, NguoiDungHienTai } from '@lib/signing/types';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { khoa: vi.fn(), ky: vi.fn() } };
});
vi.mock('@lib/signing/luongKhoa', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/luongKhoa')>('@lib/signing/luongKhoa');
  return { ...actual, kyBangPin: vi.fn().mockResolvedValue('chu-ky-so') };
});
const api = vi.mocked(signingApi);

const TOI = {
  id: 7, ten: 'Người ký', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;
const KHOA = { id: 4, ma_khoa: 'TB-7-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
  khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
const MA_BAM = 'a'.repeat(64);
const ANH = 'data:image/png;base64,iVBORw0KGgo=';

const hoSo = {
  id: 12, trang_thai: 'CHO_KY', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }, create_by: 3,
  dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Người ký', vai_tro_ky: 'KY_CHINH' }],
  luot_trinh: [{ id: 5, trang_thai: 'CHO_KY', ma_bam_tai_lieu: MA_BAM, cap_ky: [], yeu_cau_sua: [] }],
} as unknown as HoSoChiTiet;

const moHopKy = () => {
  render(
    <MemoryRouter>
      <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
        <HanhDong hoSo={hoSo} luot={hoSo.luot_trinh[0]} maBamTepDangXem={MA_BAM} onXong={() => undefined} />
      </SigningContext.Provider>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  localStorage.setItem('tlbm_user_sig_7', ANH);
  api.khoa.mockResolvedValue([KHOA]);
  api.ky.mockResolvedValue(hoSo);
});

describe('Ký duyệt gửi ảnh chữ ký', () => {
  it('gửi ảnh chữ ký đã lưu cùng yêu cầu ký', async () => {
    moHopKy();
    const oPin = await screen.findByLabelText(/Nhập PIN ký/);
    await waitFor(() => expect(oPin).toBeEnabled());
    fireEvent.change(oPin, { target: { value: '48271593' } });
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Ký duyệt/ }));
    await waitFor(() => expect(api.ky).toHaveBeenCalledTimes(1));
    expect(api.ky.mock.calls[0][2]).toMatchObject({
      khoa_ky: 4, hash_tai_lieu: MA_BAM, chu_ky_so: 'chu-ky-so', anh_chu_ky: ANH,
    });
  });

  it('chưa có ảnh chữ ký: không gọi API ký', async () => {
    localStorage.removeItem('tlbm_user_sig_7');
    moHopKy();
    expect(await screen.findByText('Chưa có ảnh chữ ký cá nhân')).toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: /Ký duyệt/ })).toBeDisabled();
    expect(api.ky).not.toHaveBeenCalled();
  });
});
