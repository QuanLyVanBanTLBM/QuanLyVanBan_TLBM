/**
 * Giao diện Trình ký (#80 mục E): tab theo quyền, danh sách (rỗng/lỗi/thử lại), hành động theo quyền và trạng thái,
 * hộp thoại ký hiển thị mã băm và chặn ký khi tệp đang xem khác mã băm đã khóa; quy trình chọn đơn vị từ danh sách;
 * bộ lọc danh sách, thông báo, xem chi tiết/xóa quy trình nháp, danh sách tệp của hồ sơ.
 */
if (typeof globalThis.ResizeObserver === 'undefined') {
  class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
}
if (typeof globalThis.DOMMatrix === 'undefined') {
  class MockDOMMatrix {
    a = 1; b = 0; c = 0; d = 1; e = 0; f = 0;
    is2D = true; isIdentity = true;
  }
  globalThis.DOMMatrix = MockDOMMatrix as unknown as typeof DOMMatrix;
}

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import CauHinhUyQuyen from '@components/signing/CauHinhUyQuyen';
import TaiLieuPanel from '@components/signing/TaiLieuPanel';
import TienTrinh from '@components/signing/TienTrinh';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, LuotTrinh, NguoiKyLuot, NguoiDungHienTai, QuyTrinh } from '@lib/signing/types';
import DanhSachPage from './DanhSachPage';
import QuyTrinhPage from './QuyTrinhPage';
import SigningModule from './SigningModule';
import TaiLieuPage from './TaiLieuPage';
import ThongBaoPage from './ThongBaoPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    toi: vi.fn(), danhSach: vi.fn(), thongKe: vi.fn(), taiLieu: vi.fn(), quyTrinh: vi.fn(), donVi: vi.fn(), thongBao: vi.fn(), chiTietQuyTrinh: vi.fn(),
    xoaQuyTrinh: vi.fn(), taoQuyTrinh: vi.fn(), suaQuyTrinh: vi.fn(), chucVu: vi.fn(), danhBaCanBo: vi.fn(), canBoTheoChucVu: vi.fn(), tepCuaLuot: vi.fn(), tepGoc: vi.fn(), tepHoanTat: vi.fn(), bangChung: vi.fn(),
    uyQuyen: vi.fn(), timNguoiNhanUyQuyen: vi.fn(), thaoTacQuyTrinh: vi.fn(),
    cauHinhUyQuyen: vi.fn(), chucVuUyQuyen: vi.fn(), luuCauHinhUyQuyen: vi.fn(),
  } };
});
// pdfjs-dist cần DOMMatrix/canvas của trình duyệt; jsdom không có, nên chỉ thay lớp vẽ PDF.
vi.mock('@lib/signing/pdf', () => ({
  moPdf: vi.fn().mockResolvedValue({ numPages: 1, getPage: vi.fn().mockResolvedValue({ getViewport: () => ({ width: 600, height: 800 }), render: () => ({ promise: Promise.resolve() }) }) }),
  veTrang: vi.fn(() => ({ xong: Promise.resolve(undefined), huy: vi.fn() })),
  laLoiHuyVe: vi.fn(() => false),
}));
const api = vi.mocked(signingApi);

const TOI: NguoiDungHienTai = {
  id: 7, ten: 'Trưởng phòng', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
};

function hoSo(sua: Partial<HoSoChiTiet> = {}): HoSoChiTiet {
  return {
    id: 12, document_type: 'vanbandi', van_ban_id: 3, so_hieu_van_ban: '', trich_yeu_van_ban: '',
    van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
    quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt mua sắm', phien_ban_quy_trinh: 1,
    trang_thai: 'CHO_KY', han_chot: null, ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '',
    ghi_chu: '', ho_so_goc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3,
    ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z', dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Trưởng phòng', vai_tro_ky: 'KY_CHINH' }],
    luot_trinh: [{
      id: 5, so_luot: 1, luot_truoc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), trang_thai: 'CHO_KY',
      ly_do: '', thoi_diem_gui: null, thoi_diem_hoan_thanh: null, trang_thai_tep_hoan_tat: null, loi_tep_hoan_tat: '',
      ma_bam_tep_hoan_tat: '', ma_bam_bang_chung: null, cap_ky: [], yeu_cau_sua: [],
    }],
    lich_su: [], trang_thai_luot: 'CHO_KY', qua_han: false,
    ...sua,
  };
}

/** Một trang danh sách hồ sơ (phân trang DRF). */
function trang<T>(results: T[], count = results.length) {
  return { count, next: null, previous: null, results };
}

// Gắn dưới route cha như ứng dụng thật (/approvals/*) để route con `:id` không khớp nhầm "/approvals".
const moModule = (duong_dan = '/approvals') => render(
  <MemoryRouter initialEntries={[duong_dan]}>
    <Routes><Route path="/approvals/*" element={<SigningModule />} /></Routes>
  </MemoryRouter>,
);

const boc = (ui: React.ReactNode, toi: NguoiDungHienTai = TOI) => render(
  <MemoryRouter><SigningContext.Provider value={{ toi, taiLaiToi: () => undefined }}>{ui}</SigningContext.Provider></MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  api.quyTrinh.mockResolvedValue([]);
  api.thongBao.mockResolvedValue(trang([]));
  api.chucVu.mockResolvedValue([]);
  api.danhBaCanBo.mockResolvedValue([]);
  api.canBoTheoChucVu.mockResolvedValue({ count: 0, results: [] });
  api.thongKe.mockResolvedValue({ tat_ca: 3, cho_ky: 1, qua_han: 1, hoan_thanh: 0, tra_lai: 1 });
  localStorage.setItem('tlbm_lang', 'vi');
});

