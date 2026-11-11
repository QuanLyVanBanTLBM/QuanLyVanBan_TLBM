/** Trang quản trị quyền ký: dòng trạng thái PIN hiển thị thành khối riêng; bố cục thẻ dưới breakpoint sm giữ nút Thao tác trong khung. */
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { NguoiDungHienTai, QuanTriNguoiDung } from '@lib/signing/types';
import QuanTriQuyenKyPage from './QuanTriQuyenKyPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { quanTriNguoiDung: vi.fn() } };
});

const QUAN_TRI: NguoiDungHienTai = {
  id: 1, ten: 'Quản trị', don_vi_id: 1, la_quan_tri: true, la_lanh_dao_don_vi: false, quyen: {},
};
const nguoi = (id: number, soSai: number): QuanTriNguoiDung => ({
  id, ten: `Người ${id}`, ten_dang_nhap: `u${id}`, chuc_vu: null, don_vi: null, co_quyen_ky: true,
  pin: { da_dat: true, so_lan_sai_ngay: soSai, so_lan_sai_chu_ky: 0, khoa_den: null },
  khoa_quyen_ky: null,
});

beforeEach(() => {
  localStorage.setItem('tlbm_lang', 'vi');
  vi.mocked(signingApi.quanTriNguoiDung).mockResolvedValue([nguoi(2, 3), nguoi(3, 0)]);
});

describe('QuanTriQuyenKyPage', () => {
  it('dòng PIN là khối riêng và có nút Thao tác trên mỗi dòng', async () => {
    render(
      <MemoryRouter><SigningContext.Provider value={{ toi: QUAN_TRI, taiLaiToi: () => undefined }}>
        <QuanTriQuyenKyPage />
      </SigningContext.Provider></MemoryRouter>,
    );
    const sai = await screen.findByText(/Sai 3\/10 lần trong ngày/);
    expect(sai.tagName).toBe('DIV');
    expect(screen.getByText('Bình thường', { selector: 'div' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Khóa quyền/ })).toHaveLength(2);
  });
});
