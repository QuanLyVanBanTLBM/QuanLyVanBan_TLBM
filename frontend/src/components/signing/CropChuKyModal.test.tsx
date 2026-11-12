/**
 * Hộp thoại cắt ảnh chữ ký: khung cắt, điều khiển thu phóng và bộ màu cố định (không phụ thuộc theme).
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CropChuKyModal from './CropChuKyModal';

class AnhGia {
  width = 600;
  height = 300;
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  set src(_v: string) {
    queueMicrotask(() => this.onload?.());
  }
}

const moHopThoai = async () => {
  const tep = new File([new Uint8Array(8)], 'chu-ky.png', { type: 'image/png' });
  render(<CropChuKyModal mo onDong={() => {}} tep={tep} onLuu={() => {}} />);
  await screen.findByRole('slider');
};

describe('CropChuKyModal', () => {
  beforeEach(() => {
    vi.stubGlobal('Image', AnhGia);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('dùng lớp nền caro và khung cắt có lưới, 4 góc', async () => {
    await moHopThoai();
    const khung = screen.getByTestId('khung-cat');
    expect(khung.classList.contains('signing-crop-khung')).toBe(true);
    expect(khung.querySelector('.signing-crop-luoi')).not.toBeNull();
    expect(khung.querySelectorAll('.signing-crop-goc')).toHaveLength(4);
    expect(khung.parentElement?.classList.contains('signing-chuky-caro')).toBe(true);
  });

  it('nút phóng to, thu nhỏ và đặt lại cập nhật mức thu phóng', async () => {
    await moHopThoai();
    const slider = screen.getByRole('slider');
    expect(slider.getAttribute('aria-valuetext')).toBe('100%');
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to' }));
    await waitFor(() => expect(slider.getAttribute('aria-valuetext')).toBe('110%'));
    fireEvent.click(screen.getByRole('button', { name: 'Thu nhỏ' }));
    fireEvent.click(screen.getByRole('button', { name: 'Thu nhỏ' }));
    await waitFor(() => expect(slider.getAttribute('aria-valuetext')).toBe('90%'));
    fireEvent.click(screen.getByRole('button', { name: /Đặt lại/ }));
    await waitFor(() => expect(slider.getAttribute('aria-valuetext')).toBe('100%'));
  });
});