describe('SigningModule', () => {
  it('chỉ hiện tab theo quyền (không có quyền tạo thì không có tab tạo hồ sơ)', async () => {
    api.toi.mockResolvedValue(TOI);
    api.danhSach.mockResolvedValue(trang([]));
    moModule();
    expect(await screen.findByRole('link', { name: /Cần tôi ký duyệt/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Khóa ký & PIN/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Tạo hồ sơ trình ký/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Ký số & Phê duyệt điện tử/)).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Trình ký' })).toBeInTheDocument();
  });

  it('tab "Cần tôi ký duyệt" hiện số hồ sơ đang chờ (gồm cả quá hạn); tab phụ nằm trong nhóm riêng', async () => {
    api.toi.mockResolvedValue(TOI);
    api.danhSach.mockResolvedValue(trang([]));
    moModule();
    const tabKy = await screen.findByRole('link', { name: /Cần tôi ký duyệt/ });
    await waitFor(() => expect(tabKy).toHaveTextContent('2'));
    expect(api.thongKe).toHaveBeenCalledWith('can_toi_ky');
    const nav = within(screen.getByRole('navigation'));
    for (const ten of [/Hồ sơ tôi trình/, /Hồ sơ được xem/, /Thông báo/, /Khóa ký & PIN/]) {
      expect(nav.getByRole('link', { name: ten })).toBeInTheDocument();
    }
    expect(nav.queryByRole('link', { name: /^Quy trình/ })).toBeInTheDocument();
  });

  it('có quyền tạo thì có nút riêng "Tạo hồ sơ trình ký" ở đầu trang, không nằm trong tab', async () => {
    api.toi.mockResolvedValue({ ...TOI, quyen: { ...TOI.quyen, add_trinhky: true } });
    api.danhSach.mockResolvedValue(trang([]));
    moModule();
    expect(await screen.findByRole('button', { name: /Tạo hồ sơ trình ký/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Tạo hồ sơ trình ký/ })).not.toBeInTheDocument();
  });
});

describe('DanhSachPage', () => {
  it('hiện trạng thái rỗng', async () => {
    api.danhSach.mockResolvedValue(trang([]));
    boc(<DanhSachPage hop="can_toi_ky" />);
    expect(await screen.findByText('Không có hồ sơ nào đang chờ bạn ký duyệt.')).toBeInTheDocument();
    expect(api.danhSach).toHaveBeenCalledWith('can_toi_ky', {}, 1);
  });

  it('hiện dòng hồ sơ với văn bản, mức độ, trạng thái, người đang chờ', async () => {
    api.danhSach.mockResolvedValue(trang([hoSo()]));
    boc(<DanhSachPage hop="toi_gui" />);
    const bang = within(await screen.findByRole('table'));
    expect(bang.getByRole('link', { name: /15\/TTr — Mua sắm/ })).toHaveAttribute('href', '/approvals/12');
    expect(bang.getByText(/#12 · Duyệt mua sắm/)).toBeInTheDocument();
    expect(bang.queryByRole('columnheader', { name: /Tác vụ/ })).not.toBeInTheDocument();
    expect(bang.getByText('Đang chờ ký')).toBeInTheDocument();
    expect(bang.getByText('Trưởng phòng')).toBeInTheDocument();
  });

  it('bộ lọc: từ khóa tự áp dụng, Lọc thêm thu gọn mặc định, mức độ áp dụng ngay, xóa lọc trả về rỗng', async () => {
    api.danhSach.mockResolvedValue(trang([]));
    boc(<DanhSachPage hop="toi_gui" />);
    await screen.findByText('Bạn chưa gửi trình hồ sơ nào.');
    expect(screen.queryByRole('button', { name: /^Lọc$/ })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Từ ngày')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Xóa lọc/ })).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: '15/TTr' } });
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { q: '15/TTr' }, 1));
    fireEvent.click(screen.getByRole('button', { name: /Lọc thêm/ }));
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2026-10-01' } });
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { q: '15/TTr', tu_ngay: '2026-10-01' }, 1));
    expect(screen.getByRole('button', { name: /Lọc thêm \(1\)/ })).toBeInTheDocument();
    expect(await screen.findByText('Không có hồ sơ nào khớp bộ lọc.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Xóa lọc/ }));
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', {}, 1));
    expect(screen.getByRole('searchbox')).toHaveValue('');
  });

  it('hộp rỗng và chưa lọc: không hiện khối lọc, chỉ hiện trạng thái rỗng; thống kê gọi một lần', async () => {
    api.thongKe.mockResolvedValue({ tat_ca: 0, cho_ky: 0, qua_han: 0, hoan_thanh: 0, tra_lai: 0 });
    api.danhSach.mockResolvedValue(trang([]));
    boc(<DanhSachPage hop="tat_ca" />);
    expect(await screen.findByText(/(Chưa có hồ sơ nào bạn được xem\.|Chưa có văn bản nào bạn được xem\.)/)).toBeInTheDocument();
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Lọc nhanh' })).not.toBeInTheDocument();
    expect(api.thongKe).toHaveBeenCalledTimes(1);
  });

  it('bộ lọc trạng thái chỉ có Tất cả + 4 trạng thái, hiện số lượng (kể cả 0), bấm thẻ là lọc', async () => {
    api.danhSach.mockResolvedValue(trang([]));
    boc(<DanhSachPage hop="toi_gui" />);
    const quaHan = await screen.findByRole('button', { name: /Quá hạn/ });
    expect(quaHan).toHaveTextContent('1');
    const nhom = within(screen.getByRole('group', { name: 'Lọc nhanh' }));
    expect(nhom.getAllByRole('button').map((b) => b.textContent?.replace(/\d+$/, ''))).toEqual(
      ['Tất cả', 'Đang chờ ký', 'Quá hạn', 'Đã ký xong', 'Trả lại để sửa']);
    expect(nhom.getByRole('button', { name: /Đã ký xong/ })).toHaveTextContent('0');
    for (const bo of [/Nháp/, /Không đồng ý/, /Đã hủy/]) expect(nhom.queryByRole('button', { name: bo })).not.toBeInTheDocument();
    fireEvent.click(quaHan);
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { nhanh: 'qua_han' }, 1));
    expect(screen.getByRole('button', { name: /Quá hạn/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('phân trang: hiện tổng số, sang trang sau gọi trang 2; đổi bộ lọc về trang 1', async () => {
    api.danhSach.mockResolvedValue(trang([hoSo()], 23));
    boc(<DanhSachPage hop="toi_gui" />);
    const thanh = await screen.findByRole('navigation', { name: 'Phân trang' });
    expect(within(thanh).getByText('Hiển thị 1–10 trên 23 hồ sơ')).toBeInTheDocument();
    expect(within(thanh).getByText('Trang 1/3')).toBeInTheDocument();
    expect(within(thanh).getByRole('button', { name: /Trước/ })).toBeDisabled();
    fireEvent.click(within(thanh).getByRole('button', { name: /Sau/ }));
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', {}, 2));
    expect(await screen.findByText('Trang 2/3')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Quá hạn/ }));
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { nhanh: 'qua_han' }, 1));
  });

  it('một trang thì không hiện thanh phân trang', async () => {
    api.danhSach.mockResolvedValue(trang([hoSo()]));
    boc(<DanhSachPage hop="toi_gui" />);
    await screen.findByRole('table');
    expect(screen.queryByRole('navigation', { name: 'Phân trang' })).not.toBeInTheDocument();
  });

  it('lỗi tải có nút thử lại', async () => {
    api.danhSach.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(trang([]));
    boc(<DanhSachPage hop="tat_ca" />);
    fireEvent.click(await screen.findByRole('button', { name: /Thử lại/ }));
    expect(await screen.findByText(/(Chưa có hồ sơ nào bạn được xem\.|Chưa có văn bản nào bạn được xem\.)/)).toBeInTheDocument();
  });
});

describe('HanhDong', () => {
  it('người ký đang được mở thấy Ký duyệt / Trả lại để sửa / Không đồng ý; không thấy Hủy', () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'a'.repeat(64)} onXong={() => undefined} />);
    expect(screen.getByRole('button', { name: /Ký duyệt/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trả lại để sửa/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Từ chối hồ sơ/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Hủy hồ sơ/ })).not.toBeInTheDocument();
  });

  it('người ngoài luồng không thấy hành động ký; người tạo thấy Hủy', () => {
    const nguoiTao = { ...TOI, id: 3 };
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={null} onXong={() => undefined} />, nguoiTao);
    expect(screen.queryByRole('button', { name: /Ký duyệt/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hủy hồ sơ/ })).toBeInTheDocument();
  });

  it('hộp thoại ký chặn ký khi tệp đang xem khác mã băm đã khóa', async () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'b'.repeat(64)} onXong={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
    const hop = await screen.findByRole('dialog');
    expect(hop).toHaveTextContent('Tệp đã thay đổi so với lượt trình');
    fireEvent.change(screen.getByLabelText(/Nhập PIN ký/), { target: { value: '48273916' } });
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Ký duyệt/ }).at(-1)).toBeDisabled());
  });

  it('hộp thoại không đồng ý hiển thị cảnh báo từ chối vĩnh viễn và cho phép chuyển sang trả lại để sửa', async () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'a'.repeat(64)} onXong={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /Từ chối hồ sơ/ }));
    const hop = await screen.findByRole('dialog');
    expect(hop).toHaveTextContent(/Từ chối sẽ kết thúc hồ sơ/);
    const nutChuyen = screen.getByRole('button', { name: /Chuyển sang/ });
    expect(nutChuyen).toBeInTheDocument();
    fireEvent.click(nutChuyen);
    expect(screen.getByRole('dialog')).toHaveTextContent(/Trả lại để sửa/);
  });
});

function nguoiKy(sua: Partial<NguoiKyLuot>): NguoiKyLuot {
  return {
    id: 21, nguoi_ky: 9, ten_nguoi_ky: 'Giám đốc', ten_chuc_vu: null, vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true,
    trang_thai: 'CHO_KY', thoi_diem_mo: '2026-10-07T01:00:00Z', ngay_ky: null, ngay_tu_choi: null, ly_do_tu_choi: '',
    uy_quyen_tu: null, ten_nguoi_uy_quyen: null, ly_do_uy_quyen: '', ngay_uy_quyen: null, trang_ky: null,
    toa_do_x: null, toa_do_y: null, chieu_rong_khung: null, chieu_cao_khung: null, chu_ky: null, ...sua,
  };
}

function luotCo(nguoi: NguoiKyLuot[]): LuotTrinh {
  return {
    ...hoSo().luot_trinh[0],
    cap_ky: [{ id: 2, cap_ky: 1, ten_cap_ky: 'Duyệt', thu_tu: 1, trang_thai: 'DANG_KY', han_xu_ly: null,
      thoi_diem_mo: null, thoi_diem_hoan_thanh: null, nguoi_ky: nguoi }],
  };
}

describe('Danh sách: trạng thái trả lại, quá hạn', () => {
  it('hồ sơ chỉ hiển thị duy nhất một trạng thái: trả sửa hiện "Đang trả lại để sửa", quá hạn hiện "Quá hạn"', async () => {
    api.danhSach.mockResolvedValue(trang([
      hoSo({ id: 1, trang_thai_luot: 'YEU_CAU_SUA', qua_han: false }),
      hoSo({ id: 2, trang_thai_luot: 'CHO_KY', qua_han: true }),
    ]));
    boc(<DanhSachPage hop="tat_ca" />);
    expect((await screen.findAllByText('Chờ người trình sửa')).length).toBe(2);
    expect(screen.getAllByText('Quá hạn').length).toBe(3);
  });
});

