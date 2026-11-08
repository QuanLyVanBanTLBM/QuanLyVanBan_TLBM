import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import SettingsPage from './SettingsPage';
import soundAlert from '@lib/soundAlert';

// Mock soundAlert
vi.mock('@lib/soundAlert', () => ({
  default: {
    isUrgentSoundEnabled: vi.fn().mockReturnValue(true),
    setUrgentSoundEnabled: vi.fn(),
    playUrgentChime: vi.fn(),
  },
}));

describe('SettingsPage Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <SettingsPage />
      </BrowserRouter>
    );

  it('renders Sound Alert and Screen Security cards', () => {
    renderComponent();

    // Sound alert section
    expect(screen.getByText(/cấu hình cảnh báo âm thanh/i)).toBeInTheDocument();
    expect(screen.getByText(/cảnh báo âm thanh đối với văn bản có độ khẩn/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /nghe thử âm thanh/i })).toBeInTheDocument();

    // Security section
    expect(screen.getByText(/bảo mật phiên làm việc/i)).toBeInTheDocument();
    expect(screen.getByText(/tự động khóa màn hình làm việc khi không thao tác/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /khóa màn hình ngay/i })).toBeInTheDocument();
  });

  it('does NOT render removed mock toggles', () => {
    renderComponent();

    // Ensure mock toggles are absent
    expect(screen.queryByText(/nhận thông báo khi có văn bản đến mới được phân phối/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/nhắc việc tự động trước hạn xử lý 01 ngày/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/bắt buộc xác thực hai bước \(2fa\) khi truy cập tài liệu tuyệt mật/i)).not.toBeInTheDocument();
  });

  it('calls soundAlert.playUrgentChime when clicking Test Sound', () => {
    renderComponent();

    const testSoundButton = screen.getByRole('button', { name: /nghe thử âm thanh/i });
    fireEvent.click(testSoundButton);

    expect(soundAlert.playUrgentChime).toHaveBeenCalledWith(true);
  });

  it('dispatches tlbm_lock_screen_now event when clicking Lock Screen Now', () => {
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
    renderComponent();

    const lockNowButton = screen.getByRole('button', { name: /khóa màn hình ngay/i });
    fireEvent.click(lockNowButton);

    expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({ type: 'tlbm_lock_screen_now' }));
  });

  it('saves settings to localStorage on clicking Save Settings', () => {
    renderComponent();

    const saveButton = screen.getByRole('button', { name: /lưu cài đặt/i });
    fireEvent.click(saveButton);

    expect(localStorage.getItem('tlbm_notif_sound_urgent')).toBe('true');
    expect(localStorage.getItem('tlbm_sec_auto_lock')).toBe('true');
    expect(localStorage.getItem('tlbm_sec_lock_timeout')).toBe('15');
    expect(screen.getByText(/đã lưu thành công/i)).toBeInTheDocument();
  });
});
