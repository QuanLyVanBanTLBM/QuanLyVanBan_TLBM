import { describe, it, expect, beforeEach, vi } from 'vitest';
import authService, { TwoFactorRequiredError } from './authService';
import apiClient, { ApiError } from './apiClient';

describe('authService Unit Tests (Issue #8 Django Auth & Session Management)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores access and refresh tokens and returns user session on successful login', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        access: 'jwt-access-token-xyz',
        refresh: 'jwt-refresh-token-123',
        user: {
          id: 1,
          username: 'admin',
          fullName: 'Quản Trị Viên Hệ Thống',
          role: 'admin',
          roleTitle: 'Quản trị viên tối cao',
        },
      }),
    });

    const session = await authService.login({
      username: 'admin',
      password: 'Admin@123',
    });

    expect(session.username).toBe('admin');
    expect(session.fullName).toBe('Quản Trị Viên Hệ Thống');
    expect(session.role).toBe('admin');
    expect(session.token).toBe('jwt-access-token-xyz');

    expect(localStorage.getItem('tlbm_access_token')).toBe('jwt-access-token-xyz');
    expect(localStorage.getItem('tlbm_refresh_token')).toBe('jwt-refresh-token-123');
    expect(authService.isAuthenticated()).toBe(true);
    expect(authService.getSession()?.username).toBe('admin');
  });

  it('does NOT infer admin role if backend returns role staff, even if username contains admin', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        access: 'jwt-access-token-guest',
        refresh: 'jwt-refresh-token-guest',
        user: {
          id: 99,
          username: 'admin_intern',
          fullName: 'Thực Tập Sinh',
          role: 'staff',
          roleTitle: 'Cán bộ thực tập',
        },
      }),
    });

    const session = await authService.login({
      username: 'admin_intern',
      password: 'InternPassword123',
    });

    // Quyền phải là staff theo backend, không tự đoán admin
    expect(session.role).toBe('staff');
    expect(session.roleTitle).toBe('Cán bộ thực tập');
  });

  it('preserves exact password without trimming whitespace', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: true,
        access: 'jwt-token-whitespace',
        user: { id: 2, username: 'test_user', role: 'staff' },
      }),
    });
    globalThis.fetch = fetchMock;

    const rawPasswordWithSpaces = '   my secure password with space   ';
    await authService.login({
      username: '  test_user  ',
      password: rawPasswordWithSpaces,
    });

    expect(fetchMock).toHaveBeenCalled();
    const calledBody = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(calledBody.username).toBe('test_user'); // username được trim
    expect(calledBody.password).toBe(rawPasswordWithSpaces); // password KHÔNG bị trim
  });

  it('does not store token or session when login fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        success: false,
        error: 'Tên đăng nhập hoặc mật khẩu không chính xác!',
      }),
    });

    await expect(
      authService.login({ username: 'user', password: 'wrong' })
    ).rejects.toThrow(ApiError);

    expect(localStorage.getItem('tlbm_access_token')).toBeNull();
    expect(localStorage.getItem('tlbm_session')).toBeNull();
    expect(authService.isAuthenticated()).toBe(false);
  });

  it('clears all credentials and dispatches tlbm_auth_changed on logout', async () => {
    localStorage.setItem('tlbm_access_token', 'token-to-be-removed');
    localStorage.setItem('tlbm_refresh_token', 'refresh-to-be-removed');
    localStorage.setItem('tlbm_session', JSON.stringify({ username: 'canbo' }));

    const eventSpy = vi.fn();
    window.addEventListener('tlbm_auth_changed', eventSpy);

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true, message: 'Đã đăng xuất' }),
    });

    await authService.logout();

    expect(localStorage.getItem('tlbm_access_token')).toBeNull();
    expect(localStorage.getItem('tlbm_refresh_token')).toBeNull();
    expect(localStorage.getItem('tlbm_session')).toBeNull();
    expect(authService.isAuthenticated()).toBe(false);
    expect(eventSpy).toHaveBeenCalled();
  });

  it('auto-refreshes token on 401 in apiClient and retries original request', async () => {
    localStorage.setItem('tlbm_access_token', 'expired-token');
    localStorage.setItem('tlbm_refresh_token', 'valid-refresh-token');

    let requestCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      requestCount++;
      if (url.includes('/api/auth/token/refresh/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ access: 'brand-new-access-token' }),
        });
      }

      if (requestCount === 1) {
        // Request đầu tiên bị 401
        return Promise.resolve({
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ error: 'Token expired' }),
        });
      }

      // Request thứ 2 sau khi retry với token mới -> thành công
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ success: true, data: 'secure content' }),
      });
    });

    const result = await apiClient<{ success: boolean; data: string }>('/api/protected-resource/');
    expect(result.data).toBe('secure content');
    expect(localStorage.getItem('tlbm_access_token')).toBe('brand-new-access-token');
  });

  it('clears session when refresh token fails on 401', async () => {
    localStorage.setItem('tlbm_access_token', 'expired-token');
    localStorage.setItem('tlbm_refresh_token', 'invalid-refresh-token');
    localStorage.setItem('tlbm_session', JSON.stringify({ username: 'user' }));

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/token/refresh/')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ error: 'Refresh token blacklisted' }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ error: 'Unauthorized' }),
      });
    });

    await expect(apiClient('/api/protected/')).rejects.toThrow(ApiError);
    expect(localStorage.getItem('tlbm_access_token')).toBeNull();
    expect(localStorage.getItem('tlbm_session')).toBeNull();
  });

  it('throws TwoFactorRequiredError when backend requires 2FA challenge and verifyTwoFactor completes login', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/login/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            success: true,
            require_2fa: true,
            temp_token: 'temp-2fa-token-abc',
            method: 'totp',
            auth_provider: 'local',
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
            access: 'final-jwt-access',
            refresh: 'final-jwt-refresh',
            verified_via: 'totp',
            user: {
              id: 7,
              username: 'canbo_2fa',
              fullName: 'Cán bộ 2FA',
              role: 'staff',
              is_2fa_enabled: true,
              has_usable_credential: true,
            },
          }),
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    await expect(
      authService.login({ username: 'canbo_2fa', password: 'Secret@123' })
    ).rejects.toBeInstanceOf(TwoFactorRequiredError);

    expect(authService.isAuthenticated()).toBe(false);

    const session = await authService.verifyTwoFactor({
      tempToken: 'temp-2fa-token-abc',
      code: '123456',
      username: 'canbo_2fa',
    });

    expect(session.username).toBe('canbo_2fa');
    expect(session.is_2fa_enabled).toBe(true);
    expect(localStorage.getItem('tlbm_access_token')).toBe('final-jwt-access');
    expect(authService.isAuthenticated()).toBe(true);
  });
});