describe('Ủy quyền ký', () => {
  const QUAN_TRI: NguoiDungHienTai = { ...TOI, id: 1, quyen: { ...TOI.quyen, delegate_trinhky: true } };

  it('cấu hình chức danh, tìm theo tên và lưu các chức danh được ký thay', async () => {
    api.chucVuUyQuyen.mockResolvedValue([{ id: 1, ten: 'Trưởng phòng', stt: 1 }, { id: 2, ten: 'Phó phòng', stt: 2 }]);
    api.danhBaCanBo.mockResolvedValue([{ id: 5, username: 'pho', ho_ten: 'Nguyễn An', don_vi_id: 1, don_vi_ten: 'Kế toán', chuc_vu_id: 2, chuc_vu_ten: 'Phó phòng' }]);
    api.cauHinhUyQuyen.mockResolvedValue([]);
    api.luuCauHinhUyQuyen.mockResolvedValue({});
    boc(<CauHinhUyQuyen onDong={() => undefined} />);
    fireEvent.click(await screen.findByRole('button', { name: /Chọn/ }));
    fireEvent.click(screen.getByRole('button', { name: /Trưởng phòng/ }));
    fireEvent.change(screen.getByPlaceholderText('Tìm theo chức danh hoặc tên người'), { target: { value: 'Nguyễn An' } });
    expect(screen.getByText('Nguyễn An · Kế toán')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Lưu' }));
    await waitFor(() => expect(api.luuCauHinhUyQuyen).toHaveBeenCalledWith(1, [2]));
  });

  it('không có delegate_trinhky thì không thấy nút ủy quyền', () => {
    const luot = luotCo([nguoiKy({})]);
    boc(<HanhDong hoSo={hoSo({ luot_trinh: [luot] })} luot={luot} maBamTepDangXem={null} onXong={() => undefined} />,
      { ...TOI, id: 1 });
    expect(screen.queryByRole('button', { name: /Ủy quyền ký/ })).not.toBeInTheDocument();
  });

  it('chọn người ký, tìm người nhận, nhập lý do rồi gửi đúng payload kèm Idempotency-Key', async () => {
    const luot = luotCo([nguoiKy({ co_the_uy_quyen: true }), nguoiKy({ id: 22, nguoi_ky: 10, ten_nguoi_ky: 'Đã ký', trang_thai: 'DA_KY' })]);
    const ho_so = hoSo({ luot_trinh: [luot] });
    api.timNguoiNhanUyQuyen.mockResolvedValue([
      { id: 15, ten: 'Phó giám đốc', ten_dang_nhap: 'pgd', chuc_vu: 'Phó giám đốc', don_vi_id: 1, don_vi: 'Ban TGĐ' },
    ]);
    api.uyQuyen.mockResolvedValue(ho_so);
    const xong = vi.fn();
    boc(<HanhDong hoSo={ho_so} luot={luot} maBamTepDangXem={null} onXong={xong} />, QUAN_TRI);
    fireEvent.click(screen.getByRole('button', { name: /Ủy quyền ký/ }));
    const chonNguoiKy = await screen.findByRole('combobox', { name: /Người cần được ký thay/ });
    expect(within(chonNguoiKy).queryByRole('option', { name: /Đã ký/ })).not.toBeInTheDocument();
    fireEvent.change(chonNguoiKy, { target: { value: '21' } });
    const chonNhan = screen.getByRole('group', { name: /Người nhận ủy quyền/ });
    const nguoiNhan = await within(chonNhan).findByRole('button', { name: /Phó giám đốc/ });
    fireEvent.click(nguoiNhan);
    expect(api.timNguoiNhanUyQuyen).toHaveBeenCalledWith('', 12, 21);
    fireEvent.change(screen.getByLabelText(/Lý do ủy quyền/), { target: { value: 'Đi công tác' } });
    fireEvent.click(screen.getAllByRole('button', { name: /Ủy quyền ký/ }).at(-1)!);
    await waitFor(() => expect(api.uyQuyen).toHaveBeenCalledWith(12, expect.any(String),
      { dong_nguoi_ky: 21, nguoi_nhan: 15, ly_do_uy_quyen: 'Đi công tác' }));
    await waitFor(() => expect(xong).toHaveBeenCalledWith(ho_so));
  });

  it('từ khóa để trống mà vẫn rỗng thì báo chưa có ai đủ điều kiện, không phải lỗi từ khóa', async () => {
    const luot = luotCo([nguoiKy({ co_the_uy_quyen: true })]);
    const ho_so = hoSo({ luot_trinh: [luot] });
    api.timNguoiNhanUyQuyen.mockResolvedValue([]);
    boc(<HanhDong hoSo={ho_so} luot={luot} maBamTepDangXem={null} onXong={() => undefined} />, QUAN_TRI);
    fireEvent.click(screen.getByRole('button', { name: /Ủy quyền ký/ }));
    fireEvent.change(await screen.findByRole('combobox', { name: /Người cần được ký thay/ }), { target: { value: '21' } });
    expect(await screen.findByText(/Chưa có ai đủ điều kiện nhận ủy quyền/)).toBeInTheDocument();
  });

  it('gõ từ khóa mà vẫn rỗng thì báo không khớp từ khóa', async () => {
    const luot = luotCo([nguoiKy({ co_the_uy_quyen: true })]);
    const ho_so = hoSo({ luot_trinh: [luot] });
    api.timNguoiNhanUyQuyen.mockResolvedValue([]);
    boc(<HanhDong hoSo={ho_so} luot={luot} maBamTepDangXem={null} onXong={() => undefined} />, QUAN_TRI);
    fireEvent.click(screen.getByRole('button', { name: /Ủy quyền ký/ }));
    fireEvent.change(await screen.findByRole('combobox', { name: /Người cần được ký thay/ }), { target: { value: '21' } });
    fireEvent.change(screen.getByPlaceholderText('Tìm theo tên, chức danh, đơn vị…'), { target: { value: 'nguoi_ngoai' } });
    expect(await screen.findByText(/Không khớp từ khóa/)).toBeInTheDocument();
  });

  it('chỉ cho chọn người ký mà backend xác nhận người hiện tại được ủy quyền', async () => {
    const truongPhong = {
      ...TOI, id: 4, la_lanh_dao_don_vi: true,
      quyen: { ...TOI.quyen, delegate_trinhky: true },
    };
    const luot = luotCo([
      nguoiKy({ id: 31, nguoi_ky: 5, ten_nguoi_ky: 'Giám đốc', co_the_uy_quyen: false }),
      nguoiKy({ id: 32, nguoi_ky: 10, ten_nguoi_ky: 'Chuyên viên cùng đơn vị', co_the_uy_quyen: true }),
    ]);
    boc(<HanhDong hoSo={hoSo({ luot_trinh: [luot] })} luot={luot} maBamTepDangXem={null} onXong={() => undefined} />,
      truongPhong);
    fireEvent.click(screen.getByRole('button', { name: /Ủy quyền ký/ }));
    const chonNguoiKy = await screen.findByRole('combobox', { name: /Người cần được ký thay/ });
    expect(within(chonNguoiKy).queryByRole('option', { name: /Giám đốc/ })).not.toBeInTheDocument();
    expect(within(chonNguoiKy).getByRole('option', { name: /Chuyên viên cùng đơn vị/ })).toBeInTheDocument();
  });

  it('tiến trình hiện người ký thay', () => {
    boc(<TienTrinh luot={luotCo([nguoiKy({ ten_nguoi_ky: 'Phó giám đốc', ten_nguoi_uy_quyen: 'Giám đốc' })])} />);
    expect(screen.getByText('Ký thay Giám đốc')).toBeInTheDocument();
  });
});

describe('Ký bằng file khóa', () => {
  it('hộp thoại ký có ô tải file khóa và báo lỗi khi file sai định dạng', async () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'a'.repeat(64)} onXong={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
    const o = await screen.findByLabelText(/File khóa ký/);
    fireEvent.change(o, { target: { files: [new File(['khong phai json'], 'sai.tlbmkey')] } });
    expect(await screen.findByText('File khóa không đúng định dạng.')).toBeInTheDocument();
  });
});

