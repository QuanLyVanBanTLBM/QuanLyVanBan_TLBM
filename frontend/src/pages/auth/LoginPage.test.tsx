import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import { setLanguage } from '@i18n/translate';

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

    expect(screen.getByText('Chào mừng trở lại')).toBeInTheDocument();
    expect(screen.getByText('Tài khoản / Mã nhân viên')).toBeInTheDocument();
    expect(screen.getByText('Mật khẩu xác thực')).toBeInTheDocument();
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
    expect(screen.getByText('Welcome back')).toBeInTheDocument();
    expect(screen.getByText('Account / Employee ID')).toBeInTheDocument();
    expect(screen.getByText('Authentication Password')).toBeInTheDocument();
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
    const userInput = screen.getByPlaceholderText('Enter username or employee code...');
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

  it('transitions to 2FA OTP step when require_2fa is returned and supports backup code toggle', async () => {
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

    fireEvent.change(screen.getByPlaceholderText('Nhập tên đăng nhập hoặc mã cán bộ...'), {
      target: { value: 'canbo_2fa' },
    });
    fireEvent.change(screen.getByPlaceholderText('Nhập mật khẩu...'), {
      target: { value: 'Secret@123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));

    expect(await screen.findByText('Xác thực hai yếu tố (2FA)')).toBeInTheDocument();

    const otpInput = screen.getByPlaceholderText('Nhập 6 chữ số...');
    fireEvent.change(otpInput, { target: { value: '111222' } });
    fireEvent.click(screen.getByRole('button', { name: /xác nhận & đăng nhập/i }));

    expect(await screen.findByText('Mã xác thực không chính xác. Còn 4 lần thử.')).toBeInTheDocument();

    // Chuyển ngôn ngữ -> lỗi dịch tự động
    fireEvent.click(screen.getByRole('button', { name: /switch to english/i }));
    expect(screen.getByText('Invalid verification code. 4 attempts remaining.')).toBeInTheDocument();

    // Chuyển sang dùng mã dự phòng
    fireEvent.click(screen.getByRole('button', { name: /use a backup code instead/i }));
    expect(screen.getByPlaceholderText('Example: ABCD-EFGH')).toBeInTheDocument();
  });
});


