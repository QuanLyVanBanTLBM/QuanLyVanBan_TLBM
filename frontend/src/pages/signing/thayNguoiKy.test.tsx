/**
 * Thay người ký (#500): hộp thoại chọn người thay kèm lý do bắt buộc; nút "Thay người ký" ở trang chi tiết chỉ hiện
 * khi máy chủ báo người ký đang chờ có thể thay (cờ `co_the_thay`).
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ThayNguoiKyDialog from '@components/signing/ThayNguoiKyDialog';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, NguoiDungHienTai, NguoiKyLuot } from '@lib/signing/types';
import ChiTietPage from './ChiTietPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    chiTiet: vi.fn(), ungVienThayNguoiKy: vi.fn(), thayNguoiKy: vi.fn(), tepCuaLuot: vi.fn(), tepGoc: vi.fn(),
    tepHoanTat: vi.fn(), bangChung: vi.fn(), khoa: vi.fn(), tepTaiLieu: vi.fn(), anhChuKy: vi.fn(),
  } };
});
const api = vi.mocked(signingApi);

const TOI = {
  id: 3, ten: 'Văn thư', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: true, sign_trinhky: false, send_trinhky: true },
} as NguoiDungHienTai;

const nguoiKy = (ghiDe: Partial<NguoiKyLuot> = {}) => ({
  id: 21, nguoi_ky: 7, ten_nguoi_ky: 'Trưởng phòng A', ten_chuc_vu: 'Trưởng phòng', vai_tro_ky: 'KY_CHINH',
  trang_thai: 'CHO_KY', co_the_thay: true, ...ghiDe,
}) as NguoiKyLuot;

const hoSo = (nguoi: NguoiKyLuot): HoSoChiTiet => ({
  id: 12, document_type: 'vanbandi', van_ban_id: 3, van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
  trang_thai: 'CHO_KY', create_by: 3, ten_nguoi_tao: 'Văn thư', ten_quy_trinh: 'Quy trình', ma_bam_tai_lieu: 'a'.repeat(64),
  dang_cho: [], lich_su: [],
  luot_trinh: [{
    id: 5, so_luot: 1, trang_thai: 'CHO_KY', ma_bam_tai_lieu: 'a'.repeat(64), yeu_cau_sua: [],
    cap_ky: [{ id: 9, cap_ky: 1, ten_cap_ky: 'Cấp 1', thu_tu: 1, trang_thai: 'DANG_KY', han_xu_ly: null, nguoi_ky: [nguoi] }],
  }],
}) as unknown as HoSoChiTiet;

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.ungVienThayNguoiKy.mockResolvedValue([
    { id: 31, ten: 'Phó phòng B', chuc_vu: 'Phó phòng', don_vi: 'Phòng Kế toán' },
    { id: 32, ten: 'Chuyên viên C', chuc_vu: null, don_vi: null },
  ]);
});

describe('ThayNguoiKyDialog', () => {
  const mo = (onXong = vi.fn()) => {
    render(<ThayNguoiKyDialog hoSo={hoSo(nguoiKy())} nguoiKyThayDuoc={[nguoiKy()]} onDong={vi.fn()} onXong={onXong} />);
    return onXong;
  };

  it('chỉ cho xác nhận khi đã chọn người thay và nhập lý do, rồi gửi đúng nội dung', async () => {
    const moi = hoSo(nguoiKy({ nguoi_ky: 31, ten_nguoi_ky: 'Phó phòng B' }));
    api.thayNguoiKy.mockResolvedValue(moi);
    const onXong = mo();
    const nutXacNhan = screen.getByRole('button', { name: 'Thay người ký' });
    expect(nutXacNhan).toBeDisabled();
    await waitFor(() => expect(api.ungVienThayNguoiKy).toHaveBeenCalledWith(12, 21, ''));
    fireEvent.change(await screen.findByRole('combobox', { name: 'Chọn người ký mới' }), { target: { value: '31' } });
    expect(nutXacNhan).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Lý do thay người ký/), { target: { value: '   ' } });
    expect(nutXacNhan).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Lý do thay người ký/), { target: { value: ' Nghỉ phép dài ngày ' } });
    expect(nutXacNhan).toBeEnabled();
    fireEvent.click(nutXacNhan);
    await waitFor(() => expect(api.thayNguoiKy).toHaveBeenCalledWith(12, {
      nguoi_ky_id: 21, nguoi_ky_moi_id: 31, ly_do: 'Nghỉ phép dài ngày',
    }));
    await waitFor(() => expect(onXong).toHaveBeenCalledWith(moi));
  });

  it('tìm ứng viên theo từ khóa và hiện thông báo khi không có ai phù hợp', async () => {
    api.ungVienThayNguoiKy.mockResolvedValue([]);
    mo();
    fireEvent.change(screen.getByLabelText('Tìm theo tên, chức vụ, đơn vị'), { target: { value: 'xyz' } });
    await waitFor(() => expect(api.ungVienThayNguoiKy).toHaveBeenCalledWith(12, 21, 'xyz'));
    expect(await screen.findByText(/Không có tài khoản phù hợp/)).toBeInTheDocument();
  });

  it('hiện lỗi nghiệp vụ của máy chủ và không đóng hộp thoại', async () => {
    api.thayNguoiKy.mockRejectedValue(Object.assign(new Error('x'), {
      status: 409, data: { code: 'nguoi_ky_khong_bi_khoa_quyen_ky' },
    }));
    const onXong = mo();
    fireEvent.change(await screen.findByRole('combobox', { name: 'Chọn người ký mới' }), { target: { value: '32' } });
    fireEvent.change(screen.getByLabelText(/Lý do thay người ký/), { target: { value: 'Lý do' } });
    fireEvent.click(screen.getByRole('button', { name: 'Thay người ký' }));
    await waitFor(() => expect(api.thayNguoiKy).toHaveBeenCalled());
    expect(onXong).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Nút "Thay người ký" ở trang chi tiết hồ sơ', () => {
  const dung = async (nguoi: NguoiKyLuot) => {
    api.chiTiet.mockResolvedValue(hoSo(nguoi));
    api.tepCuaLuot.mockResolvedValue({ buf: new ArrayBuffer(8), maBam: 'a'.repeat(64) } as never);
    api.tepGoc.mockResolvedValue({ buf: new ArrayBuffer(8), maBam: 'a'.repeat(64) } as never);
    api.khoa.mockResolvedValue([]);
    render(
      <MemoryRouter initialEntries={['/approvals/12']}>
        <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
          <Routes><Route path="/approvals/:id" element={<ChiTietPage />} /></Routes>
        </SigningContext.Provider>
      </MemoryRouter>,
    );
    await screen.findByText(/#12/);
  };

  it('hiện khi máy chủ báo có thể thay và mở hộp thoại', async () => {
    await dung(nguoiKy());
    fireEvent.click(await screen.findByRole('button', { name: 'Thay người ký' }));
    expect(await screen.findByRole('dialog', { name: 'Thay người ký' })).toBeInTheDocument();
  });

  it('không hiện khi không có người ký nào thay được', async () => {
    await dung(nguoiKy({ co_the_thay: false }));
    expect(screen.queryByRole('button', { name: 'Thay người ký' })).not.toBeInTheDocument();
  });
});