describe('QuyTrinhPage', () => {
  const TP: NguoiDungHienTai = { ...TOI, don_vi_id: 4, la_lanh_dao_don_vi: true, quyen: { ...TOI.quyen, manage_signing_process: true } };
  const QT: QuyTrinh = {
    id: 1, ma_quy_trinh: 'QT-KH', ten_quy_trinh: 'Duyệt kế hoạch', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
    pham_vi: 'PHONG_BAN', don_vi_ap_dung_id: 4, ten_don_vi_ap_dung: 'Phòng Kế hoạch', cap_ky: [], so_ho_so: 3,
  };

  it('hiện tên đơn vị áp dụng và chọn đơn vị từ danh sách khi tạo quy trình phòng ban', async () => {
    api.quyTrinh.mockResolvedValue([QT]);
    api.donVi.mockResolvedValue([{ id: 4, ten: 'Phòng Kế hoạch' }]);
    boc(<QuyTrinhPage />, TP);
    expect(await screen.findByText(/Phòng ban · Phòng Kế hoạch/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tạo quy trình/ }));
    const chon = await screen.findByRole('combobox', { name: /Đơn vị áp dụng/ });
    await waitFor(() => expect(within(chon).getByRole('option', { name: 'Phòng Kế hoạch' })).toBeInTheDocument());
    expect((chon as HTMLSelectElement).value).toBe('4');
    expect(api.donVi).toHaveBeenCalledTimes(1);
  });

  it('form tạo quy trình: ô tên cấp ký có nhãn "Tên cấp ký 1", chọn từ danh mục chức danh', async () => {
    api.quyTrinh.mockResolvedValue([QT]);
    api.donVi.mockResolvedValue([{ id: 4, ten: 'Phòng Kế hoạch' }]);
    api.chucVu.mockResolvedValue([{ id: 5, name: 'Trưởng phòng', display_order: 1 }]);
    boc(<QuyTrinhPage />, TP);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    const o = await screen.findByRole('combobox', { name: /Tên cấp ký 1/ });
    expect(o).toBeInTheDocument();
    await waitFor(() => expect(within(o).getByRole('option', { name: 'Trưởng phòng' })).toBeInTheDocument());
  });

  it('quy trình cũ phải bỏ người ký nháy trước khi lưu, vẫn giữ người ký chính', async () => {
    const nhap: QuyTrinh = {
      ...QT, id: 2, trang_thai: 'NHAP', so_ho_so: 0, cap_ky: [{
        id: 9, cap_ky: 1, ten_cap_ky: 'Duyệt', thu_tu: 1, don_vi_id: null, so_gio_xu_ly: null,
        nguoi_ky: [
          { id: 3, nguoi_ky: 7, ten_nguoi_ky: 'Người nháy', chuc_vu_id: null, ten_chuc_vu: null,
            pham_vi_chuc_vu: null, vai_tro_ky: 'KY_NHAY', chan_ky_chinh: true, thu_tu: 1 },
          { id: 4, nguoi_ky: 8, ten_nguoi_ky: 'Người ký chính', chuc_vu_id: null, ten_chuc_vu: null,
            pham_vi_chuc_vu: null, vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true, thu_tu: 2 },
        ],
      }],
    };
    api.quyTrinh.mockResolvedValue([nhap]);
    api.donVi.mockResolvedValue([{ id: 4, ten: 'Phòng Kế hoạch' }]);
    api.suaQuyTrinh.mockResolvedValue(nhap);
    boc(<QuyTrinhPage />, TP);
    fireEvent.click(await screen.findByRole('button', { name: 'Sửa quy trình' }));
    const hop = await screen.findByRole('dialog', { name: 'Sửa quy trình' });
    expect(within(hop).getByText(/Quy trình này còn cấu hình ký cũ/)).toBeInTheDocument();
    expect(within(hop).getByRole('button', { name: /Lưu/ })).toBeDisabled();
    expect(within(hop).queryByRole('combobox', { name: /Vai trò ký/ })).not.toBeInTheDocument();
    fireEvent.click(within(hop).getAllByRole('button', { name: 'Bỏ người ký' })[0]);
    expect(within(hop).getByRole('button', { name: /Lưu/ })).toBeEnabled();
    fireEvent.click(within(hop).getByRole('button', { name: /Lưu/ }));
    await waitFor(() => expect(api.suaQuyTrinh).toHaveBeenCalledTimes(1));
    expect(api.suaQuyTrinh.mock.calls[0][1]).toMatchObject({
      cap_ky: [{ nguoi_ky: [{ nguoi_ky: 8, vai_tro_ky: 'KY_CHINH' }] }],
    });
  });

  it('xem chi tiết quy trình; chỉ nháp có Sửa; chưa có hồ sơ thì Xóa được (phải xác nhận), có hồ sơ thì Xóa bị khóa', async () => {
    const nhap: QuyTrinh = {
      ...QT, id: 2, trang_thai: 'NHAP', ten_quy_trinh: 'Quy trình nháp', cap_ky: [{
        id: 9, cap_ky: 1, ten_cap_ky: 'Trưởng phòng', thu_tu: 1, don_vi_id: null, so_gio_xu_ly: 24, nguoi_ky: [{
          id: 3, nguoi_ky: 7, ten_nguoi_ky: 'Trần Trưởng', chuc_vu_id: null, ten_chuc_vu: null, pham_vi_chuc_vu: null,
          vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true, thu_tu: 1,
        }],
      }],
      so_ho_so: 0,
    };
    api.quyTrinh.mockResolvedValue([QT, nhap]);
    api.chiTietQuyTrinh.mockResolvedValue(nhap);
    api.xoaQuyTrinh.mockResolvedValue({});
    boc(<QuyTrinhPage />, TP);
    await screen.findByText('Quy trình nháp');
    expect(screen.getAllByRole('button', { name: /Sửa quy trình/ })).toHaveLength(1);  // chỉ quy trình nháp
    fireEvent.click(screen.getAllByRole('button', { name: /Xem chi tiết/ })[1]);
    expect(await screen.findByText('Chi tiết quy trình')).toBeInTheDocument();
    expect(await screen.findByText('Trần Trưởng')).toBeInTheDocument();
    expect(api.chiTietQuyTrinh).toHaveBeenCalledWith(2);
    fireEvent.click(screen.getAllByRole('button', { name: /Đóng/ })[0]);
    const [xoaDangDung, xoaNhap] = screen.getAllByRole('button', { name: /Xóa quy trình/ });
    expect(xoaDangDung).toBeDisabled();  // quy trình đang có 3 hồ sơ dùng
    expect(xoaDangDung).toHaveAttribute('title', expect.stringContaining('3 hồ sơ'));
    expect(screen.getByText(/Đang có 3 hồ sơ trình ký dùng phiên bản này/)).toBeInTheDocument();
    fireEvent.click(xoaNhap);
    expect(screen.getByText(/Xóa quy trình “Quy trình nháp” \(phiên bản 1\)/)).toBeInTheDocument();
    expect(api.xoaQuyTrinh).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Xác nhận/ }));
    await waitFor(() => expect(api.xoaQuyTrinh).toHaveBeenCalledWith(2));
  });

  it('nhân bản quy trình hoạt động tự động mở ngay form chỉnh sửa phiên bản mới', async () => {
    const qtHoatDong: QuyTrinh = { ...QT, id: 1, phien_ban: 1, trang_thai: 'HOAT_DONG' };
    const qtMoi: QuyTrinh = { ...QT, id: 99, phien_ban: 2, trang_thai: 'NHAP' };
    api.quyTrinh.mockResolvedValue([qtHoatDong]);
    api.thaoTacQuyTrinh.mockResolvedValue(qtMoi);
    boc(<QuyTrinhPage />, TP);
    await screen.findByText('Duyệt kế hoạch');
    const nutNhanBan = screen.getByRole('button', { name: /Tạo phiên bản mới/ });
    fireEvent.click(nutNhanBan);
    await waitFor(() => expect(api.thaoTacQuyTrinh).toHaveBeenCalledWith(1, 'nhan-ban'));
    expect(await screen.findByRole('dialog', { name: /Sửa quy trình/ })).toBeInTheDocument();
  });

  it('modal chi tiết có nút hành động: nháp có nút Sửa, hoạt động có nút Tạo phiên bản mới', async () => {
    const qtHoatDong: QuyTrinh = { ...QT, id: 1, phien_ban: 1, trang_thai: 'HOAT_DONG' };
    api.quyTrinh.mockResolvedValue([qtHoatDong]);
    api.chiTietQuyTrinh.mockResolvedValue(qtHoatDong);
    api.thaoTacQuyTrinh.mockResolvedValue({ ...qtHoatDong, id: 2, phien_ban: 2, trang_thai: 'NHAP' });
    boc(<QuyTrinhPage />, TP);
    await screen.findByText('Duyệt kế hoạch');
    fireEvent.click(screen.getByRole('button', { name: /Xem chi tiết/ }));
    const hop = await screen.findByRole('dialog', { name: /Chi tiết quy trình/ });
    const nutNhanBan = within(hop).getByRole('button', { name: /Tạo phiên bản mới/ });
    expect(nutNhanBan).toBeInTheDocument();
    fireEvent.click(nutNhanBan);
    await waitFor(() => expect(api.thaoTacQuyTrinh).toHaveBeenCalledWith(1, 'nhan-ban'));
  });
});

describe('QuyTrinhPage bộ lọc', () => {
  it('lọc quy trình theo từ khóa, trạng thái và phạm vi', async () => {
    const mau = (id: number, ten: string, trang_thai: 'NHAP' | 'HOAT_DONG', pham_vi: 'CONG_TY' | 'PHONG_BAN'): QuyTrinh => ({
      id, ma_quy_trinh: `QT-${id}`, ten_quy_trinh: ten, mo_ta: '', phien_ban: 1, trang_thai, pham_vi,
      don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0,
    });
    api.quyTrinh.mockResolvedValue([mau(1, 'Duyệt tờ trình', 'HOAT_DONG', 'CONG_TY'), mau(2, 'Duyệt hợp đồng', 'NHAP', 'PHONG_BAN')]);
    boc(<QuyTrinhPage />);
    await screen.findByText('Duyệt tờ trình');
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'hợp đồng' } });
    expect(screen.queryByText('Duyệt tờ trình')).not.toBeInTheDocument();
    expect(screen.getByText('Duyệt hợp đồng')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Trạng thái' }), { target: { value: 'HOAT_DONG' } });
    expect(screen.getByText('Không có quy trình nào khớp bộ lọc.')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Trạng thái' }), { target: { value: '' } });
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'DUYET TO TRINH' } });  // không dấu
    expect(screen.getByText('Duyệt tờ trình')).toBeInTheDocument();
    expect(screen.queryByText('Duyệt hợp đồng')).not.toBeInTheDocument();
  });
});

