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

  it('renders 2FA TOTP security card and runs setup wizard when authenticated', async () => {
    localStorage.setItem('tlbm_access_token', 'valid-token');
    localStorage.setItem('tlbm_session', JSON.stringify({ username: 'staff_test', is_2fa_enabled: false }));

    globalThis.fetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url.includes('/api/auth/2fa/status/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            enabled: false,
            backup_codes_remaining: 0,
            has_usable_credential: true,
          }),
        });
      }
      if (url.includes('/api/auth/2fa/setup/') && opts?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            secret_key: 'JBSWY3DPEHPK3PXP',
            otpauth_uri: 'otpauth://totp/Bao%20Long?secret=JBSWY3DPEHPK3PXP',
            qr_code: 'data:image/png;base64,iVBORw0KGgo=',
            setup_token: 'setup-token-123',
            expires_in: 600,
          }),
        });
      }
      if (url.includes('/api/auth/2fa/confirm/') && opts?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            enabled: true,
            backup_codes: ['AAAA-BBBB', 'CCCC-DDDD'],
            backup_codes_remaining: 2,
          }),
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    renderComponent();

    expect(screen.getByText(/xác thực hai yếu tố \(2fa totp\)/i)).toBeInTheDocument();
    const enableBtn = await screen.findByRole('button', { name: /thiết lập & bật 2fa/i });
    fireEvent.click(enableBtn);

    expect(await screen.findByAltText('2FA QR Code')).toBeInTheDocument();
    expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Nhập 6 chữ số OTP...'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /xác nhận kích hoạt 2fa/i }));

    expect(await screen.findByText('AAAA-BBBB')).toBeInTheDocument();
    expect(screen.getByText('CCCC-DDDD')).toBeInTheDocument();
  });
});
