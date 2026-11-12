/**
 * Ảnh chữ ký trên trang PIN: tải qua Bearer và chỉ giới hạn kích thước sau khi cắt.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signingApi } from '@lib/signing/api';
import { SigningContext } from '@lib/signing/hooks';
import type { NguoiDungHienTai } from '@lib/signing/types';
import PinPage from './PinPage';

vi.mock('@lib/signing/api', async () => {
  const actual = await vi.importActual<typeof import('@lib/signing/api')>('@lib/signing/api');
  return {
    ...actual,
    signingApi: {
      pinTrangThai: vi.fn(),
      pinOtpYeuCau: vi.fn(),
      pinOtpXacNhan: vi.fn(),
      pinOtpHuy: vi.fn(),
      taiLenAnhChuKy: vi.fn(),
      xoaAnhChuKy: vi.fn(),
      tepAnhChuKyCaNhan: vi.fn(),
    },
  };
});

vi.mock('@components/signing/CropChuKyModal', () => ({
  default: ({ mo, tep, onLuu }: { mo: boolean; tep: File | null; onLuu: (blob: Blob, dataUrl: string) => void }) => (mo ? (
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
  id: 7,
  ten: 'Người ký',
  don_vi_id: 1,
  la_quan_tri: false,
  la_lanh_dao_don_vi: false,
  co_anh_chu_ky: false,
  quyen: { view_trinhky: true, add_trinhky: false, sign_trinhky: true, send_trinhky: false },
} as NguoiDungHienTai;

const chonTep = (kichThuoc: number, ten = 'chup-dien-thoai.jpg') => {
  const tep = new File([new Uint8Array(kichThuoc)], ten, { type: 'image/jpeg' });
  const input = document.querySelector('input[type="file"][accept^="image/"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [tep] } });
};

const moTrang = () => render(
  <MemoryRouter>
    <SigningContext.Provider value={{ toi: TOI, taiLaiToi: () => undefined }}>
      <PinPage />
    </SigningContext.Provider>
  </MemoryRouter>,
);

const moVoiAnh = () => render(
  <MemoryRouter>
    <SigningContext.Provider value={{ toi: { ...TOI, co_anh_chu_ky: true }, taiLaiToi: () => undefined }}>
      <PinPage />
    </SigningContext.Provider>
  </MemoryRouter>,
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem('tlbm_lang', 'vi');
  api.pinTrangThai.mockResolvedValue({ da_dat_pin: false } as never);
  api.taiLenAnhChuKy.mockResolvedValue({} as never);
  URL.createObjectURL = vi.fn(() => 'blob:anh-chu-ky');
  URL.revokeObjectURL = vi.fn();
});

describe('PinPage: ảnh chữ ký cá nhân', () => {
  it('tệp gốc lớn hơn 2 MB vẫn mở hộp cắt', async () => {
    moTrang();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    chonTep(5 * 1024 * 1024);
    expect(await screen.findByText('Đang cắt chup-dien-thoai.jpg')).toBeInTheDocument();
    expect(screen.queryByText(/vượt quá 2 MB/)).not.toBeInTheDocument();
  });

  it('ảnh sau khi cắt trong giới hạn thì tải lên', async () => {
    moTrang();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    chonTep(5 * 1024 * 1024);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-nho' }));
    await waitFor(() => expect(api.taiLenAnhChuKy).toHaveBeenCalledTimes(1));
  });

  it('ảnh sau khi cắt lớn hơn 2 MB thì báo lỗi và không gọi API', async () => {
    moTrang();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    chonTep(1024);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-lon' }));
    expect(await screen.findByText(/sau khi cắt vượt quá 2 MB/)).toBeInTheDocument();
    expect(api.taiLenAnhChuKy).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog', { name: 'hop-cat' })).not.toBeInTheDocument();
  });

  it('ảnh sau khi cắt fallback sang Base64 nếu upload Blob lỗi', async () => {
    moTrang();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    chonTep(1024);
    api.taiLenAnhChuKy.mockRejectedValueOnce(new Error('Network error on multipart'));
    api.taiLenAnhChuKy.mockResolvedValueOnce({} as never);
    fireEvent.click(await screen.findByRole('button', { name: 'luu-nho' }));
    await waitFor(() => expect(api.taiLenAnhChuKy).toHaveBeenCalledTimes(2));
    expect(api.taiLenAnhChuKy).toHaveBeenLastCalledWith('data:image/png;base64,AA');
    expect(await screen.findByText(/Đã lưu ảnh chữ ký cá nhân/)).toBeInTheDocument();
  });

  it('khi ảnh máy chủ đang tải thì hiển thị trạng thái trống', async () => {
    api.tepAnhChuKyCaNhan.mockReturnValue(new Promise(() => undefined));
    moVoiAnh();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    expect(screen.queryByRole('img', { name: 'Ảnh chữ ký cá nhân' })).not.toBeInTheDocument();
  });

  it('khi tải ảnh máy chủ lỗi thì hiển thị trạng thái trống và nút tải lên', async () => {
    api.tepAnhChuKyCaNhan.mockRejectedValue(new Error('404'));
    moVoiAnh();
    await waitFor(() => expect(api.tepAnhChuKyCaNhan).toHaveBeenCalled());
    expect(screen.getByText('Chưa thiết lập ảnh chữ ký cá nhân')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tải lên ảnh chữ ký/ })).toBeInTheDocument();
  });

  it('tải ảnh máy chủ qua API có Bearer và thu hồi object URL khi rời trang', async () => {
    api.tepAnhChuKyCaNhan.mockResolvedValue(new Blob(['x'], { type: 'image/png' }));
    const { unmount } = moVoiAnh();
    const image = await screen.findByRole('img', { name: 'Ảnh chữ ký cá nhân' });
    expect(api.tepAnhChuKyCaNhan).toHaveBeenCalledOnce();
    expect(image).toHaveAttribute('src', 'blob:anh-chu-ky');
    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:anh-chu-ky');
  });

  it('đặt ảnh chữ ký trên nền giấy sáng cố định để nét mực rõ ở giao diện tối', async () => {
    api.tepAnhChuKyCaNhan.mockResolvedValue(new Blob(['x'], { type: 'image/png' }));
    moVoiAnh();
    const image = await screen.findByRole('img', { name: 'Ảnh chữ ký cá nhân' });
    expect(image.parentElement).toHaveClass('signing-chuky-giay');
  });

  it('không tải ảnh nếu tài khoản không có ảnh chữ ký', async () => {
    moTrang();
    await screen.findByText('Chưa thiết lập ảnh chữ ký cá nhân');
    expect(api.tepAnhChuKyCaNhan).not.toHaveBeenCalled();
  });
});