describe('ThongBaoPage', () => {
  it('hiện thông báo của tôi với loại, văn bản và liên kết tới hồ sơ', async () => {
    api.thongBao.mockResolvedValue(trang([{
      id: 1, loai_thong_bao: 'CAN_KY', trinh_ky: 12, van_ban: '15/TTr — Mua sắm', trang_thai_ho_so: 'CHO_KY',
      ten_quy_trinh: 'Duyệt mua sắm', created_at: '2026-10-07T01:00:00Z',
    }]));
    boc(<ThongBaoPage />);
    const lienKet = await screen.findByRole('link', { name: /Cần ký duyệt/ });
    expect(lienKet).toHaveAttribute('href', '/approvals/12');
    expect(within(lienKet).getByText(/#12 · 15\/TTr — Mua sắm/)).toBeInTheDocument();
  });

  it('loại thông báo mới (ủy quyền, tin nhắn, nhắc hạn) có nhãn riêng; mở trang thì đánh dấu đã xem', async () => {
    localStorage.removeItem('tlbm_signing_thong_bao_xem_luc:7');
    api.thongBao.mockResolvedValue(trang(['UY_QUYEN', 'TIN_NHAN', 'QUA_HAN'].map((loai, i) => ({
      id: i + 1, loai_thong_bao: loai as 'UY_QUYEN', trinh_ky: 12, van_ban: '15/TTr', trang_thai_ho_so: 'CHO_KY' as const,
      ten_quy_trinh: 'Duyệt', created_at: '2026-10-07T01:00:00Z',
    }))));
    boc(<ThongBaoPage />);
    const ds = within(await screen.findByRole('list'));
    expect(ds.getByText('Ủy quyền ký')).toBeInTheDocument();
    expect(ds.getByText('Tin nhắn trao đổi')).toBeInTheDocument();
    expect(ds.getByText('Quá hạn ký')).toBeInTheDocument();
    await waitFor(() => expect(Number(localStorage.getItem('tlbm_signing_thong_bao_xem_luc:7'))).toBeGreaterThan(0));
  });

  it('tab Thông báo hiện số thông báo mới kể từ lần xem trước', async () => {
    localStorage.setItem('tlbm_signing_thong_bao_xem_luc:7', String(Date.parse('2026-10-07T00:00:00Z')));
    api.toi.mockResolvedValue(TOI);
    api.danhSach.mockResolvedValue(trang([]));
    api.thongBao.mockResolvedValue(trang([
      { id: 1, loai_thong_bao: 'CAN_KY', trinh_ky: 12, van_ban: 'a', trang_thai_ho_so: 'CHO_KY', ten_quy_trinh: 'Q', created_at: '2026-10-07T01:00:00Z' },
      { id: 2, loai_thong_bao: 'HUY', trinh_ky: 13, van_ban: 'b', trang_thai_ho_so: 'HUY', ten_quy_trinh: 'Q', created_at: '2026-10-06T01:00:00Z' },
    ]));
    moModule();
    const tab = await screen.findByRole('link', { name: /Thông báo/ });
    await waitFor(() => expect(tab).toHaveTextContent('Thông báo1'));
  });

  it('thông báo cần ký hiện hạn xử lý theo định dạng ngày Việt Nam', async () => {
    api.thongBao.mockResolvedValue(trang([{
      id: 1, loai_thong_bao: 'CAN_KY', trinh_ky: 12, van_ban: '15/TTr', trang_thai_ho_so: 'CHO_KY',
      ten_quy_trinh: 'Duyệt', created_at: '2026-10-07T01:00:00Z', han_xu_ly: '2026-10-08T03:30:00Z',
    }]));
    boc(<ThongBaoPage />);
    const han = new Date('2026-10-08T03:30:00Z').toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
    expect(await screen.findByText(han)).toBeInTheDocument();
    expect(screen.getByText(/Hạn xử lý/)).toBeInTheDocument();
  });

  it('Từ ngày lớn hơn Đến ngày: báo lỗi tại form, không gửi request; sửa lại hợp lệ thì lọc', async () => {
    api.danhSach.mockResolvedValue(trang([]));
    boc(<DanhSachPage hop="toi_gui" />);
    await screen.findByText('Bạn chưa gửi trình hồ sơ nào.');
    fireEvent.click(screen.getByRole('button', { name: /Lọc thêm/ }));
    fireEvent.change(screen.getByLabelText('Đến ngày'), { target: { value: '2026-10-01' } });
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { den_ngay: '2026-10-01' }, 1));
    const soLan = api.danhSach.mock.calls.length;
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2026-10-10' } });
    const loi = await screen.findByRole('alert');
    expect(loi).toHaveTextContent('Từ ngày không được lớn hơn Đến ngày');
    expect(screen.getByLabelText('Từ ngày')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Đến ngày')).toHaveAttribute('aria-describedby', loi.id);
    expect(screen.getByLabelText('Từ ngày')).toHaveValue('2026-10-10');
    expect(api.danhSach).toHaveBeenCalledTimes(soLan);
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2026-09-30' } });
    await waitFor(() => expect(api.danhSach).toHaveBeenLastCalledWith('toi_gui', { tu_ngay: '2026-09-30', den_ngay: '2026-10-01' }, 1));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Từ ngày')).not.toHaveAttribute('aria-invalid');
  });

  it('chưa có thông báo', async () => {
    api.thongBao.mockResolvedValue(trang([]));
    boc(<ThongBaoPage />);
    expect(await screen.findByText('Chưa có thông báo nào.')).toBeInTheDocument();
  });

  it('thông báo mới hơn lần xem trước được tô đậm; thông báo cũ thì không, dù huy hiệu ở tab đã về 0', async () => {
    localStorage.setItem('tlbm_signing_thong_bao_xem_luc:7', String(Date.parse('2026-10-07T00:30:00Z')));
    api.thongBao.mockResolvedValue(trang([
      { id: 1, loai_thong_bao: 'CAN_KY', trinh_ky: 12, van_ban: 'Mới', trang_thai_ho_so: 'CHO_KY', ten_quy_trinh: 'Q', created_at: '2026-10-07T01:00:00Z' },
      { id: 2, loai_thong_bao: 'HUY', trinh_ky: 13, van_ban: 'Cũ', trang_thai_ho_so: 'HUY', ten_quy_trinh: 'Q', created_at: '2026-10-06T01:00:00Z' },
    ]));
    boc(<ThongBaoPage />);
    const ds = within(await screen.findByRole('list'));
    const moi = ds.getByText('Cần ký duyệt');
    const cu = ds.getByText('Hồ sơ đã hủy');
    expect(moi.closest('div')).toHaveClass('font-bold');
    expect(cu.closest('div')).not.toHaveClass('font-bold');
    // Mốc trên trình duyệt cập nhật ngay (huy hiệu ở tab về 0) nhưng mốc dùng để tô đậm không đổi khi đang xem trang này
    await waitFor(() => expect(Number(localStorage.getItem('tlbm_signing_thong_bao_xem_luc:7')))
      .toBeGreaterThan(Date.parse('2026-10-07T01:00:00Z')));
    expect(moi.closest('div')).toHaveClass('font-bold');
  });

  it('ô tìm kiếm gọi lại API sau khi gõ xong (debounce)', async () => {
    api.thongBao.mockResolvedValue(trang([]));
    boc(<ThongBaoPage />);
    await screen.findByText('Chưa có thông báo nào.');
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'mua sam' } });
    await waitFor(() => expect(api.thongBao).toHaveBeenLastCalledWith({ q: 'mua sam' }, 1));
  });

  it('chọn loại thông báo gọi lại API với loai_thong_bao, về trang 1', async () => {
    api.thongBao.mockResolvedValue(trang([]));
    boc(<ThongBaoPage />);
    await screen.findByText('Chưa có thông báo nào.');
    fireEvent.change(screen.getByRole('combobox', { name: 'Loại thông báo' }), { target: { value: 'QUA_HAN' } });
    await waitFor(() => expect(api.thongBao).toHaveBeenLastCalledWith({ loai_thong_bao: 'QUA_HAN' }, 1));
    expect(screen.getByRole('button', { name: /Xóa lọc/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Xóa lọc/ }));
    await waitFor(() => expect(api.thongBao).toHaveBeenLastCalledWith({}, 1));
  });
});

