/**
 * Giao diện Trình ký (#80 mục E): tab theo quyền, danh sách (rỗng/lỗi/thử lại), hành động theo quyền và trạng thái,
 * hộp thoại ký hiển thị mã băm và chặn ký khi tệp đang xem khác mã băm đã khóa.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HanhDong from '@components/signing/HanhDong';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, NguoiDungHienTai } from '@lib/signing/types';
import DanhSachPage from './DanhSachPage';
import SigningModule from './SigningModule';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { toi: vi.fn(), danhSach: vi.fn() } };
});
const api = vi.mocked(signingApi);

const TOI: NguoiDungHienTai = {
  id: 7, ten: 'Trưởng phòng', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
};

function hoSo(sua: Partial<HoSoChiTiet> = {}): HoSoChiTiet {
  return {
    id: 12, document_type: 'vanbandi', van_ban_id: 3, van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
    quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt mua sắm', phien_ban_quy_trinh: 1, muc_do: 'KHAN',
    trang_thai: 'CHO_KY', han_chot: null, ngay_gui: null, ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '',
    ghi_chu: '', ho_so_goc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3,
    ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z', dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Trưởng phòng', vai_tro_ky: 'KY_CHINH' }],
    luot_trinh: [{
      id: 5, so_luot: 1, luot_truoc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), trang_thai: 'CHO_KY',
      ly_do: '', thoi_diem_gui: null, thoi_diem_hoan_thanh: null, trang_thai_tep_hoan_tat: null, loi_tep_hoan_tat: '',
      ma_bam_tep_hoan_tat: '', ma_bam_bang_chung: null, cap_ky: [], yeu_cau_sua: [],
    }],
    lich_su: [],
    ...sua,
  };
}

const boc = (ui: React.ReactNode, toi: NguoiDungHienTai = TOI) => render(
  <MemoryRouter><SigningContext.Provider value={{ toi, taiLaiToi: () => undefined }}>{ui}</SigningContext.Provider></MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
});

describe('SigningModule', () => {
  it('chỉ hiện tab theo quyền (không có quyền tạo thì không có tab tạo hồ sơ)', async () => {
    api.toi.mockResolvedValue(TOI);
    api.danhSach.mockResolvedValue([]);
    render(<MemoryRouter initialEntries={['/approvals']}><SigningModule /></MemoryRouter>);
    expect(await screen.findByRole('link', { name: /Cần tôi ký duyệt/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Khóa ký & PIN/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Tạo hồ sơ trình ký/ })).not.toBeInTheDocument();
  });
});

describe('DanhSachPage', () => {
  it('hiện trạng thái rỗng', async () => {
    api.danhSach.mockResolvedValue([]);
    boc(<DanhSachPage hop="can_toi_ky" />);
    expect(await screen.findByText('Không có hồ sơ nào đang chờ bạn ký duyệt.')).toBeInTheDocument();
    expect(api.danhSach).toHaveBeenCalledWith('can_toi_ky', undefined);
  });

  it('hiện dòng hồ sơ với văn bản, mức độ, trạng thái, người đang chờ', async () => {
    api.danhSach.mockResolvedValue([hoSo()]);
    boc(<DanhSachPage hop="toi_gui" />);
    expect(await screen.findByRole('link', { name: '#12' })).toHaveAttribute('href', '/approvals/12');
    const bang = within(screen.getByRole('table'));
    expect(bang.getByText('15/TTr — Mua sắm')).toBeInTheDocument();
    expect(bang.getByText('Khẩn')).toBeInTheDocument();
    expect(bang.getByText('Đang chờ ký')).toBeInTheDocument();
    expect(bang.getByText('Trưởng phòng')).toBeInTheDocument();
  });

  it('lỗi tải có nút thử lại', async () => {
    api.danhSach.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce([]);
    boc(<DanhSachPage hop="tat_ca" />);
    fireEvent.click(await screen.findByRole('button', { name: /Thử lại/ }));
    expect(await screen.findByText('Chưa có hồ sơ nào bạn được xem.')).toBeInTheDocument();
  });
});

describe('HanhDong', () => {
  it('người ký đang được mở thấy Ký duyệt / Trả lại để sửa / Không đồng ý; không thấy Hủy', () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'a'.repeat(64)} onXong={() => undefined} />);
    expect(screen.getByRole('button', { name: /Ký duyệt/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Trả lại để sửa/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Không đồng ý ban hành/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Hủy hồ sơ/ })).not.toBeInTheDocument();
  });

  it('người ngoài luồng không thấy hành động ký; người tạo thấy Hủy', () => {
    const nguoiTao = { ...TOI, id: 3 };
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={null} onXong={() => undefined} />, nguoiTao);
    expect(screen.queryByRole('button', { name: /Ký duyệt/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hủy hồ sơ/ })).toBeInTheDocument();
  });

  it('hộp thoại ký hiện mã băm và chặn ký khi tệp đang xem khác mã băm đã khóa', async () => {
    boc(<HanhDong hoSo={hoSo()} luot={hoSo().luot_trinh[0]} maBamTepDangXem={'b'.repeat(64)} onXong={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: /Ký duyệt/ }));
    const hop = await screen.findByRole('dialog');
    expect(hop).toHaveTextContent('a'.repeat(64));
    expect(hop).toHaveTextContent('Tệp đã thay đổi so với lượt trình');
    fireEvent.change(screen.getByLabelText(/Nhập PIN ký/), { target: { value: '48273916' } });
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Ký duyệt/ }).at(-1)).toBeDisabled());
  });
});
