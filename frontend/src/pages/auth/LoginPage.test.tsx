import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import { setLanguage } from '@i18n/translate';

vi.mock('canvas-confetti', () => ({
  default: vi.fn(),
}));

describe('LoginPage i18n and Language Switching', () => {
  beforeEach(() => {
    setLanguage('vi');
  });

  it('renders login form with Vietnamese text by default', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument();
    expect(screen.getByText('Tên đăng nhập hoặc Email')).toBeInTheDocument();
    expect(screen.getByText('Mật khẩu')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /đăng nhập/i })).toBeInTheDocument();
  });

  it('renders LanguageSwitcher and toggles language to English on demand', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Tìm nút chuyển đổi tiếng Anh
    const enBtn = screen.getByRole('button', { name: /switch to english/i });
    expect(enBtn).toBeInTheDocument();

    fireEvent.click(enBtn);

    // Các text phải tự động chuyển sang tiếng Anh
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.getByText('Username or Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('displays authentication error in active language and translates dynamically', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({
        success: false,
        error: 'Tên đăng nhập hoặc mật khẩu không chính xác!',
      }),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Chuyển sang tiếng Anh
    const enBtn = screen.getByRole('button', { name: /switch to english/i });
    fireEvent.click(enBtn);

    // Điền tài khoản sai và submit
    const userInput = screen.getByPlaceholderText('Enter username or email...');
    const passInput = screen.getByPlaceholderText('Enter password...');
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(userInput, { target: { value: 'admind' } });
    fireEvent.change(passInput, { target: { value: 'wrongpass' } });
    fireEvent.click(submitBtn);

    // Thông báo lỗi phải hiển thị bằng tiếng Anh
    expect(await screen.findByText('Incorrect username or password!')).toBeInTheDocument();

    // Khi chuyển lại tiếng Việt
    const viBtn = screen.getByRole('button', { name: /chuyển sang tiếng việt/i });
    fireEvent.click(viBtn);

    // Thông báo lỗi phải tự động chuyển sang tiếng Việt
    expect(screen.getByText('Tên đăng nhập hoặc mật khẩu không chính xác!')).toBeInTheDocument();
  });

  it('transitions to 2FA OTP step when require_2fa is returned and supports email/sms/backup tabs', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/login/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            require_2fa: true,
            temp_token: 'temp-token-xyz',
            method: 'totp',
            auth_provider: 'local',
            available_channels: {
              totp: true,
              backup: true,
              email: true,
              sms: true,
            },
            masked_email: 'ca***@baolong.vn',
            masked_phone: '09******78',
          }),
        });
      }
      if (url.includes('/api/auth/2fa/send-otp/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            otp_token: 'email-otp-token-123',
            channel: 'email',
            masked_destination: 'ca***@baolong.vn',
            expires_in: 300,
            cooldown_seconds: 60,
          }),
        });
      }
      if (url.includes('/api/auth/verify-2fa/')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            detail: 'Mã xác thực không chính xác. Còn 4 lần thử.',
            code: 'otp_invalid',
            attempts_remaining: 4,
          }),
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Nhập tên đăng nhập hoặc email...'), {
      target: { value: 'canbo_2fa@baolong.vn' },
    });
    fireEvent.change(screen.getByPlaceholderText('Nhập mật khẩu...'), {
      target: { value: 'Secret@123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    expect(await screen.findByText('Xác thực 2 bước')).toBeInTheDocument();
    expect(screen.getByLabelText('Tin cậy thiết bị này trong 30 ngày')).toBeChecked();

    const otpInput = screen.getByPlaceholderText('Nhập 6 chữ số...');
    fireEvent.change(otpInput, { target: { value: '111222' } });
    fireEvent.click(screen.getByRole('button', { name: /xác nhận/i }));

    expect(await screen.findByText('Mã xác thực không chính xác. Còn 4 lần thử.')).toBeInTheDocument();

    // Chuyển ngôn ngữ -> lỗi dịch tự động
    fireEvent.click(screen.getByRole('button', { name: /switch to english/i }));
    expect(screen.getByText('Invalid verification code. 4 attempts remaining.')).toBeInTheDocument();

    // Chuyển sang kênh Email và gửi mã OTP
    fireEvent.click(screen.getByRole('button', { name: 'Email' }));
    expect(screen.getByText('ca***@baolong.vn')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Send code' }));
    expect(await screen.findByText('Code sent to ca***@baolong.vn.')).toBeInTheDocument();

    // Chuyển sang dùng mã dự phòng
    fireEvent.click(screen.getByRole('button', { name: 'Backup code' }));
    expect(screen.getByPlaceholderText('Example: ABCD-EFGH')).toBeInTheDocument();
  });

  it('completes self-service forgot password flow via OTP', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/forgot-password/lookup/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            channels: { email: true, sms: true },
            masked_email: 'nv***@baolong.vn',
            masked_phone: '09******11',
          }),
        });
      }
      if (url.includes('/api/auth/forgot-password/send-otp/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            reset_token: 'reset-token-abc',
            channel: 'sms',
            masked_destination: '09******11',
            expires_in: 600,
            cooldown_seconds: 60,
          }),
        });
      }
      if (url.includes('/api/auth/forgot-password/confirm/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            message: 'Đặt lại mật khẩu thành công.',
          }),
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Quên mật khẩu?' }));
    expect(await screen.findByRole('heading', { name: 'Đặt lại mật khẩu' })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Nhập tên đăng nhập hoặc email...'), {
      target: { value: 'nv01@baolong.vn' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp tục' }));

    expect(await screen.findByText(/09\*\*\*\*\*\*11/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /SĐT/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã' }));
    expect(await screen.findByText('Đã gửi mã tới 09******11.')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Nhập 6 chữ số...'), {
      target: { value: '654321' },
    });
    fireEvent.change(screen.getByPlaceholderText('Tối thiểu 8 ký tự...'), {
      target: { value: 'NewPassword@2026' },
    });
    fireEvent.change(screen.getByPlaceholderText('Nhập lại mật khẩu mới...'), {
      target: { value: 'NewPassword@2026' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Cập nhật mật khẩu' }));

    expect(await screen.findByText('Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.')).toBeInTheDocument();
  });

  it('verifies SMS OTP 2FA submission sends otp_token and trust_device flag', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/login/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            require_2fa: true,
            temp_token: 'temp-sms-tok',
            method: 'totp',
            auth_provider: 'local',
            available_channels: { totp: true, backup: true, email: false, sms: true },
            masked_email: '',
            masked_phone: '09******99',
          }),
        });
      }
      if (url.includes('/api/auth/2fa/send-otp/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            otp_token: 'sms-otp-token-99',
            channel: 'sms',
            masked_destination: '09******99',
            expires_in: 300,
            cooldown_seconds: 60,
          }),
        });
      }
      if (url.includes('/api/auth/verify-2fa/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            access: 'jwt-ok',
            refresh: 'refresh-ok',
            verified_via: 'sms',
            user: { id: 10, username: 'sms_user', role: 'staff', is_2fa_enabled: true },
          }),
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });
    globalThis.fetch = fetchMock;

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('Nhập tên đăng nhập hoặc email...'), {
      target: { value: 'sms_user' },
    });
    fireEvent.change(screen.getByPlaceholderText('Nhập mật khẩu...'), {
      target: { value: 'Secret@123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    expect(await screen.findByText('Xác thực 2 bước')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Email' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'SĐT' }));
    fireEvent.click(screen.getByRole('button', { name: 'Gửi mã' }));
    expect(await screen.findByText('Đã gửi mã tới 09******99.')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Nhập 6 chữ số...'), {
      target: { value: '777888' },
    });
    fireEvent.click(screen.getByRole('button', { name: /xác nhận/i }));

    expect(await screen.findByText('Xác thực thành công!')).toBeInTheDocument();
    const verifyCall = fetchMock.mock.calls.find(([u]) => String(u).includes('/api/auth/verify-2fa/'));
    expect(verifyCall).toBeTruthy();
    expect(JSON.parse(verifyCall![1].body)).toEqual({
      temp_token: 'temp-sms-tok',
      code: '777888',
      otp_token: 'sms-otp-token-99',
      trust_device: true,
    });
  });

  it('shows restriction error when privileged account requests forgot password lookup', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        detail: 'Tài khoản quản trị cấp cao không hỗ trợ tự đặt lại mật khẩu. Vui lòng liên hệ Quản trị viên tối cao.',
        code: 'self_reset_restricted',
      }),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Quên mật khẩu?' }));
    fireEvent.change(screen.getByPlaceholderText('Nhập tên đăng nhập hoặc email...'), {
      target: { value: 'admin' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp tục' }));

    expect(
      await screen.findByText(
        'Tài khoản quản trị cấp cao không hỗ trợ tự đặt lại mật khẩu. Vui lòng liên hệ Quản trị viên tối cao.'
      )
    ).toBeInTheDocument();
    expect(screen.queryByText('Nhận mã qua')).not.toBeInTheDocument();
  });
});