describe('TaiLieuPage', () => {
  it('liệt kê tệp mọi hồ sơ, lọc theo loại và tải đúng lượt', async () => {
    api.taiLieu.mockResolvedValue(trang([{
      trinh_ky: 12, trang_thai_ho_so: 'CHO_KY', ten_quy_trinh: 'Duyệt mua sắm', van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
      loai: 'LUOT', luot: 5, so_luot: 1, phien_ban: '1', ma_bam: 'a'.repeat(64), thoi_diem: '2026-10-07T01:00:00Z',
      ten_tep: 'trinh-ky-12-luot-1.pdf',
    }]));
    api.tepCuaLuot.mockResolvedValue(new Blob(['%PDF-']));
    URL.createObjectURL = vi.fn(() => 'blob:tep');
    URL.revokeObjectURL = vi.fn();
    boc(<TaiLieuPage />);
    // Trang render cả thẻ (màn hẹp) lẫn bảng (md trở lên) nên mỗi phần tử xuất hiện hai lần
    expect((await screen.findAllByText(/PDF trình ký · lượt 1|trinh-ky-12-luot-1\.pdf/)).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('link', { name: /#12/ })[0]).toHaveAttribute('href', '/approvals/12');
    fireEvent.change(screen.getByRole('combobox', { name: /Loại tệp/ }), { target: { value: 'HOAN_TAT' } });
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({ loai: 'HOAN_TAT' }, 1));
    fireEvent.click(screen.getAllByText(/PDF trình ký · lượt 1|trinh-ky-12-luot-1\.pdf/)[0]);
    await waitFor(() => expect(api.tepCuaLuot).toHaveBeenCalledWith(12, 5));
  });
});

describe('TaiLieuPage khoảng ngày và tải trong hộp xem', () => {
  const tep = { trinh_ky: 12, trang_thai_ho_so: 'CHO_KY' as const, ten_quy_trinh: 'Duyệt', van_ban: { so_hieu: '15/TTr' },
    loai: 'LUOT' as const, luot: 5, so_luot: 1, phien_ban: '1', ma_bam: 'a'.repeat(64), thoi_diem: '2026-10-07T01:00:00Z',
    ten_tep: 'trinh-ky-12-luot-1.pdf' };

  it('Từ ngày lớn hơn Đến ngày: báo lỗi, không gửi request', async () => {
    api.taiLieu.mockResolvedValue(trang([tep]));
    boc(<TaiLieuPage />);
    await screen.findAllByText(/PDF trình ký · lượt 1|trinh-ky-12-luot-1\.pdf/);
    fireEvent.change(screen.getByLabelText('Đến ngày'), { target: { value: '2026-10-01' } });
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({ den_ngay: '2026-10-01' }, 1));
    const soLan = api.taiLieu.mock.calls.length;
    fireEvent.change(screen.getByLabelText('Từ ngày'), { target: { value: '2026-10-10' } });
    expect(await screen.findByRole('alert')).toHaveTextContent('Từ ngày không được lớn hơn Đến ngày');
    expect(api.taiLieu).toHaveBeenCalledTimes(soLan);
    fireEvent.click(screen.getByRole('button', { name: /Xóa lọc/ }));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByLabelText('Từ ngày')).toHaveValue('');
  });

  it('hộp xem PDF có nút Tải xuống: tải đúng tệp, đúng tên; lỗi thì báo trong hộp', async () => {
    api.taiLieu.mockResolvedValue(trang([tep]));
    api.tepCuaLuot.mockResolvedValue(new Blob(['%PDF-']));
    URL.createObjectURL = vi.fn(() => 'blob:tep');
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    boc(<TaiLieuPage />);
    fireEvent.click((await screen.findAllByText(/PDF trình ký · lượt 1|trinh-ky-12-luot-1\.pdf/))[0]);
    const hop = within(await screen.findByRole('dialog'));
    await waitFor(() => expect(api.tepCuaLuot).toHaveBeenCalledTimes(1));
    fireEvent.click(hop.getByRole('button', { name: 'Tải xuống' }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(api.tepCuaLuot).toHaveBeenLastCalledWith(12, 5);
    expect(URL.createObjectURL).toHaveBeenCalled();
    api.tepCuaLuot.mockRejectedValueOnce(new Error('Mất kết nối'));
    fireEvent.click(hop.getByRole('button', { name: 'Tải xuống' }));
    expect(await hop.findByRole('alert')).toBeInTheDocument();
    expect(click).toHaveBeenCalledTimes(1);
    click.mockRestore();
  });
});

describe('TaiLieuPage phân trang', () => {
  it('nhiều tệp thì phân trang như danh sách hồ sơ; sang trang 2, đổi bộ lọc về trang 1', async () => {
    const tep = { trinh_ky: 12, trang_thai_ho_so: 'CHO_KY' as const, ten_quy_trinh: 'Duyệt', van_ban: { so_hieu: '15/TTr' },
      loai: 'LUOT' as const, luot: 5, so_luot: 1, phien_ban: '1', ma_bam: 'a'.repeat(64), thoi_diem: '2026-10-07T01:00:00Z',
      ten_tep: 'trinh-ky-12-luot-1.pdf' };
    api.taiLieu.mockResolvedValue(trang([tep], 25));
    boc(<TaiLieuPage />);
    const thanh = await screen.findByRole('navigation', { name: 'Phân trang' });
    expect(within(thanh).getByText('Hiển thị 1–10 trên 25 tệp')).toBeInTheDocument();
    expect(within(thanh).getByText('Trang 1/3')).toBeInTheDocument();
    fireEvent.click(within(thanh).getByRole('button', { name: /Sau/ }));
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({}, 2));
    fireEvent.change(await screen.findByRole('combobox', { name: /Loại tệp/ }), { target: { value: 'LUOT' } });
    await waitFor(() => expect(api.taiLieu).toHaveBeenLastCalledWith({ loai: 'LUOT' }, 1));
  });
});

describe('QuyTrinhPage chọn người ký từ phân hệ CBNV', () => {
  const QUAN_TRI: NguoiDungHienTai = { ...TOI, la_quan_tri: true, quyen: { ...TOI.quyen, manage_signing_process: true } };
  const CHUC_VU_THU_BAC = [
    { id: 10, name: 'Chức vụ cấp cao', display_order: 10 },
    { id: 20, name: 'Chức vụ cấp trung', display_order: 20 },
    { id: 30, name: 'Chức vụ cấp thấp', display_order: 30 },
  ];

  async function moFormThuBac() {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.chucVu.mockResolvedValue(CHUC_VU_THU_BAC);
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    return screen.findAllByRole('combobox', { name: 'Thêm người ký theo chức danh' });
  }

  it('chọn cán bộ từ danh bạ CBNV và chức danh từ Danh mục chức danh; lưu đúng payload', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.danhBaCanBo.mockResolvedValue([
      { id: 31, username: 'tp_kh', ho_ten: 'Lê Văn Minh', don_vi_id: 4, don_vi_ten: 'Phòng Kế hoạch', chuc_vu_id: 5, chuc_vu_ten: 'Trưởng phòng' },
      { id: 32, username: 'cv_kt', ho_ten: 'Phạm Thu Hà', don_vi_id: 2, don_vi_ten: 'Phòng Kế toán', chuc_vu_id: 9, chuc_vu_ten: 'Chuyên viên' },
    ]);
    api.chucVu.mockResolvedValue([{ id: 5, name: 'Trưởng phòng', display_order: 6 }, { id: 2, name: 'Giám đốc', display_order: 3 }]);
    api.taoQuyTrinh.mockResolvedValue({} as QuyTrinh);
    api.canBoTheoChucVu.mockResolvedValue({ count: 1, results: [
      { id: 40, ten: 'Đỗ Quang Huy', chuc_vu: 'Giám đốc', don_vi_id: 1, don_vi: 'Ban Tổng Giám đốc' }] });
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    fireEvent.change(screen.getByRole('textbox', { name: /Mã tra cứu|Mã quy trình/ }), { target: { value: 'QT-CV' } });
    fireEvent.change(screen.getByRole('textbox', { name: /Tên quy trình/ }), { target: { value: 'Theo chức danh' } });
    const tim = screen.getByRole('textbox', { name: 'Thêm người ký' });
    fireEvent.focus(tim);
    fireEvent.change(tim, { target: { value: 'ke toan' } });  // tìm không dấu theo đơn vị
    fireEvent.click(await screen.findByRole('button', { name: /Phạm Thu Hà/ }));
    expect(api.danhBaCanBo).toHaveBeenCalledTimes(1);
    const chonCapKy = await screen.findByRole('combobox', { name: /Tên cấp ký 1/ });
    await waitFor(() => expect(within(chonCapKy).getByRole('option', { name: 'Giám đốc' })).toBeInTheDocument());
    fireEvent.change(chonCapKy, { target: { value: 'Giám đốc' } });
    const chonCv = screen.getByRole('combobox', { name: 'Thêm người ký theo chức danh' });
    expect((chonCv as HTMLSelectElement).value).toBe('2');
    await waitFor(() => expect(within(chonCv).getByRole('option', { name: 'Giám đốc' })).toBeInTheDocument());
    fireEvent.change(chonCv, { target: { value: '2' } });
    // Chọn chức danh là thấy ngay tên người đang giữ chức danh (quy trình công ty: mọi đơn vị)
    expect(await screen.findByText('Đỗ Quang Huy')).toBeInTheDocument();
    expect(api.canBoTheoChucVu).toHaveBeenLastCalledWith(2, null);
    fireEvent.change(screen.getByRole('combobox', { name: 'Phạm vi chức danh' }), { target: { value: 'TOAN_CO_QUAN' } });
    fireEvent.click(screen.getByRole('button', { name: /Thêm người ký theo chức danh/ }));
    expect(screen.getByText('Chức danh: Giám đốc')).toBeInTheDocument();
    expect(await screen.findAllByText('Đỗ Quang Huy')).toHaveLength(1);  // dòng người ký đã thêm (ô chọn đã xóa chức danh)
    fireEvent.click(screen.getByRole('button', { name: /Lưu/ }));
    await waitFor(() => expect(api.taoQuyTrinh).toHaveBeenCalledTimes(1));
    const body = api.taoQuyTrinh.mock.calls[0][0] as { cap_ky: Array<{ nguoi_ky: unknown[] }> };
    expect(body.cap_ky[0].nguoi_ky).toEqual([
      expect.objectContaining({ nguoi_ky: 32, thu_tu: 1, vai_tro_ky: 'KY_CHINH' }),
      expect.objectContaining({ chuc_vu_id: 2, pham_vi_chuc_vu: 'TOAN_CO_QUAN', thu_tu: 2, vai_tro_ky: 'KY_CHINH' }),
    ]);
  });

  it('danh bạ CBNV trong Chọn người ký cụ thể luôn hiển thị đầy đủ tất cả cán bộ nhân viên', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.danhBaCanBo.mockResolvedValue([
      { id: 31, username: 'tp_kh', ho_ten: 'Lê Văn Minh', don_vi_id: 4, don_vi_ten: 'Phòng Kế hoạch', chuc_vu_id: 5, chuc_vu_ten: 'Trưởng phòng' },
      { id: 32, username: 'cv_kt', ho_ten: 'Phạm Thu Hà', don_vi_id: 2, don_vi_ten: 'Phòng Kế toán', chuc_vu_id: 9, chuc_vu_ten: 'Chuyên viên' },
      { id: 33, username: 'tp_cntt', ho_ten: 'Hoàng Đức Nam', don_vi_id: 3, don_vi_ten: 'Phòng CNTT', chuc_vu_id: 5, chuc_vu_ten: 'Trưởng phòng' },
    ]);
    api.chucVu.mockResolvedValue([
      { id: 5, name: 'Trưởng phòng', display_order: 1 },
      { id: 9, name: 'Chuyên viên', display_order: 2 },
    ]);
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));

    const oNhap = screen.getByRole('textbox', { name: 'Thêm người ký' });
    fireEvent.focus(oNhap);
    expect(await screen.findByRole('button', { name: /Phạm Thu Hà/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Lê Văn Minh/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hoàng Đức Nam/ })).toBeInTheDocument();

    // Chọn chức danh "Trưởng phòng" ở phần thêm theo chức danh
    const chonCv = screen.getByRole('combobox', { name: 'Thêm người ký theo chức danh' });
    await waitFor(() => expect(within(chonCv).getByRole('option', { name: 'Trưởng phòng' })).toBeInTheDocument());
    fireEvent.change(chonCv, { target: { value: '5' } });

    // Ô chọn người ký cụ thể vẫn hiển thị đầy đủ cả 3 cán bộ (kể cả Chuyên viên Phạm Thu Hà)
    expect(screen.getByRole('button', { name: /Phạm Thu Hà/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Lê Văn Minh/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hoàng Đức Nam/ })).toBeInTheDocument();
  });

  it('cấp sau chỉ gợi ý chức danh giữ thứ bậc cao hơn hoặc bằng cấp chức danh liền trước', async () => {
    const [capTruoc] = await moFormThuBac();
    fireEvent.change(capTruoc, { target: { value: '20' } });
    fireEvent.click(screen.getByRole('button', { name: /Thêm người ký theo chức danh/ }));
    fireEvent.click(screen.getByRole('button', { name: /Thêm cấp/ }));

    const capSau = (await screen.findAllByRole('combobox', { name: 'Thêm người ký theo chức danh' }))[1];
    await waitFor(() => expect(within(capSau).getByRole('option', { name: 'Chức vụ cấp cao' })).toBeInTheDocument());
    expect(within(capSau).getByRole('option', { name: 'Chức vụ cấp trung' })).toBeInTheDocument();
    expect(within(capSau).queryByRole('option', { name: 'Chức vụ cấp thấp' })).not.toBeInTheDocument();
    expect(screen.getByText(/thứ bậc hiệu lực.*Chức vụ cấp trung.*cấp có chức danh liền trước/i)).toBeInTheDocument();
  });

  it('cấp trước chỉ gợi ý chức danh không làm sai thứ bậc của cấp chức danh liền sau', async () => {
    await moFormThuBac();
    fireEvent.click(screen.getByRole('button', { name: /Thêm cấp/ }));
    const cap = await screen.findAllByRole('combobox', { name: 'Thêm người ký theo chức danh' });
    fireEvent.change(cap[1], { target: { value: '30' } });
    fireEvent.click(screen.getAllByRole('button', { name: /Thêm người ký theo chức danh/ })[1]);

    await waitFor(() => expect(within(cap[0]).getByRole('option', { name: 'Chức vụ cấp thấp' })).toBeInTheDocument());
    expect(within(cap[0]).queryByRole('option', { name: 'Chức vụ cấp cao' })).not.toBeInTheDocument();
    expect(within(cap[0]).queryByRole('option', { name: 'Chức vụ cấp trung' })).not.toBeInTheDocument();
    expect(screen.getByText(/thứ bậc hiệu lực.*Chức vụ cấp thấp.*cấp có chức danh liền sau/i)).toBeInTheDocument();
  });

  it('giới hạn thứ bậc chức danh không làm hẹp danh bạ cán bộ đích danh', async () => {
    api.danhBaCanBo.mockResolvedValue([
      { id: 41, username: 'can_bo_cap_cao', ho_ten: 'Cán bộ cấp cao', don_vi_id: 1, don_vi_ten: 'Đơn vị A', chuc_vu_id: 10, chuc_vu_ten: 'Chức vụ cấp cao' },
      { id: 42, username: 'can_bo_cap_thap', ho_ten: 'Cán bộ cấp thấp', don_vi_id: 2, don_vi_ten: 'Đơn vị B', chuc_vu_id: 30, chuc_vu_ten: 'Chức vụ cấp thấp' },
    ]);
    const [capTruoc] = await moFormThuBac();
    fireEvent.change(capTruoc, { target: { value: '20' } });
    fireEvent.click(screen.getByRole('button', { name: /Thêm người ký theo chức danh/ }));
    fireEvent.click(screen.getByRole('button', { name: /Thêm cấp/ }));

    const capSau = (await screen.findAllByRole('combobox', { name: 'Thêm người ký theo chức danh' }))[1];
    await waitFor(() => expect(within(capSau).queryByRole('option', { name: 'Chức vụ cấp thấp' })).not.toBeInTheDocument());
    const danhBaCapSau = screen.getAllByRole('textbox', { name: 'Thêm người ký' })[1];
    fireEvent.focus(danhBaCapSau);
    expect(await screen.findByRole('button', { name: /Cán bộ cấp cao/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cán bộ cấp thấp/ })).toBeInTheDocument();
  });

  it('hiển thị danh sách Cán bộ nhân viên trong ô tìm kiếm người ký (#330)', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.danhBaCanBo.mockResolvedValue([
      { id: 101, username: 'admin', ho_ten: 'Quản trị hệ thống', don_vi_id: 1, don_vi_ten: 'Ban CNTT', chuc_vu_id: 1, chuc_vu_ten: 'Quản trị viên' },
      { id: 102, username: 'tan', ho_ten: 'tothanhtan', don_vi_id: 2, don_vi_ten: 'Hội đồng quản trị', chuc_vu_id: 1, chuc_vu_ten: 'Quản trị viên' },
    ]);
    api.chucVu.mockResolvedValue([
      { id: 1, name: 'Quản trị viên', display_order: 1 },
      { id: 5, name: 'Tổng Giám đốc', display_order: 5 },
      { id: 19, name: 'Trưởng phòng', display_order: 19 },
    ]);
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));

    const oNhap = screen.getByRole('textbox', { name: 'Thêm người ký' });
    fireEvent.focus(oNhap);

    // Hiển thị trực tiếp danh sách cán bộ, không lẫn nhóm chức danh
    expect(await screen.findByRole('button', { name: /tothanhtan/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /admin/ })).toBeInTheDocument();
    expect(screen.queryByText(/Theo chức danh/)).not.toBeInTheDocument();

    // Bấm chọn cán bộ tothanhtan
    fireEvent.click(screen.getByRole('button', { name: /tothanhtan/ }));
    expect(await screen.findByText('tothanhtan')).toBeInTheDocument();
  });
});

