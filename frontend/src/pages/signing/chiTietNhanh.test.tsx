/**
 * Hộp thoại "Chi tiết hồ sơ" mở từ danh sách hồ sơ: bấm thường mở hộp thoại, Ctrl+click giữ hành vi liên kết, hộp thoại chỉ
 * đọc (không khung PDF, không nút ký/hủy), "Mở hồ sơ" điều hướng kèm state nguồn, Esc đóng và trả tiêu điểm.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { HoSoChiTiet, NguoiDungHienTai } from '@lib/signing/types';
import DanhSachPage from './DanhSachPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: {
    danhSach: vi.fn(), thongKe: vi.fn(), chiTiet: vi.fn(), quyTrinh: vi.fn(), donViApDungTheoHop: vi.fn(), chucVu: vi.fn(),
    tepCuaLuot: vi.fn(), tepGoc: vi.fn(), tepHoanTat: vi.fn(), bangChung: vi.fn(),
  } };
});
const api = vi.mocked(signingApi);

const TOI: NguoiDungHienTai = {
  id: 7, ten: 'Trưởng phòng', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
};

function hoSo(): HoSoChiTiet {
  return {
    id: 12, document_type: 'vanbandi', van_ban_id: 3, so_hieu_van_ban: '', trich_yeu_van_ban: '',
    van_ban: { so_hieu: '15/TTr', trich_yeu: 'Mua sắm' },
    quy_trinh: 1, ma_quy_trinh: 'QT', ten_quy_trinh: 'Duyệt mua sắm', phien_ban_quy_trinh: 1,
    trang_thai: 'CHO_KY', han_chot: null, ngay_gui: '2026-10-07T01:00:00Z', ngay_hoan_thanh: null, ly_do_tu_choi: '', ly_do_huy: '',
    ghi_chu: 'Ghi chú nội bộ', ho_so_goc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), create_by: 3,
    ten_nguoi_tao: 'Văn thư', created_at: '2026-10-07T01:00:00Z',
    dang_cho: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Trưởng phòng', vai_tro_ky: 'KY_CHINH' }],
    luot_trinh: [{
      id: 5, so_luot: 1, luot_truoc: null, phien_ban_van_ban: '1', ma_bam_tai_lieu: 'a'.repeat(64), trang_thai: 'CHO_KY',
      ly_do: '', thoi_diem_gui: '2026-10-07T01:00:00Z', thoi_diem_hoan_thanh: null, trang_thai_tep_hoan_tat: null, loi_tep_hoan_tat: '',
      ma_bam_tep_hoan_tat: '', ma_bam_bang_chung: null, yeu_cau_sua: [],
      cap_ky: [{
        id: 9, cap_ky: 1, ten_cap_ky: 'Cấp trưởng phòng', trang_thai: 'DANG_KY', han_xu_ly: null,
        nguoi_ky: [{ id: 1, nguoi_ky: 7, ten_nguoi_ky: 'Trưởng phòng', ten_chuc_vu: '', vai_tro_ky: 'KY_CHINH', trang_thai: 'CHO_KY' }],
      }],
    }],
    lich_su: [{ id: 1, hanh_dong: 'GUI', chi_tiet: '', ten_nguoi_thuc_hien: 'Văn thư', created_at: '2026-10-07T01:00:00Z' }],
    trang_thai_luot: 'CHO_KY', qua_han: false,
  } as unknown as HoSoChiTiet;
}

function ViTri() {
  const loc = useLocation();
  return <div data-testid="vi-tri">{loc.pathname}|{JSON.stringify(loc.state)}</div>;
}

const boc = (hop: 'can_toi_ky' | 'toi_gui' | 'tat_ca' = 'toi_gui') => render(
  <MemoryRouter initialEntries={['/approvals']}>
    <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
      <Routes>
        <Route path="/approvals" element={<DanhSachPage hop={hop} />} />
        <Route path="/approvals/:id" element={<ViTri />} />
      </Routes>
    </SigningContext.Provider>
  </MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  const dong: Partial<HoSoChiTiet> = hoSo();
  delete dong.luot_trinh;
  delete dong.lich_su;
  api.danhSach.mockResolvedValue({ count: 1, next: null, previous: null, results: [dong] } as never);
  api.thongKe.mockResolvedValue({ tat_ca: 1 } as never);
  api.quyTrinh.mockResolvedValue([]);
  api.donViApDungTheoHop.mockResolvedValue([]);
  api.chucVu.mockResolvedValue([]);
  api.chiTiet.mockResolvedValue(hoSo());
});

const tieuDe = async () => within(await screen.findByRole('table')).getByRole('link', { name: /15\/TTr — Mua sắm/ });

describe('Hộp thoại chi tiết hồ sơ trong danh sách', () => {
  it('bấm thường vào tiêu đề mở hộp thoại, không điều hướng, đủ thông tin và tiến trình', async () => {
    boc();
    fireEvent.click(await tieuDe());
    const hop = await screen.findByRole('dialog', { name: 'Chi tiết hồ sơ' });
    expect(screen.queryByTestId('vi-tri')).not.toBeInTheDocument();
    const trong = within(hop);
    expect(trong.getByText('Duyệt mua sắm')).toBeInTheDocument();
    expect(trong.getByText('Ghi chú nội bộ')).toBeInTheDocument();
    expect(await trong.findByText(/Cấp trưởng phòng/)).toBeInTheDocument();
    expect(trong.getByText('Tiến trình ký duyệt')).toBeInTheDocument();
    expect(trong.getByText('Lịch sử gần đây')).toBeInTheDocument();
    expect(trong.getByRole('button', { name: /Tải xuống/ })).toBeInTheDocument();
    expect(api.chiTiet).toHaveBeenCalledWith(12);
  });

  it('bấm vào hàng (ngoài tiêu đề) cũng mở hộp thoại', async () => {
    boc();
    fireEvent.click(within(await screen.findByRole('table')).getByText(/#12 · Duyệt mua sắm/));
    expect(await screen.findByRole('dialog', { name: 'Chi tiết hồ sơ' })).toBeInTheDocument();
  });

  it('Ctrl+click vào tiêu đề không bị chặn và không mở hộp thoại', async () => {
    boc();
    const lienKet = await tieuDe();
    const duocPhep = fireEvent.click(lienKet, { ctrlKey: true });
    expect(duocPhep).toBe(true);
    expect(lienKet).toHaveAttribute('href', '/approvals/12');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('không có khung xem PDF và không có nút ký, trả lại, từ chối, hủy', async () => {
    boc('can_toi_ky');
    fireEvent.click(await tieuDe());
    const hop = within(await screen.findByRole('dialog'));
    await hop.findByText(/Cấp trưởng phòng/);
    expect(document.querySelector('canvas')).toBeNull();
    for (const ten of [/^Ký duyệt$/, /Trả lại/, /Từ chối/, /Hủy/]) {
      expect(hop.queryByRole('button', { name: ten })).not.toBeInTheDocument();
    }
    expect(api.tepGoc).not.toHaveBeenCalled();
    expect(api.tepCuaLuot).not.toHaveBeenCalled();
  });

  it('"Mở hồ sơ" điều hướng /approvals/:id kèm state nguồn; tab cần ký ghi "Mở để ký duyệt"', async () => {
    boc('can_toi_ky');
    fireEvent.click(await tieuDe());
    const hop = within(await screen.findByRole('dialog'));
    fireEvent.click(hop.getByRole('button', { name: 'Mở để ký duyệt' }));
    expect(await screen.findByTestId('vi-tri')).toHaveTextContent('/approvals/12|{"hop":"can_toi_ky"}');
  });

  it('Esc đóng hộp thoại và trả tiêu điểm về liên kết của hàng', async () => {
    boc();
    const lienKet = await tieuDe();
    fireEvent.click(lienKet);
    await screen.findByRole('dialog');
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(lienKet).toHaveFocus();
  });

  it('đang tải rồi lỗi mạng hiện "Thử lại" và tải lại được', async () => {
    api.chiTiet.mockRejectedValueOnce(new Error('mạng'));
    boc();
    fireEvent.click(await tieuDe());
    const hop = within(await screen.findByRole('dialog'));
    expect(hop.getByText('Duyệt mua sắm')).toBeInTheDocument();
    fireEvent.click(await hop.findByRole('button', { name: 'Thử lại' }));
    expect(await hop.findByText(/Cấp trưởng phòng/)).toBeInTheDocument();
    expect(api.chiTiet).toHaveBeenCalledTimes(2);
  });
});
