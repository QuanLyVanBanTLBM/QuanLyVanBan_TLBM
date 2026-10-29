/**
 * Lỗi người kiểm thử chéo có thể bắt (rà soát trước kiểm thử chéo): hộp thoại không giữ tiêu điểm/không đóng bằng
 * bấm nền, đường dẫn hồ sơ sai dạng gọi API, tệp/hạn chót sai vẫn gửi request, Enter không gửi tin nhắn, thu hồi khóa
 * không xác nhận, nhấn đúp thao tác quy trình, cấp ký không xóa được, thông báo "Dữ liệu không hợp lệ" không nêu trường.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HopThoai } from '@components/signing/ChungUI';
import TraoDoiPanel from '@components/signing/TraoDoiPanel';
import { ApiError } from '@lib/apiClient';
import { signingApi } from '@lib/signing/api';
import { hanChotDaQua, kiemTraTepPdf } from '@lib/signing/dinhDang';
import { SigningContext } from '@lib/signing/hooks';
import { dich, useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet, KhoaKy, NguoiDungHienTai, QuyTrinh } from '@lib/signing/types';
import ChiTietPage from './ChiTietPage';
import DanhSachPage from './DanhSachPage';
import KhoaPage from './KhoaPage';
import QuyTrinhPage from './QuyTrinhPage';
import SigningModule from './SigningModule';
import TaiLieuPage from './TaiLieuPage';
import TaoHoSoPage from './TaoHoSoPage';
import ThongBaoPage from './ThongBaoPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    toi: vi.fn(), danhSach: vi.fn(), thongKe: vi.fn(), thongBao: vi.fn(), chiTiet: vi.fn(), tepGoc: vi.fn(), taiLieu: vi.fn(), huy: vi.fn(),
    timVanBanDi: vi.fn(), chiTietVanBanDi: vi.fn(), lienKetVanBanDi: vi.fn(), quyTrinh: vi.fn(), taoNhap: vi.fn(), khoa: vi.fn(), thuHoiKhoa: vi.fn(), traoDoi: vi.fn(),
    guiTinNhan: vi.fn(), giaiQuyet: vi.fn(), thaoTacQuyTrinh: vi.fn(), taoQuyTrinh: vi.fn(), xoaQuyTrinh: vi.fn(),
    donVi: vi.fn(), chucVu: vi.fn(), danhBaCanBo: vi.fn(), canBoTheoChucVu: vi.fn(),
  } };
});
vi.mock('@lib/signing/pdf', () => ({
  moPdf: vi.fn().mockResolvedValue({ numPages: 1 }),
  veTrang: vi.fn(() => ({ xong: Promise.resolve(undefined), huy: vi.fn() })),
  laLoiHuyVe: vi.fn(() => false),
}));
const api = vi.mocked(signingApi);

const TOI: NguoiDungHienTai = {
  id: 3, ten: 'Văn thư', don_vi_id: 1, la_quan_tri: true, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: true, send_trinhky: true, sign_trinhky: true, manage_signing_process: true },
};
const boc = (ui: React.ReactNode, toi: NguoiDungHienTai = TOI) => render(
  <MemoryRouter><SigningContext.Provider value={{ toi, taiLaiToi: () => undefined }}>{ui}</SigningContext.Provider></MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.timVanBanDi.mockResolvedValue([]);
  api.quyTrinh.mockResolvedValue([]);
  api.donVi.mockResolvedValue([]);
  api.chucVu.mockResolvedValue([]);
  api.danhBaCanBo.mockResolvedValue([]);
  api.canBoTheoChucVu.mockResolvedValue({ count: 0, results: [] });
  api.thongKe.mockResolvedValue({ tat_ca: 25, cho_ky: 0, qua_han: 0, hoan_thanh: 0, tra_lai: 0 });
  api.thongBao.mockResolvedValue([]);
});

describe('HopThoai: bàn phím và bấm nền', () => {
  function Mau({ dangXuLy = false }: { dangXuLy?: boolean }) {
    const [mo, setMo] = useState(false);
    return (
      <>
        <button type="button" onClick={() => setMo(true)}>Mở hộp</button>
        <HopThoai moTieuDe="Hộp thử" mo={mo} onDong={() => setMo(false)} dangXuLy={dangXuLy}
          chanDuoi={<button type="button">Đồng ý</button>}>
          <input aria-label="Ô một" />
          <input aria-label="Ô hai" />
        </HopThoai>
      </>
    );
  }

  it('đưa tiêu điểm vào ô nhập đầu tiên, giữ Tab trong hộp và trả tiêu điểm về nút đã mở khi đóng', async () => {
    render(<Mau />);
    const nut = screen.getByRole('button', { name: 'Mở hộp' });
    nut.focus();
    fireEvent.click(nut);
    const hop = await screen.findByRole('dialog', { name: 'Hộp thử' });
    expect(screen.getByLabelText('Ô một')).toHaveFocus();
    // Tab từ phần tử cuối quay về phần tử đầu (nút Đóng), Shift+Tab từ đầu về cuối
    screen.getByRole('button', { name: 'Đồng ý' }).focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(within(hop).getByRole('button', { name: 'Đóng' })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: 'Đồng ý' })).toHaveFocus();
    // Tiêu điểm lạc ra ngoài hộp thì kéo vào lại
    nut.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(hop.contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(nut).toHaveFocus();
  });

  it('bấm nền đóng hộp, bấm trong hộp hoặc kéo chọn chữ ra nền thì không đóng', async () => {
    render(<Mau />);
    fireEvent.click(screen.getByRole('button', { name: 'Mở hộp' }));
    const hop = await screen.findByRole('dialog');
    const nen = hop.parentElement as HTMLElement;
    fireEvent.mouseDown(hop);
    fireEvent.click(hop);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.mouseDown(hop);  // bắt đầu ở trong hộp, thả ở nền
    fireEvent.click(nen);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.mouseDown(nen);
    fireEvent.click(nen);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('đang xử lý thì Esc, bấm nền và nút Đóng không đóng hộp', async () => {
    render(<Mau dangXuLy />);
    fireEvent.click(screen.getByRole('button', { name: 'Mở hộp' }));
    const hop = await screen.findByRole('dialog');
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.mouseDown(hop.parentElement as HTMLElement);
    fireEvent.click(hop.parentElement as HTMLElement);
    expect(screen.getByRole('button', { name: 'Đóng' })).toBeDisabled();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});

describe('Đường dẫn hồ sơ và trang không tồn tại', () => {
  const moChiTiet = (id: string) => render(
    <MemoryRouter initialEntries={[`/approvals/${id}`]}>
      <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
        <Routes><Route path="/approvals/:id" element={<ChiTietPage />} /></Routes>
      </SigningContext.Provider>
    </MemoryRouter>,
  );

  it.each(['abc', '0', '-3', '1.5', '12abc', '99999999999'])('mã hồ sơ "%s" sai dạng: báo không tìm thấy, không gọi API', (ma) => {
    moChiTiet(ma);
    expect(screen.getByText('Không tìm thấy hoặc bạn không được xem hồ sơ này.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Về danh sách hồ sơ/ })).toHaveAttribute('href', '/approvals');
    expect(screen.queryByRole('button', { name: /Thử lại/ })).not.toBeInTheDocument();
    expect(api.chiTiet).not.toHaveBeenCalled();
  });

  it('hồ sơ không tồn tại (404): báo không tìm thấy kèm đường về danh sách, không có nút Thử lại', async () => {
    api.chiTiet.mockRejectedValue(new ApiError(404, { code: 'khong_tim_thay', detail: 'x', fields: {} }));
    moChiTiet('99999');
    expect(await screen.findByText('Không tìm thấy hoặc bạn không được xem hồ sơ này.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Về danh sách hồ sơ/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Thử lại/ })).not.toBeInTheDocument();
  });

  it('đường dẫn con không có trang: hiện "Trang không tồn tại" thay vì vùng trắng', async () => {
    api.toi.mockResolvedValue(TOI);
    render(
      <MemoryRouter initialEntries={['/approvals/tao-moi/abc']}>
        <Routes><Route path="/approvals/*" element={<SigningModule />} /></Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Trang không tồn tại.')).toBeInTheDocument();
  });
});

describe('Kiểm tra tệp và hạn chót phía trình duyệt', () => {
  it('kiemTraTepPdf: rỗng, sai định dạng, quá 20 MB; PDF hợp lệ thì không lỗi', () => {
    expect(kiemTraTepPdf({ name: 'a.pdf', size: 0, type: 'application/pdf' })).toBe('tao.loiTepRong');
    expect(kiemTraTepPdf({ name: 'a.txt', size: 10, type: 'text/plain' })).toBe('tao.loiTepDinhDang');
    expect(kiemTraTepPdf({ name: 'a.pdf', size: 21 * 1024 * 1024, type: 'application/pdf' })).toBe('loi.tep_qua_lon');
    expect(kiemTraTepPdf({ name: 'Báo cáo (bản #1).PDF', size: 10, type: '' })).toBeNull();
    expect(kiemTraTepPdf({ name: 'x', size: 10, type: 'application/pdf' })).toBeNull();
  });

  it('hanChotDaQua: ô trống không lỗi, quá khứ lỗi, tương lai không lỗi', () => {
    expect(hanChotDaQua('')).toBe(false);
    expect(hanChotDaQua('2020-01-01T10:00')).toBe(true);
    expect(hanChotDaQua('2999-01-01T10:00')).toBe(false);
  });

  async function moFormNhapKhac() {
    api.timVanBanDi.mockResolvedValue([]);
    api.quyTrinh.mockResolvedValue([{
      id: 2, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt hai cấp', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
      pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0,
    } as unknown as QuyTrinh]);
    api.taoNhap.mockReturnValue(new Promise(() => undefined));
    boc(<TaoHoSoPage />);
    fireEvent.click(await screen.findByLabelText(/Tải PDF dự thảo/));
    fireEvent.change(await screen.findByLabelText(/Quy trình ký/), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Trích yếu'), { target: { value: 'Tờ trình thử' } });
    return screen.getByRole('button', { name: /Lưu nháp và xem trước/ });
  }
  const chonTep = (ten: string, kichThuoc: number, loai = 'application/pdf') => {
    const tep = new File(['x'], ten, { type: loai });
    Object.defineProperty(tep, 'size', { value: kichThuoc });
    fireEvent.change(screen.getByLabelText(/PDF dự thảo chưa vào sổ/), { target: { files: [tep] } });
  };

  it.each([
    ['rỗng', 'a.pdf', 0, 'application/pdf', 'Tệp rỗng, hãy chọn tệp khác.'],
    ['không phải PDF', 'a.txt', 10, 'text/plain', 'Chỉ nhận tệp PDF (.pdf).'],
    ['quá 20 MB', 'lon.pdf', 21 * 1024 * 1024, 'application/pdf', 'Tệp vượt quá 20 MB.'],
  ])('tệp %s: báo lỗi ngay dưới ô, khóa nút lưu, không gửi request', async (_ten, ten, size, loai, thongBao) => {
    const luu = await moFormNhapKhac();
    chonTep(ten, size, loai);
    expect(await screen.findByText(thongBao)).toBeInTheDocument();
    expect(luu).toBeDisabled();
    fireEvent.click(luu);
    expect(api.taoNhap).not.toHaveBeenCalled();
  });

  it('hạn chót ở quá khứ: báo lỗi, khóa nút lưu; đổi sang tương lai thì lưu được', async () => {
    const luu = await moFormNhapKhac();
    chonTep('a.pdf', 100);
    const o = screen.getByLabelText(/Hạn chót/);
    fireEvent.change(o, { target: { value: '2020-01-01T10:00' } });
    expect(await screen.findByText('Hạn chót phải sau thời điểm hiện tại.')).toBeInTheDocument();
    expect(luu).toBeDisabled();
    fireEvent.change(o, { target: { value: '2999-01-01T10:00' } });
    await waitFor(() => expect(luu).toBeEnabled());
    expect(screen.queryByText('Hạn chót phải sau thời điểm hiện tại.')).not.toBeInTheDocument();
    fireEvent.click(luu);
    await waitFor(() => expect(api.taoNhap).toHaveBeenCalledTimes(1));
  });

  it('tìm văn bản đi: gõ nhiều phím liền nhau chỉ gửi một request sau khi dừng gõ', async () => {
    api.timVanBanDi.mockResolvedValue([]);
    api.quyTrinh.mockResolvedValue([]);
    boc(<TaoHoSoPage />);
    const o = await screen.findByLabelText('Tìm theo số hiệu hoặc trích yếu…');
    await waitFor(() => expect(api.timVanBanDi).toHaveBeenCalledWith(''));
    const truoc = api.timVanBanDi.mock.calls.length;
    for (const v of ['m', 'mu', 'mua', 'mua ']) fireEvent.change(o, { target: { value: v } });
    await waitFor(() => expect(api.timVanBanDi).toHaveBeenLastCalledWith('mua'), { timeout: 2000 });
    expect(api.timVanBanDi.mock.calls.length).toBe(truoc + 1);
  });

  it('trích yếu và ghi chú có giới hạn độ dài khớp máy chủ', async () => {
    await moFormNhapKhac();
    expect(screen.getByLabelText('Trích yếu')).toHaveAttribute('maxlength', '1000');
    expect(screen.getByLabelText(/Ghi chú/)).toHaveAttribute('maxlength', '2000');
  });
});

describe('TraoDoiPanel: Enter và tên người viết', () => {
  const THREAD = { id: 1, nguoi_yeu_cau: 9, tieu_de: 'Sai số', ly_do: 'Mục 2', trang_thai: 'DANG_MO' as const,
    created_at: '2026-10-07T01:00:00Z', thoi_diem_giai_quyet: null };
  const HO_SO = {
    id: 12, trang_thai: 'CHO_KY', create_by: 3, luot_trinh: [{ id: 5, trang_thai: 'YEU_CAU_SUA' }],
  } as unknown as HoSoChiTiet;

  it('hiện tên người viết (bản thân là "Bạn") và gửi tin nhắn bằng Enter', async () => {
    api.traoDoi.mockResolvedValue({ thread: THREAD, tin_nhan: [
      { id: 1, nguoi_viet: 9, ten_nguoi_viet: 'Trưởng phòng Ban CNTT', noi_dung: 'Bổ sung tổng tiền', created_at: '2026-10-07T01:00:00Z' },
      { id: 2, nguoi_viet: 3, ten_nguoi_viet: 'Văn thư', noi_dung: 'Đã nhận', created_at: '2026-10-07T02:00:00Z' }] });
    api.guiTinNhan.mockResolvedValue({ id: 3, nguoi_viet: 3, noi_dung: 'Đã sửa', created_at: '2026-10-07T03:00:00Z' });
    boc(<TraoDoiPanel hoSo={HO_SO} onXong={() => undefined} />);
    expect(await screen.findByText('Trưởng phòng Ban CNTT')).toBeInTheDocument();
    expect(screen.getByText('Bạn')).toBeInTheDocument();
    expect(screen.queryByText('Văn thư')).not.toBeInTheDocument();
    const o = screen.getByPlaceholderText('Nhập nội dung trao đổi…');
    expect(o).toHaveAttribute('maxlength', '2000');
    fireEvent.change(o, { target: { value: '  Đã sửa  ' } });
    fireEvent.submit(o.closest('form') as HTMLFormElement);  // Enter trong ô nhập gửi biểu mẫu
    await waitFor(() => expect(api.guiTinNhan).toHaveBeenCalledWith(12, 'Đã sửa'));
    await waitFor(() => expect(o).toHaveValue(''));
  });

  it('nội dung chỉ có khoảng trắng: không gửi', async () => {
    api.traoDoi.mockResolvedValue({ thread: THREAD, tin_nhan: [] });
    boc(<TraoDoiPanel hoSo={HO_SO} onXong={() => undefined} />);
    const o = await screen.findByPlaceholderText('Nhập nội dung trao đổi…');
    fireEvent.change(o, { target: { value: '    ' } });
    expect(screen.getByRole('button', { name: 'Gửi' })).toBeDisabled();
    fireEvent.submit(o.closest('form') as HTMLFormElement);
    expect(api.guiTinNhan).not.toHaveBeenCalled();
  });
});

describe('KhoaPage: thu hồi khóa cần xác nhận', () => {
  it('bấm Thu hồi chỉ mở hộp xác nhận; thu hồi khi bấm Thu hồi trong hộp', async () => {
    const khoa = { id: 4, ma_khoa: 'TB-3-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
      khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
    api.khoa.mockResolvedValue([khoa]);
    api.thuHoiKhoa.mockResolvedValue(khoa);
    boc(<KhoaPage />);
    fireEvent.change(await screen.findByLabelText('Lý do thu hồi'), { target: { value: 'Mất thiết bị' } });
    fireEvent.click(screen.getByRole('button', { name: 'Thu hồi khóa' }));
    const hop = await screen.findByRole('dialog', { name: 'Thu hồi khóa' });
    expect(within(hop).getByText(/Thu hồi khóa ký đang hoạt động|Thu hồi khóa ký “TB-3-1”/)).toBeInTheDocument();
    expect(api.thuHoiKhoa).not.toHaveBeenCalled();
    fireEvent.click(within(hop).getByRole('button', { name: 'Thu hồi khóa' }));
    await waitFor(() => expect(api.thuHoiKhoa).toHaveBeenCalledWith(4, 'Mất thiết bị'));
  });

  it('Hủy bỏ trong hộp xác nhận thì không thu hồi', async () => {
    const khoa = { id: 4, ma_khoa: 'TB-3-1', dau_van_tay: 'f'.repeat(64), thuat_toan: 'Ed25519',
      khoa_cong_khai: 'pub', trang_thai: 'HOAT_DONG' } as KhoaKy;
    api.khoa.mockResolvedValue([khoa]);
    boc(<KhoaPage />);
    fireEvent.change(await screen.findByLabelText('Lý do thu hồi'), { target: { value: 'Mất thiết bị' } });
    fireEvent.click(screen.getByRole('button', { name: 'Thu hồi khóa' }));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Hủy bỏ' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(api.thuHoiKhoa).not.toHaveBeenCalled();
  });
});

describe('Vào thẳng đường dẫn khi thiếu quyền', () => {
  const CHUYEN_VIEN: NguoiDungHienTai = { ...TOI, id: 9, la_quan_tri: false,
    quyen: { view_trinhky: true, add_trinhky: false, send_trinhky: true, sign_trinhky: false } };

  it('Khóa ký & PIN: không có quyền ký thì báo ngay, không hiện ô nhập PIN', async () => {
    api.khoa.mockResolvedValue([]);
    boc(<KhoaPage />, CHUYEN_VIEN);
    expect(await screen.findByText(/chưa được cấp quyền ký nên không cần khóa ký/)).toBeInTheDocument();
    expect(screen.queryByLabelText('PIN mới (8 chữ số)')).not.toBeInTheDocument();
  });

  it('Tạo hồ sơ: không có quyền tạo thì báo ngay, không hiện form', async () => {
    api.timVanBanDi.mockResolvedValue([]);
    boc(<TaoHoSoPage />, CHUYEN_VIEN);
    expect(await screen.findByText('Tài khoản của bạn chưa được cấp quyền tạo hồ sơ trình ký.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Lưu nháp và xem trước/ })).not.toBeInTheDocument();
  });
});

describe('QuyTrinhPage: thao tác an toàn', () => {
  const QT = (sua: Partial<QuyTrinh> = {}) => ({
    id: 1, ma_quy_trinh: 'QT1', ten_quy_trinh: 'Duyệt hai cấp', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
    pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0, ...sua,
  } as unknown as QuyTrinh);

  it('nhấn đúp "Tạo phiên bản mới" chỉ gửi một yêu cầu', async () => {
    api.quyTrinh.mockResolvedValue([QT()]);
    let xong: () => void = () => undefined;
    api.thaoTacQuyTrinh.mockReturnValue(new Promise((r) => { xong = () => r(QT({ id: 2, phien_ban: 2 })); }));
    boc(<QuyTrinhPage />);
    const nut = await screen.findByRole('button', { name: 'Tạo phiên bản mới' });
    fireEvent.click(nut);
    fireEvent.click(nut);
    expect(api.thaoTacQuyTrinh).toHaveBeenCalledTimes(1);
    expect(nut).toBeDisabled();
    xong();
    await waitFor(() => expect(nut).toBeEnabled());
  });

  it('"Ngừng" cần xác nhận trước khi gửi', async () => {
    api.quyTrinh.mockResolvedValue([QT()]);
    api.thaoTacQuyTrinh.mockResolvedValue(QT({ trang_thai: 'NGUNG' }));
    boc(<QuyTrinhPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Ngừng' }));
    const hop = await screen.findByRole('dialog', { name: 'Ngừng' });
    expect(api.thaoTacQuyTrinh).not.toHaveBeenCalled();
    expect(within(hop).getByText(/Ngừng quy trình “Duyệt hai cấp” \(phiên bản 1\)/)).toBeInTheDocument();
    fireEvent.click(within(hop).getByRole('button', { name: 'Xác nhận' }));
    await waitFor(() => expect(api.thaoTacQuyTrinh).toHaveBeenCalledWith(1, 'ngung'));
  });

  it('form tạo: mã sai định dạng khóa nút Lưu, số giờ quá một năm báo lỗi, cấp ký xóa được khi có từ hai cấp', async () => {
    api.quyTrinh.mockResolvedValue([]);
    boc(<QuyTrinhPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Tạo quy trình' }));
    const hop = await screen.findByRole('dialog', { name: 'Tạo quy trình' });
    const ma = within(hop).getByLabelText(/Mã tra cứu|Mã quy trình/);
    fireEvent.change(ma, { target: { value: 'QT #1 <b>' } });
    expect(within(hop).getByText(/chỉ gồm chữ không dấu/)).toBeInTheDocument();
    expect(within(hop).getByRole('button', { name: 'Lưu' })).toBeDisabled();
    fireEvent.change(ma, { target: { value: 'QT_PB.2026-01' } });
    expect(within(hop).queryByText(/chỉ gồm chữ không dấu/)).not.toBeInTheDocument();
    expect(within(hop).getByLabelText(/Tên quy trình/)).toHaveAttribute('maxlength', '255');
    const gio = within(hop).getByLabelText('Số giờ xử lý (tùy chọn) 1');
    fireEvent.change(gio, { target: { value: '9000' } });
    expect(within(hop).getByText('Số giờ xử lý tối đa 8760 (một năm).')).toBeInTheDocument();
    fireEvent.change(gio, { target: { value: '24' } });
    expect(within(hop).queryByText(/Số giờ xử lý tối đa/)).not.toBeInTheDocument();
    expect(within(hop).queryByRole('button', { name: /Xóa cấp ký/ })).not.toBeInTheDocument();
    fireEvent.click(within(hop).getByRole('button', { name: /Thêm cấp/ }));
    expect(within(hop).getAllByRole('button', { name: /Xóa cấp ký/ })).toHaveLength(2);
    fireEvent.click(within(hop).getByRole('button', { name: 'Xóa cấp ký 2' }));
    expect(within(hop).queryByRole('button', { name: /Xóa cấp ký/ })).not.toBeInTheDocument();
  });
});

describe('Hạn chót, ghi chú và tìm kiếm tự áp dụng', () => {
  it('hồ sơ không đặt hạn chót vẫn hiện hạn xử lý của cấp đang ký', async () => {
    api.danhSach.mockResolvedValue({ count: 1, next: null, previous: null, results: [{
      id: 21, van_ban_id: null, van_ban: { so_hieu: '203/BC', trich_yeu: 'Báo cáo' }, ten_quy_trinh: 'QT', trang_thai: 'CHO_KY',
      dang_cho: [], ten_nguoi_tao: 'A', han_chot: null, han_xu_ly_cap: '2026-10-24T06:39:00Z',
    } as never] });
    boc(<DanhSachPage hop="tat_ca" />);
    expect((await screen.findAllByRole('link', { name: /203\/BC/ })).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Hạn bước ký:/)).length).toBeGreaterThan(0);
  });

  it('số trên thẻ lọc nhanh tính theo cùng từ khóa với danh sách (không theo thẻ đang chọn)', async () => {
    api.danhSach.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    boc(<DanhSachPage hop="tat_ca" />);
    await screen.findByRole('searchbox');
    expect(api.thongKe).toHaveBeenLastCalledWith('tat_ca', { q: undefined, quy_trinh: undefined, tu_ngay: undefined, den_ngay: undefined });
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'mua sam' } });
    await waitFor(() => expect(api.thongKe).toHaveBeenLastCalledWith('tat_ca', { q: 'mua sam', quy_trinh: undefined, tu_ngay: undefined, den_ngay: undefined }));
    const soLan = api.thongKe.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: /Quá hạn/ }));
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('tat_ca', { q: 'mua sam', nhanh: 'qua_han' }, 1));
    expect(api.thongKe).toHaveBeenCalledTimes(soLan);
  });

  it('hồ sơ có hạn chót: không thêm dòng hạn cấp', async () => {
    api.danhSach.mockResolvedValue({ count: 1, next: null, previous: null, results: [{
      id: 22, van_ban_id: null, van_ban: { so_hieu: '204/BC', trich_yeu: 'Báo cáo' }, ten_quy_trinh: 'QT', trang_thai: 'CHO_KY',
      dang_cho: [], ten_nguoi_tao: 'A', han_chot: '2026-10-27T12:00:00Z', han_xu_ly_cap: '2026-10-24T06:39:00Z',
    } as never] });
    boc(<DanhSachPage hop="tat_ca" />);
    await screen.findAllByText('204/BC — Báo cáo');
    expect(screen.queryByText(/Hạn bước ký:/)).not.toBeInTheDocument();
  });

  it('chi tiết hồ sơ hiện ghi chú của người trình', async () => {
    api.chiTiet.mockResolvedValue({
      id: 5, document_type: null, van_ban_id: null, so_hieu_van_ban: '', trich_yeu_van_ban: 'Tờ trình', van_ban: { so_hieu: '', trich_yeu: 'Tờ trình' },
      quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt', phien_ban_quy_trinh: 1, trang_thai: 'NHAP', han_chot: null,
      ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '', ghi_chu: 'Gấp, trình trước thứ Sáu', ho_so_goc: null,
      phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 99, ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z',
      dang_cho: [], luot_trinh: [], lich_su: [], trang_thai_luot: null, qua_han: false,
    } as unknown as HoSoChiTiet);
    api.tepGoc.mockRejectedValue(new ApiError(404, { code: 'khong_doc_duoc_tep', detail: 'x', fields: {} }));
    render(
      <MemoryRouter initialEntries={['/approvals/5']}>
        <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
          <Routes><Route path="/approvals/:id" element={<ChiTietPage />} /></Routes>
        </SigningContext.Provider>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Gấp, trình trước thứ Sáu')).toBeInTheDocument();
  });

  it('hồ sơ PDF dự thảo đã ký xong dẫn tới đăng ký văn bản đi rồi mới cho liên kết', async () => {
    const hoSo = {
      id: 51, document_type: null, van_ban_id: null, so_hieu_van_ban: '05/TTr', trich_yeu_van_ban: 'Kế hoạch thử',
      van_ban: { so_hieu: '05/TTr', trich_yeu: 'Kế hoạch thử' }, quy_trinh: 1, ma_quy_trinh: 'QT',
      ten_quy_trinh: 'Duyệt', phien_ban_quy_trinh: 1, trang_thai: 'HOAN_THANH', han_chot: null,
      ngay_gui: null, ngay_hoan_thanh: '2026-10-28T01:00:00Z', ly_do_tu_choi: '', ly_do_huy: '', ghi_chu: '',
      ho_so_goc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3,
      ten_nguoi_tao: 'Văn thư', created_at: '2026-10-28T01:00:00Z', dang_cho: [], trang_thai_luot: 'HOAN_THANH',
      qua_han: false, luot_trinh: [{
        id: 52, so_luot: 1, luot_truoc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64),
        trang_thai: 'HOAN_THANH', ly_do: '', thoi_diem_gui: '2026-10-28T01:00:00Z',
        thoi_diem_hoan_thanh: '2026-10-28T02:00:00Z', thoi_diem_tu_choi: null, thoi_diem_huy: null,
        trang_thai_tep_hoan_tat: 'THANH_CONG', loi_tep_hoan_tat: '', ma_bam_tep_hoan_tat: 'b'.repeat(64),
        ma_bam_bang_chung: null, cap_ky: [], yeu_cau_sua: [],
      }], lich_su: [],
    } as unknown as HoSoChiTiet;
    api.chiTiet.mockResolvedValue(hoSo);
    api.tepGoc.mockRejectedValue(new ApiError(404, { code: 'khong_doc_duoc_tep', detail: 'x', fields: {} }));
    api.timVanBanDi.mockResolvedValue([{ id: 71, so_hieu: '06/TTr', trich_yeu: 'Kế hoạch đã ký' }]);
    api.lienKetVanBanDi.mockResolvedValue({ ...hoSo, document_type: 'vanbandi', van_ban_id: 71 } as HoSoChiTiet);
    render(
      <MemoryRouter initialEntries={['/approvals/51']}>
        <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
          <Routes><Route path="/approvals/:id" element={<ChiTietPage />} /></Routes>
        </SigningContext.Provider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole('link', { name: /Mở Văn bản đi để đăng ký văn bản đã ký/ }))
      .toHaveAttribute('href', '/documents/outgoing');
    fireEvent.change(await screen.findByLabelText(/Chọn văn bản đi đã đăng ký/), { target: { value: '71' } });
    fireEvent.click(screen.getByRole('button', { name: 'Liên kết văn bản đi' }));
    const hop = await screen.findByRole('dialog', { name: 'Liên kết văn bản đi' });
    expect(within(hop).getByText(/06\/TTr — Kế hoạch đã ký/)).toBeInTheDocument();
    fireEvent.click(within(hop).getByRole('button', { name: 'Xác nhận' }));
    await waitFor(() => expect(api.lienKetVanBanDi).toHaveBeenCalledWith(51, 71));
  });

  it('sau khi hủy hồ sơ: số ở thanh tab được tải lại ngay (không chờ đổi trang)', async () => {
    const nhap = {
      id: 5, document_type: null, van_ban_id: null, so_hieu_van_ban: '', trich_yeu_van_ban: 'Tờ trình', van_ban: { so_hieu: '', trich_yeu: 'Tờ trình' },
      quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt', phien_ban_quy_trinh: 1, trang_thai: 'NHAP', han_chot: null,
      ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '', ghi_chu: '', ho_so_goc: null,
      phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3, ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z',
      dang_cho: [], luot_trinh: [], lich_su: [], trang_thai_luot: null, qua_han: false,
    } as unknown as HoSoChiTiet;
    api.chiTiet.mockResolvedValue(nhap);
    api.tepGoc.mockRejectedValue(new ApiError(404, { code: 'khong_doc_duoc_tep', detail: 'x', fields: {} }));
    api.huy.mockResolvedValue({ ...nhap, trang_thai: 'HUY' });
    const lamMoiDem = vi.fn();
    render(
      <MemoryRouter initialEntries={['/approvals/5']}>
        <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined, lamMoiDem }}>
          <Routes><Route path="/approvals/:id" element={<ChiTietPage />} /></Routes>
        </SigningContext.Provider>
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Hủy hồ sơ' }));
    const hop = await screen.findByRole('dialog', { name: 'Hủy hồ sơ' });
    fireEvent.click(within(hop).getByRole('button', { name: 'Hủy hồ sơ' }));
    await waitFor(() => expect(api.huy).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(lamMoiDem).toHaveBeenCalledTimes(1));
  });

  it('trang Tệp hồ sơ: gõ từ khóa tự áp dụng sau một nhịp, không cần bấm Lọc; xóa chữ thì bỏ lọc', async () => {
    api.taiLieu.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    boc(<TaiLieuPage />);
    const o = await screen.findByRole('searchbox');
    fireEvent.change(o, { target: { value: '  mua sam ' } });
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({ q: 'mua sam' }, 1), { timeout: 2000 });
    fireEvent.change(o, { target: { value: '' } });
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({ q: '' }, 1), { timeout: 2000 });
  });
});

describe('Danh sách, thông báo, lỗi dữ liệu', () => {
  it('trang đang xem không còn (404): tự về trang 1 thay vì báo lỗi', async () => {
    api.danhSach.mockImplementation(async (_hop, _loc, tr) => {
      if (tr === 2) throw new ApiError(404, { code: 'khong_tim_thay', detail: 'x', fields: {} });
      return { count: 25, next: null, previous: null, results: [] };
    });
    api.danhSach.mockResolvedValueOnce({ count: 25, next: null, previous: null, results: [{
      id: 1, van_ban_id: null, van_ban: { so_hieu: '1/TTr', trich_yeu: 'Một' }, ten_quy_trinh: 'QT', trang_thai: 'CHO_KY',
      dang_cho: [], ten_nguoi_tao: 'A', han_chot: null,
    } as never] });
    boc(<DanhSachPage hop="tat_ca" />);
    fireEvent.click(await screen.findByRole('button', { name: /Sau/ }));
    await waitFor(() => expect(api.danhSach.mock.calls.map((c) => c[2])).toEqual([1, 2, 1]));
    expect(screen.queryByText(/Không tìm thấy/)).not.toBeInTheDocument();
  });

  it('thông báo đủ 50 mục: ghi rõ chỉ hiển thị 50 thông báo gần nhất', async () => {
    const tb = Array.from({ length: 50 }, (_, i) => ({
      id: i + 1, loai_thong_bao: 'CAN_KY', trinh_ky: i + 1, van_ban: `VB ${i + 1}`, trang_thai_ho_so: 'CHO_KY',
      ten_quy_trinh: 'QT', created_at: '2026-10-07T01:00:00Z', kenh_in_app: true, email_da_gui: false,
      email_trang_thai: null, email_nguoi_nhan: null, nguoi_thao_tac: null, ly_do: null, han_xu_ly: null,
    }));
    api.thongBao.mockResolvedValue(tb as never);
    boc(<ThongBaoPage />);
    expect(await screen.findByText('Hiển thị 50 thông báo gần nhất.')).toBeInTheDocument();
  });

  it('thông báo ít hơn 50 mục: không hiện ghi chú giới hạn', async () => {
    api.thongBao.mockResolvedValue([]);
    boc(<ThongBaoPage />);
    expect(await screen.findByText('Chưa có thông báo nào.')).toBeInTheDocument();
    expect(screen.queryByText(/thông báo gần nhất/)).not.toBeInTheDocument();
  });
});

function HienLoi({ err }: { err: unknown }) {
  const { loi } = useSigningT();
  return <p>{loi(err)}</p>;
}

describe('i18n lỗi dữ liệu không hợp lệ', () => {
  it('"Dữ liệu không hợp lệ" nêu trường và lý do đầu tiên (kể cả trường lồng nhau)', () => {
    const loi = (fields: unknown) => new ApiError(400, { code: 'du_lieu_khong_hop_le', detail: 'Dữ liệu không hợp lệ.', fields });
    const { rerender } = render(<HienLoi err={loi({ tep: ['Tệp rỗng.'] })} />);
    expect(screen.getByText('Tệp: Tệp rỗng.')).toBeInTheDocument();
    rerender(<HienLoi err={loi({ cap_ky: { 0: { so_gio_xu_ly: ['Tối đa 8760.'] } } })} />);
    expect(screen.getByText('Tối đa 8760.')).toBeInTheDocument();
    rerender(<HienLoi err={loi({ khong_ro: ['Giá trị không hợp lệ.'] })} />);
    expect(screen.getByText('Giá trị không hợp lệ.')).toBeInTheDocument();
    rerender(<HienLoi err={loi({})} />);
    expect(screen.getByText('Dữ liệu không hợp lệ.')).toBeInTheDocument();
  });

  it('đủ khóa vi/en cho nhãn trường và thông báo mới', () => {
    for (const lang of ['vi', 'en'] as const) {
      for (const khoa of ['chung.trangKhongTonTai', 'chung.veDanhSach', 'tao.loiTepRong', 'tao.loiHanChot',
        'khoa.xacNhanThuHoi', 'traoDoi.ban', 'thongBao.toiDa', 'quyTrinh.xoaCap', 'quyTrinh.loiMa', 'truong.tep',
        'loi.du_lieu_khong_hop_le', 'loi.quy_trinh_trung_ma', 'loi.nguoi_ky_trung_trong_cap']) {
        expect(dich(lang, khoa, { so: 1, ma: 'x', ten: 'x', phienBan: 1 }), `${lang}:${khoa}`).not.toBe(khoa);
      }
    }
    expect(dich('en', 'chung.trangKhongTonTai')).toBe('Page not found.');
  });
});