describe('QuyTrinhPage tên cán bộ theo chức danh và đơn vị', () => {
  const TP: NguoiDungHienTai = { ...TOI, don_vi_id: 4, la_lanh_dao_don_vi: true, quyen: { ...TOI.quyen, manage_signing_process: true } };

  it('quy trình phòng ban: tìm theo đơn vị áp dụng; không có ai thì cảnh báo cấp ký không có người ký', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([{ id: 4, ten: 'Phòng Kế hoạch' }]);
    api.chucVu.mockResolvedValue([{ id: 5, name: 'Trưởng phòng', display_order: 6 }]);
    boc(<QuyTrinhPage />, TP);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    const chonCv = await screen.findByRole('combobox', { name: 'Thêm người ký theo chức danh' });
    await waitFor(() => expect(within(chonCv).getByRole('option', { name: 'Trưởng phòng' })).toBeInTheDocument());
    fireEvent.change(chonCv, { target: { value: '5' } });
    expect(await screen.findByRole('alert')).toHaveTextContent('Chưa có cán bộ nào ở chức danh/đơn vị này');
    expect(api.canBoTheoChucVu).toHaveBeenLastCalledWith(5, 4);  // đơn vị người trình = đơn vị áp dụng
  });

  it('chi tiết quy trình hiện tên người đang khớp người ký theo chức danh', async () => {
    const qt: QuyTrinh = {
      id: 8, ma_quy_trinh: 'QT-CV', ten_quy_trinh: 'Theo chức danh', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
      pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, so_ho_so: 0, cap_ky: [{
        id: 1, cap_ky: 1, ten_cap_ky: 'Duyệt', thu_tu: 1, don_vi_id: null, so_gio_xu_ly: null, nguoi_ky: [{
          id: 2, nguoi_ky: null, ten_nguoi_ky: null, chuc_vu_id: 2, ten_chuc_vu: 'Giám đốc', pham_vi_chuc_vu: 'TOAN_CO_QUAN',
          vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true, thu_tu: 1,
        }],
      }],
    };
    api.quyTrinh.mockResolvedValue([qt]);
    api.chiTietQuyTrinh.mockResolvedValue(qt);
    api.canBoTheoChucVu.mockResolvedValue({ count: 2, results: [
      { id: 40, ten: 'Đỗ Quang Huy', chuc_vu: 'Giám đốc', don_vi_id: 1, don_vi: 'Ban Tổng Giám đốc' },
      { id: 41, ten: 'Lý Minh Tâm', chuc_vu: 'Giám đốc', don_vi_id: 2, don_vi: 'Chi nhánh Bắc' }] });
    boc(<QuyTrinhPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Xem chi tiết/ }));
    expect(await screen.findByText('Lý Minh Tâm')).toBeInTheDocument();
    expect(screen.getByText(/Cán bộ đang giữ chức danh \(2\)/)).toBeInTheDocument();
    expect(api.canBoTheoChucVu).toHaveBeenCalledWith(2, null);
  });
});

