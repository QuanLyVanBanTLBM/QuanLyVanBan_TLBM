/**
 * Ảnh chữ ký: giới hạn 2 MB chỉ tính trên ảnh PNG sau khi cắt (#463); tệp gốc lớn vẫn mở được hộp cắt.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { NguoiDungHienTai } from '@lib/signing/types';
import KhoaPage from './KhoaPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return { ...actual, signingApi: { khoa: vi.fn(), taiLenAnhChuKy: vi.fn(), tepAnhChuKyCaNhan: vi.fn() } };
});
// Hộp cắt thật cần canvas; thay bằng bản giả cho phép chọn dung lượng ảnh sau cắt
vi.mock('@components/signing/CropChuKyModal', () => ({
  default: ({ mo, tep, onLuu }: { mo: boolean; tep: File | null; onLuu: (b: Blob, d: string) => void }) => (mo ? (
    <div role="dialog" aria-label="hop-cat">
      <span>{`Đang cắt ${tep?.name}`}</span>
      <button type="button" onClick={() => onLuu(new Blob([new Uint8Array(1024)], { type: 'image/png' }), 'data:image/png;base64,AA')}>
        luu-nho
      </button>
      <button type="button" onClick={() => onLuu(new Blob([new Uint8Array(2 * 1024 * 1024 + 1)], { type: 'image/png' }), 'data:image/png;base64,AA')}>
        luu-lon
      </button>
    </div>
  ) : null),
}));
const api = vi.mocked(signingApi);

const TOI = {
  id: 7, ten: 'Người ký', don_vi_id: 1, la_quan_tri: false, la_lanh_dao_don_vi: false, co_anh_chu_ky: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;

const chonTep = (kichThuoc: number, ten = 'chup-dien-thoai.jpg') => {
  const tep = new File([new Uint8Array(kichThuoc)], ten, { type: 'image/jpeg' });
  const o = document.querySelector('input[type="file"][accept^="image/"]') as HTMLInputElement;
  fireEvent.change(o, { target: { files: [tep] } });
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.khoa.mockResolvedValue([]);
  api.taiLenAnhChuKy.mockResolvedValue({} as never);
});

const moTrang = async () => {
  render(
    <MemoryRouter>
      <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}><KhoaPage /></SigningContext.Provider>
    </MemoryRouter>,
  );
  await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
};

describe('KhoaPage: giới hạn dung lượng ảnh chữ ký', () => {
  it('tệp gốc lớn hơn 2 MB vẫn mở hộp cắt và không báo lỗi', async () => {
    await moTrang();
    chonTep(5 * 1024 * 1024);
    expect(await screen.findByText('Đang cắt chup-dien-thoai.jpg')).toBeInTheDocument();
    expect(screen.queryByText(/vượt quá 2 MB/)).not.toBeInTheDocument();
  });

  it('ảnh sau khi cắt trong giới hạn thì tải lên', async () => {
    await moTrang();
    chonTep(5 * 1024 * 1024);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-nho' }));
    await waitFor(() => expect(api.taiLenAnhChuKy).toHaveBeenCalledTimes(1));
  });

  it('ảnh sau khi cắt lớn hơn 2 MB thì báo lỗi, đóng hộp cắt và không gọi API', async () => {
    await moTrang();
    chonTep(1024);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-lon' }));
    expect(await screen.findByText(/sau khi cắt vượt quá 2 MB/)).toBeInTheDocument();
    expect(api.taiLenAnhChuKy).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog', { name: 'hop-cat' })).not.toBeInTheDocument();
  });

  it('ảnh sau khi cắt nếu tải dạng Blob lỗi thì tự động fallback sang Base64', async () => {
    await moTrang();
    chonTep(1024);
    api.taiLenAnhChuKy.mockRejectedValueOnce(new Error('Network error on multipart'));
    api.taiLenAnhChuKy.mockResolvedValueOnce({} as never);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-nho' }));
    await waitFor(() => expect(api.taiLenAnhChuKy).toHaveBeenCalledTimes(2));
    expect(api.taiLenAnhChuKy).toHaveBeenLastCalledWith('data:image/png;base64,AA');
    expect(await screen.findByText(/Đã lưu ảnh chữ ký cá nhân/)).toBeInTheDocument();
  });

  describe('ảnh chữ ký từ máy chủ (tải qua Bearer)', () => {
    const moVoiAnh = () =>
      render(
        <MemoryRouter>
          <SigningContext.Provider value={{ toi: { ...TOI, co_anh_chu_ky: true }, taiLaiToi: () => undefined }}>
            <KhoaPage />
          </SigningContext.Provider>
        </MemoryRouter>,
      );
    const kiemTraTrong = () => {
      expect(screen.getByText('Chưa thiết lập ảnh chữ ký cá nhân')).toBeInTheDocument();
      expect(screen.queryByRole('img', { name: 'Ảnh chữ ký cá nhân' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Tải lên ảnh chữ ký/ })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Thay đổi ảnh chữ ký/ })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Xóa ảnh chữ ký/ })).not.toBeInTheDocument();
    };

    beforeEach(() => {
      URL.createObjectURL = vi.fn(() => 'blob:anh-chu-ky');
      URL.revokeObjectURL = vi.fn();
    });

    it('chưa tải xong thì hiển thị trạng thái trống, không có thẻ img', async () => {
      api.tepAnhChuKyCaNhan.mockReturnValue(new Promise(() => undefined));
      moVoiAnh();
      await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
      kiemTraTrong();
    });

    it('tải lỗi (401/404) thì hiển thị trạng thái trống kèm nút tải lên', async () => {
      api.tepAnhChuKyCaNhan.mockRejectedValue(new Error('404'));
      moVoiAnh();
      await waitFor(() => expect(api.tepAnhChuKyCaNhan).toHaveBeenCalled());
      kiemTraTrong();
    });

    it('tải thành công thì hiển thị ảnh từ object URL và thu hồi khi gỡ trang', async () => {
      api.tepAnhChuKyCaNhan.mockResolvedValue(new Blob(['x'], { type: 'image/png' }));
      const { unmount } = moVoiAnh();
      const img = await screen.findByRole('img', { name: 'Ảnh chữ ký cá nhân' });
      expect(img).toHaveAttribute('src', 'blob:anh-chu-ky');
      expect(screen.getByRole('button', { name: /Thay đổi ảnh chữ ký/ })).toBeInTheDocument();
      unmount();
      expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:anh-chu-ky');
    });

    it('cờ co_anh_chu_ky=false thì không gọi tải tệp', async () => {
      render(
        <MemoryRouter>
          <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}><KhoaPage /></SigningContext.Provider>
        </MemoryRouter>,
      );
      await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
      expect(api.tepAnhChuKyCaNhan).not.toHaveBeenCalled();
    });
  });
});
