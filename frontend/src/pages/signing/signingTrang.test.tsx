/**
 * Trang và panel Trình ký chưa có test: tạo hồ sơ (bước 1), khóa ký & PIN, trao đổi khi trả sửa, kết quả hoàn tất.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import KetQuaPanel from '@components/signing/KetQuaPanel';
import XemPdf from '@components/signing/XemPdf';
import TraoDoiPanel from '@components/signing/TraoDoiPanel';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, KhoaKy, LuotTrinh, NguoiDungHienTai, QuyTrinh } from '@lib/signing/types';
import KhoaPage from './KhoaPage';
import TaoHoSoPage, { Buoc2 } from './TaoHoSoPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    timVanBanDi: vi.fn(), chiTietVanBanDi: vi.fn(), lienKetVanBanDi: vi.fn(), quyTrinh: vi.fn(), taoNhap: vi.fn(), chiTietQuyTrinh: vi.fn(), khoa: vi.fn(),
    traoDoi: vi.fn(), guiTinNhan: vi.fn(), giaiQuyet: vi.fn(), taoLaiTepHoanTat: vi.fn(), tepHoanTat: vi.fn(),
    bangChung: vi.fn(),
  } };
});
vi.mock('@lib/signing/pdf', () => ({
  moPdf: vi.fn().mockResolvedValue({ numPages: 1 }),
  veTrang: vi.fn(() => ({ xong: Promise.resolve({ rong: 600, cao: 800 }), huy: vi.fn() })),
  laLoiHuyVe: (err: { name?: string }) => err?.name === 'RenderingCancelledException',
}));
const api = vi.mocked(signingApi);
const pdf = vi.mocked(await import('@lib/signing/pdf'));

// Khung xem PDF đo chiều rộng bằng ResizeObserver: giả lập rộng 600px để trang được vẽ
class RoGiaLap {
  constructor(private cb: ResizeObserverCallback) {}
  observe() {
    this.cb([{ contentRect: { width: 600 } } as ResizeObserverEntry], this as unknown as ResizeObserver);
  }
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = RoGiaLap as unknown as typeof ResizeObserver;

const TOI: NguoiDungHienTai = {
  id: 3, ten: 'Văn thư', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: true, send_trinhky: true, sign_trinhky: true },
};

const LUOT: LuotTrinh = {
  id: 5, so_luot: 1, luot_truoc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), trang_thai: 'HOAN_THANH',
  ly_do: '', thoi_diem_gui: null, thoi_diem_hoan_thanh: '2026-10-07T01:00:00Z', trang_thai_tep_hoan_tat: 'THANH_CONG',
  loi_tep_hoan_tat: '', ma_bam_tep_hoan_tat: 'b'.repeat(64), ma_bam_bang_chung: 'c'.repeat(64), cap_ky: [], yeu_cau_sua: [],
};

function hoSo(sua: Partial<HoSoChiTiet> = {}): HoSoChiTiet {
  return {
    id: 12, document_type: 'vanbandi', van_ban_id: 3, so_hieu_van_ban: '', trich_yeu_van_ban: '', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
    quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt', phien_ban_quy_trinh: 1, trang_thai: 'HOAN_THANH',
    han_chot: null, ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '', ghi_chu: '', ho_so_goc: null,
    phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3, ten_nguoi_tao: 'Văn thư',
    created_at: '2026-10-07T01:00:00Z', dang_cho: [], trang_thai_luot: 'HOAN_THANH', qua_han: false,
    luot_trinh: [LUOT], lich_su: [], ...sua,
  };
}

const boc = (ui: React.ReactNode, toi: NguoiDungHienTai = TOI) => render(
  <MemoryRouter><SigningContext.Provider value={{ toi, taiLaiToi: () => undefined }}>{ui}</SigningContext.Provider></MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.timVanBanDi.mockResolvedValue([]);
});

describe('TaoHoSoPage', () => {
  it('chỉ lưu nháp khi đã chọn văn bản, quy trình, tệp; gửi đúng dữ liệu', async () => {
    api.timVanBanDi.mockResolvedValue([{ id: 7, so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }]);
    api.chiTietVanBanDi.mockResolvedValue({ id: 7, so_hieu: '15/TTr', trich_yeu: 'Mua sắm', attachments: [
      { id: 99, name: 'du-thao.pdf', file: '/api/documents/7/attachments/99/download/', file_size: 100, is_deleted: false },
    ] });
    api.quyTrinh.mockResolvedValue([{
      id: 2, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt hai cấp', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
      pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0,
    }]);
    api.taoNhap.mockReturnValue(new Promise(() => undefined));
    boc(<TaoHoSoPage />);
    const luu = await screen.findByRole('button', { name: /Lưu nháp và xem trước/ });
    expect(luu).toBeDisabled();
    fireEvent.click(await screen.findByRole('button', { name: /15\/TTr/ }));
    fireEvent.change(await screen.findByLabelText('Tệp PDF trên văn bản đi'), { target: { value: '99' } });
    fireEvent.change(screen.getByLabelText(/Quy trình ký/), { target: { value: '2' } });
    await waitFor(() => expect(luu).toBeEnabled());
    fireEvent.click(luu);
    await waitFor(() => expect(api.taoNhap).toHaveBeenCalledTimes(1));
    const form = api.taoNhap.mock.calls[0][0] as FormData;
    expect([form.get('document_type'), form.get('van_ban_id'), form.get('tep_dinh_kem_id'), form.get('quy_trinh')])
      .toEqual(['vanbandi', '7', '99', '2']);
    expect(form.get('tep')).toBeNull();
  });
});

describe('TaoHoSoPage văn bản trình ký', () => {
  it('không bắt buộc gắn bản ghi văn bản đi: tải PDF dự thảo chưa vào sổ và lưu nháp', async () => {
    api.timVanBanDi.mockResolvedValue([{ id: 7, so_hieu: '15/TTr', trich_yeu: 'Mua sắm' }]);
    api.quyTrinh.mockResolvedValue([{
      id: 2, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt hai cấp', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
      pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0,
    }]);
    api.taoNhap.mockReturnValue(new Promise(() => undefined));
    boc(<TaoHoSoPage />);
    expect(await screen.findByText('Văn bản trình ký')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Tải PDF dự thảo/));
    expect(screen.queryByRole('button', { name: /15\/TTr/ })).not.toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText(/Quy trình ký/), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText(/PDF dự thảo chưa vào sổ/), {
      target: { files: [new File(['%PDF-1.4'], 'to-trinh.pdf', { type: 'application/pdf' })] },
    });
    const luu = screen.getByRole('button', { name: /Lưu nháp và xem trước/ });
    expect(luu).toBeDisabled();  // chưa có trích yếu
    fireEvent.change(screen.getByLabelText('Số hiệu tham chiếu'), { target: { value: '05/TTr' } });
    fireEvent.change(screen.getByLabelText('Trích yếu'), { target: { value: 'Tờ trình đào tạo' } });
    await waitFor(() => expect(luu).toBeEnabled());
    fireEvent.click(luu);
    await waitFor(() => expect(api.taoNhap).toHaveBeenCalledTimes(1));
    const form = api.taoNhap.mock.calls[0][0] as FormData;
    expect([form.get('van_ban_id'), form.get('document_type')]).toEqual([null, null]);
    expect([form.get('so_hieu_van_ban'), form.get('trich_yeu_van_ban'), form.get('quy_trinh')])
      .toEqual(['05/TTr', 'Tờ trình đào tạo', '2']);
  });
});

describe('Buoc2 định vị khung ký', () => {
  const QT_GIA_LAP = {
    id: 1, ma_quy_trinh: 'QT1', ten_quy_trinh: 'Quy trình thử', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
    pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, so_ho_so: 0,
    cap_ky: [{
      id: 10, cap_ky: 1, ten_cap_ky: 'Phê duyệt', bat_buoc: true, loai_ky: 'KY_DUYET',
      nguoi_ky: [{ id: 101, ten_nguoi_ky: 'Nguyễn Văn A', vai_tro_ky: 'KY_CHINH', nguoi_ky: 1, chuc_vu: null, loai_nguoi_ky: 'CAN_BO', chan_ky_chinh: true }],
    }],
  };
  const HO_SO_GIA_LAP = {
    id: 12, document_type: 'vanbandi', van_ban_id: 3, so_hieu_van_ban: '', trich_yeu_van_ban: '',
    van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
    quy_trinh: 1, ma_quy_trinh: 'QT1', ten_quy_trinh: 'Quy trình thử', phien_ban_quy_trinh: 1,
    trang_thai: 'CHO_KY', han_chot: null, ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '',
    ghi_chu: '', ho_so_goc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3,
    ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z', dang_cho: [], luot_trinh: [], lich_su: [],
    trang_thai_luot: 'CHO_KY', qua_han: false,
  } as unknown as HoSoChiTiet;

  it('nút Đặt trang cuối tự động gán vị trí trang cuối và cho phép bỏ khung', async () => {
    boc(<Buoc2 hoSo={HO_SO_GIA_LAP} tep={new ArrayBuffer(8)} quyTrinh={QT_GIA_LAP as unknown as QuyTrinh} />);
    expect(screen.getByText('Chưa đặt vị trí (chỉ hiện trên trang phê duyệt)')).toBeInTheDocument();
    const nutDatTrangCuoi = screen.getByRole('button', { name: /Đặt trang cuối/ });
    expect(nutDatTrangCuoi).toBeInTheDocument();
    fireEvent.click(nutDatTrangCuoi);
    await waitFor(() => expect(screen.getByText('Trang 1')).toBeInTheDocument());
    const nutBoKhung = screen.getByRole('button', { name: /Bỏ khung/ });
    expect(nutBoKhung).toBeInTheDocument();
    fireEvent.click(nutBoKhung);
    await waitFor(() => expect(screen.getByText('Chưa đặt vị trí (chỉ hiện trên trang phê duyệt)')).toBeInTheDocument());
  });
});

describe('KhoaPage', () => {
  it('chưa có khóa: chặn PIN không đạt chính sách và PIN nhập lại không khớp', async () => {
    api.khoa.mockResolvedValue([]);
    boc(<KhoaPage />);
    expect(await screen.findByText('Bạn chưa có khóa ký trên thiết bị này.')).toBeInTheDocument();
    const tao = screen.getByRole('button', { name: /Tạo khóa ký cho thiết bị này/ });
    fireEvent.change(screen.getByLabelText('PIN mới (8 chữ số)'), { target: { value: '12345678' } });
    expect(await screen.findByText(/liên tiếp|tăng|giảm/i)).toBeInTheDocument();
    expect(tao).toBeDisabled();
    fireEvent.change(screen.getByLabelText('PIN mới (8 chữ số)'), { target: { value: '48273916' } });
    fireEvent.change(screen.getByLabelText('Nhập lại PIN'), { target: { value: '48273917' } });
    expect(await screen.findByText('Hai lần nhập PIN không khớp.')).toBeInTheDocument();
    expect(tao).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Nhập lại PIN'), { target: { value: '48273916' } });
    await waitFor(() => expect(tao).toBeEnabled());
  });

  it('khóa đang hoạt động thuộc thiết bị khác: cho nhập file khóa vào thiết bị này', async () => {
    const khoa = { id: 4, ma_khoa: 'TB-3-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
      khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
    api.khoa.mockResolvedValue([khoa]);
    boc(<KhoaPage />);
    expect(await screen.findByText(/thuộc thiết bị khác/)).toBeInTheDocument();
    expect(screen.getByLabelText('Hoặc nhập file khóa đã có vào thiết bị này')).toBeInTheDocument();
  });
});

describe('TraoDoiPanel', () => {
  const THREAD = { id: 1, nguoi_yeu_cau: 9, tieu_de: 'Sai số', ly_do: 'Mục 2', trang_thai: 'DANG_MO' as const,
    created_at: '2026-10-07T01:00:00Z', thoi_diem_giai_quyet: null };
  const DANG_SUA = hoSo({ trang_thai: 'CHO_KY', luot_trinh: [{ ...LUOT, trang_thai: 'YEU_CAU_SUA' }] });

  it('người tạo thấy tin nhắn, gửi tin nhắn và có phần tải bản sửa', async () => {
    api.traoDoi.mockResolvedValue({ thread: THREAD, tin_nhan: [
      { id: 1, nguoi_viet: 9, noi_dung: 'Bổ sung tổng tiền', created_at: '2026-10-07T01:00:00Z' }] });
    api.guiTinNhan.mockResolvedValue({ id: 2, nguoi_viet: 3, noi_dung: 'Đã sửa', created_at: '2026-10-07T02:00:00Z' });
    boc(<TraoDoiPanel hoSo={DANG_SUA} onXong={() => undefined} />);
    expect(await screen.findByText('Bổ sung tổng tiền')).toBeInTheDocument();
    expect(screen.getByLabelText('Chọn tệp PDF đã sửa')).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Nhập nội dung trao đổi…'), { target: { value: 'Đã sửa' } });
    fireEvent.click(screen.getByRole('button', { name: 'Gửi' }));
    await waitFor(() => expect(api.guiTinNhan).toHaveBeenCalledWith(12, 'Đã sửa'));
  });

  it('người ngoài cuộc trao đổi không có ô nhắn và không tải bản sửa', async () => {
    api.traoDoi.mockResolvedValue({ thread: THREAD, tin_nhan: [] });
    boc(<TraoDoiPanel hoSo={DANG_SUA} onXong={() => undefined} />, { ...TOI, id: 50 });
    expect(await screen.findByText('Chưa có tin nhắn.')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Nhập nội dung trao đổi…')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Chọn tệp PDF đã sửa')).not.toBeInTheDocument();
  });
});

describe('KetQuaPanel', () => {
  it('tệp hoàn tất sẵn sàng: có tải tệp và xác minh bằng chứng', () => {
    boc(<KetQuaPanel hoSo={hoSo()} luot={LUOT} onTaiLai={() => undefined} />);
    expect(screen.getByRole('button', { name: /Tải tệp hoàn tất/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xác minh bằng chứng/ })).toBeInTheDocument();
  });

  it('tạo tệp lỗi: hiện mã lỗi và cho tạo lại', async () => {
    const loi = { ...LUOT, trang_thai_tep_hoan_tat: 'LOI' as const, loi_tep_hoan_tat: 'thieu_phong_chu' };
    api.taoLaiTepHoanTat.mockResolvedValue(hoSo());
    const tai_lai = vi.fn();
    boc(<KetQuaPanel hoSo={hoSo({ luot_trinh: [loi] })} luot={loi} onTaiLai={tai_lai} />);
    expect(screen.getByText(/thieu_phong_chu/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tạo lại tệp/ }));
    await waitFor(() => expect(tai_lai).toHaveBeenCalled());
    expect(api.taoLaiTepHoanTat).toHaveBeenCalledWith(12);
  });
});

/** Promise bị từ chối đã gắn sẵn catch rỗng: không thành "unhandled rejection" khi component gắn xử lý muộn. */
function tuChoi(err: Error) {
  const p = Promise.reject(err);
  p.catch(() => undefined);
  return p;
}