describe('Chọn cấp ký từ danh mục chức danh CBNV (#297)', () => {
  const QUAN_TRI: NguoiDungHienTai = { ...TOI, la_quan_tri: true, quyen: { ...TOI.quyen, manage_signing_process: true } };
  const QT: QuyTrinh = {
    id: 1, ma_quy_trinh: 'QT-01', ten_quy_trinh: 'Quy trình mẫu', mo_ta: '', phien_ban: 1, trang_thai: 'HOAT_DONG',
    pham_vi: 'CONG_TY', don_vi_ap_dung_id: null, ten_don_vi_ap_dung: null, cap_ky: [], so_ho_so: 0,
  };

  it('hiển thị thông báo khi danh mục chức danh bị lỗi', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.chucVu.mockRejectedValue(new Error('Lỗi máy chủ kết nối CBNV'));
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    expect((await screen.findAllByText('Lỗi máy chủ kết nối CBNV')).length).toBeGreaterThan(0);
  });

  it('hiển thị thông báo khi danh mục chức danh rỗng', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.chucVu.mockResolvedValue([]);
    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));
    expect(await screen.findByText('Chưa có chức danh nào trong danh mục.')).toBeInTheDocument();
  });

  it('bảo toàn tên cấp ký ngoài danh mục khi sửa quy trình nháp', async () => {
    const nhap: QuyTrinh = {
      ...QT,
      id: 99,
      trang_thai: 'NHAP',
      ten_quy_trinh: 'Quy trình cũ',
      cap_ky: [{
        id: 1,
        cap_ky: 1,
        ten_cap_ky: 'Chuyên gia bảo hiểm',
        thu_tu: 1,
        don_vi_id: null,
        so_gio_xu_ly: 24,
        nguoi_ky: [{
          id: 10,
          nguoi_ky: 31,
          ten_nguoi_ky: 'Lê Văn Minh',
          chuc_vu_id: null,
          ten_chuc_vu: null,
          pham_vi_chuc_vu: null,
          vai_tro_ky: 'KY_CHINH',
          chan_ky_chinh: true,
          thu_tu: 1,
        }],
      }],
      so_ho_so: 0,
    };
    api.quyTrinh.mockResolvedValue([nhap]);
    api.chiTietQuyTrinh.mockResolvedValue(nhap);
    api.donVi.mockResolvedValue([]);
    api.chucVu.mockResolvedValue([{ id: 5, name: 'Trưởng phòng', display_order: 1 }]);
    api.suaQuyTrinh.mockResolvedValue(nhap);

    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Sửa quy trình/ }));

    const chonCapKy = await screen.findByRole('combobox', { name: /Tên cấp ký 1/ });
    expect(await within(chonCapKy).findByRole('option', { name: 'Chuyên gia bảo hiểm (Ngoài danh mục)' })).toBeInTheDocument();
    expect((chonCapKy as HTMLSelectElement).value).toBe('Chuyên gia bảo hiểm');

    // Lưu lại không làm mất tên cấp ký ngoài danh mục
    fireEvent.click(screen.getByRole('button', { name: /Lưu/ }));
    await waitFor(() => expect(api.suaQuyTrinh).toHaveBeenCalledTimes(1));
    const payload = api.suaQuyTrinh.mock.calls[0][1] as { cap_ky: Array<{ ten_cap_ky: string }> };
    expect(payload.cap_ky[0].ten_cap_ky).toBe('Chuyên gia bảo hiểm');
  });

  it('chọn chức danh cấp ký đồng bộ sang cấu hình người ký và không làm mất người ký hiện có', async () => {
    api.quyTrinh.mockResolvedValue([]);
    api.donVi.mockResolvedValue([]);
    api.danhBaCanBo.mockResolvedValue([
      { id: 31, username: 'tp_kh', ho_ten: 'Lê Văn Minh', don_vi_id: 4, don_vi_ten: 'Phòng Kế hoạch', chuc_vu_id: 5, chuc_vu_ten: 'Trưởng phòng' },
    ]);
    api.chucVu.mockResolvedValue([
      { id: 5, name: 'Trưởng phòng', display_order: 1 },
      { id: 2, name: 'Giám đốc', display_order: 2 },
    ]);
    api.taoQuyTrinh.mockResolvedValue({} as QuyTrinh);

    boc(<QuyTrinhPage />, QUAN_TRI);
    fireEvent.click(await screen.findByRole('button', { name: /Tạo quy trình/ }));

    // Nhập thông tin bắt buộc
    fireEvent.change(screen.getByRole('textbox', { name: /Mã tra cứu|Mã quy trình/ }), { target: { value: 'QT-SYNC' } });
    fireEvent.change(screen.getByRole('textbox', { name: /Tên quy trình/ }), { target: { value: 'Quy trình đồng bộ' } });

    // Thêm một người ký đích danh trước
    const oTim = screen.getByRole('textbox', { name: 'Thêm người ký' });
    fireEvent.focus(oTim);
    fireEvent.click(await screen.findByRole('button', { name: /Lê Văn Minh/ }));
    expect(await screen.findByText('Lê Văn Minh')).toBeInTheDocument();

    // Chọn chức danh cho cấp ký
    const chonCapKy = await screen.findByRole('combobox', { name: /Tên cấp ký 1/ });
    await waitFor(() => expect(within(chonCapKy).getByRole('option', { name: 'Trưởng phòng' })).toBeInTheDocument());
    fireEvent.change(chonCapKy, { target: { value: 'Trưởng phòng' } });

    // Bộ chọn theo chức danh tự động đồng bộ sang "Trưởng phòng"
    const chonCvNguoiKy = screen.getByRole('combobox', { name: 'Thêm người ký theo chức danh' });
    expect((chonCvNguoiKy as HTMLSelectElement).value).toBe('5');

    // Người ký hiện có không bị mất
    expect(screen.getByText('Lê Văn Minh')).toBeInTheDocument();

    // Lưu quy trình thành công
    fireEvent.click(screen.getByRole('button', { name: /Lưu/ }));
    await waitFor(() => expect(api.taoQuyTrinh).toHaveBeenCalledTimes(1));
    const payload = api.taoQuyTrinh.mock.calls[0][0] as { cap_ky: Array<{ ten_cap_ky: string; nguoi_ky: unknown[] }> };
    expect(payload.cap_ky[0].ten_cap_ky).toBe('Trưởng phòng');
    expect(payload.cap_ky[0].nguoi_ky).toHaveLength(1);
    expect(payload.cap_ky[0].nguoi_ky[0]).toEqual(expect.objectContaining({ nguoi_ky: 31 }));
  });
});

describe('TaiLieuPanel', () => {
  it('liệt kê tệp từng lượt và tải đúng lượt', async () => {
    api.tepCuaLuot.mockResolvedValue(new Blob(['%PDF-'], { type: 'application/pdf' }));
    URL.createObjectURL = vi.fn(() => 'blob:tep');
    URL.revokeObjectURL = vi.fn();
    // Tải tệp bằng thẻ <a download>: jsdom chưa hỗ trợ điều hướng, chặn click để không in cảnh báo "Not implemented"
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    boc(<TaiLieuPanel hoSo={hoSo()} />);
    expect(screen.getByText('Bản trình ký')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tải xuống/ }));
    await waitFor(() => expect(api.tepCuaLuot).toHaveBeenCalledWith(12, 5));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    click.mockRestore();
  });
});