describe('XemPdf', () => {
  it('lần vẽ bị hủy (đổi kích thước) không báo lỗi; lỗi vẽ thật thì hiện thông báo', async () => {
    const huy = Object.assign(new Error('huy'), { name: 'RenderingCancelledException' });
    pdf.veTrang.mockImplementationOnce(() => ({ xong: tuChoi(huy), huy: vi.fn() }));
    const { unmount } = boc(<XemPdf duLieu={new ArrayBuffer(8)} />);
    await waitFor(() => expect(pdf.veTrang).toHaveBeenCalled());
    expect(screen.queryByText(/Không hiển thị được tệp PDF/)).not.toBeInTheDocument();
    unmount();
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    pdf.veTrang.mockImplementationOnce(() => ({ xong: tuChoi(new Error('getOrInsertComputed is not a function')), huy: vi.fn() }));
    boc(<XemPdf duLieu={new ArrayBuffer(8)} />);
    expect(await screen.findByText(/Không hiển thị được tệp PDF/)).toBeInTheDocument();
  });

  it('không mở được PDF: hiện thông báo thay vì vùng trắng', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    pdf.moPdf.mockImplementationOnce(() => tuChoi(new Error('hong')));
    boc(<XemPdf duLieu={new ArrayBuffer(8)} />);
    expect(await screen.findByText(/Không hiển thị được tệp PDF/)).toBeInTheDocument();
  });
});
