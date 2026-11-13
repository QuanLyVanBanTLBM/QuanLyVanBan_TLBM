import {
  TwoFactorChallenge,
  TwoFactorConfirmResult,
  TwoFactorRegenerateResult,
  TwoFactorSetupPayload,
  TwoFactorStatus,
  UserSession,
} from '@app-types/auth';
import apiClient, { ApiError } from './apiClient';

export interface LoginResponse {
  success: boolean;
  require_2fa?: boolean;
  temp_token?: string;
  method?: 'totp';
  auth_provider?: string;
  verified_via?: string;
  token?: string;
  access?: string;
  refresh?: string;
  user?: {
    id?: number;
    username?: string;
    fullName?: string;
    full_name?: string;
    role?: 'admin' | 'staff';
    roleTitle?: string;
    position?: string;
    department?: string;
    unit?: string;
    email?: string;
    is_2fa_enabled?: boolean;
    has_usable_credential?: boolean;
    [key: string]: unknown;
  };
  error?: string;
  detail?: string;
  message?: string;
}

export class TwoFactorRequiredError extends Error {
  challenge: TwoFactorChallenge;

  constructor(challenge: TwoFactorChallenge) {
    super('2FA verification required');
    this.name = 'TwoFactorRequiredError';
    this.challenge = challenge;
  }
}

function clearStoredSession(): void {
  localStorage.removeItem('tlbm_access_token');
  localStorage.removeItem('tlbm_token');
  localStorage.removeItem('tlbm_refresh_token');
  localStorage.removeItem('tlbm_session');
}

function persistSessionFromAuthResponse(data: LoginResponse, fallbackUsername: string): UserSession {
  if (!data || (!data.access && !data.token)) {
    throw new ApiError(401, {
      error: data?.error || data?.detail || 'Đăng nhập không thành công. Vui lòng thử lại!',
    });
  }

  const accessToken = data.access || data.token || '';
  const refreshToken = data.refresh || '';
  const rawUser = data.user || {};
  const isRoleAdmin = rawUser.role === 'admin';

  const session: UserSession = {
    id: rawUser.id,
    username: rawUser.username || fallbackUsername,
    fullName:
      rawUser.fullName ||
      rawUser.full_name ||
      (isRoleAdmin ? 'Quản Trị Viên (Admin)' : 'Cán Bộ Chuyên Viên'),
    role: isRoleAdmin ? 'admin' : 'staff',
    roleTitle:
      rawUser.roleTitle ||
      rawUser.position ||
      (isRoleAdmin ? 'Quản trị viên tối cao' : 'Cán bộ xử lý văn bản'),
    token: accessToken,
    don_vi_id: (rawUser.don_vi_id ?? rawUser.donViId) as number | undefined,
    donViId: (rawUser.donViId ?? rawUser.don_vi_id) as number | undefined,
    department: (rawUser.department ?? rawUser.unit) as string | undefined,
    unit: (rawUser.unit ?? rawUser.department) as string | undefined,
    is_2fa_enabled: Boolean(rawUser.is_2fa_enabled),
    has_usable_credential:
      rawUser.has_usable_credential === undefined ? true : Boolean(rawUser.has_usable_credential),
  };

  localStorage.setItem('tlbm_access_token', accessToken);
  localStorage.setItem('tlbm_token', accessToken);
  if (refreshToken) {
    localStorage.setItem('tlbm_refresh_token', refreshToken);
  }
  localStorage.setItem('tlbm_session', JSON.stringify(session));
  window.dispatchEvent(new Event('tlbm_auth_changed'));

  return session;
}

function updateStoredTwoFactorFlag(enabled: boolean): void {
  try {
    const raw = localStorage.getItem('tlbm_session');
    if (!raw) return;
    const parsed = JSON.parse(raw) as UserSession;
    parsed.is_2fa_enabled = enabled;
    localStorage.setItem('tlbm_session', JSON.stringify(parsed));
    window.dispatchEvent(new Event('tlbm_auth_changed'));
  } catch {
    // Bỏ qua nếu localStorage session không hợp lệ
  }
}

export const authService = {
  /**
   * Đăng nhập người dùng bằng tài khoản thật từ Backend Django.
   * Nếu tài khoản đã bật 2FA, ném TwoFactorRequiredError để UI chuyển sang bước nhập OTP.
   */
  async login(credentials: { username: string; password: string }): Promise<UserSession> {
    const cleanUsername = credentials.username.trim();
    const payload = {
      username: cleanUsername,
      password: credentials.password,
    };

    // Xóa token cũ trước khi login — tránh apiClient tự động gửi token hết hạn
    // khiến SimpleJWT ném "Given token not valid for any token type" dù endpoint là AllowAny
    clearStoredSession();

    const data = await apiClient.post<LoginResponse>('/api/auth/login/', payload);

    if (data?.require_2fa && data.temp_token) {
      throw new TwoFactorRequiredError({
        tempToken: data.temp_token,
        method: data.method || 'totp',
        authProvider: data.auth_provider || 'local',
        username: cleanUsername,
      });
    }

    return persistSessionFromAuthResponse(data, cleanUsername);
  },

  /**
   * Hoàn tất đăng nhập bước 2 bằng mã TOTP 6 chữ số hoặc Backup Code.
   */
  async verifyTwoFactor(params: {
    tempToken: string;
    code: string;
    username?: string;
  }): Promise<UserSession> {
    const data = await apiClient.post<LoginResponse>('/api/auth/verify-2fa/', {
      temp_token: params.tempToken,
      code: params.code.trim(),
    });
    return persistSessionFromAuthResponse(data, params.username || '');
  },

  async getTwoFactorStatus(): Promise<TwoFactorStatus> {
    return apiClient.get<TwoFactorStatus>('/api/auth/2fa/status/');
  },

  async setupTwoFactor(): Promise<TwoFactorSetupPayload> {
    return apiClient.post<TwoFactorSetupPayload>('/api/auth/2fa/setup/', {});
  },

  async confirmTwoFactor(setupToken: string, code: string): Promise<TwoFactorConfirmResult> {
    const result = await apiClient.post<TwoFactorConfirmResult>('/api/auth/2fa/confirm/', {
      setup_token: setupToken,
      code: code.trim(),
    });
    if (result.enabled) {
      updateStoredTwoFactorFlag(true);
    }
    return result;
  },

  async disableTwoFactor(payload: {
    password?: string;
    code?: string;
  }): Promise<{ success: boolean; enabled: boolean; backup_codes_remaining: number }> {
    const result = await apiClient.post<{
      success: boolean;
      enabled: boolean;
      backup_codes_remaining: number;
    }>('/api/auth/2fa/disable/', payload);
    if (!result.enabled) {
      updateStoredTwoFactorFlag(false);
    }
    return result;
  },

  async regenerateBackupCodes(payload: {
    password?: string;
    code?: string;
  }): Promise<TwoFactorRegenerateResult> {
    return apiClient.post<TwoFactorRegenerateResult>('/api/auth/2fa/backup-codes/regenerate/', payload);
  },

  /**
   * Đăng xuất người dùng thật:
   * - Gửi request tới Backend /api/auth/logout/ để blacklist Refresh Token.
   * - Dọn dẹp sạch toàn bộ token và session trong localStorage.
   */
  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('tlbm_refresh_token');

    try {
      if (refreshToken) {
        await apiClient.post('/api/auth/logout/', { refresh: refreshToken });
      }
    } catch {
      // Dù API có lỗi (ví dụ token đã hết hạn hoặc server offline), vẫn luôn dọn dẹp client
    } finally {
      clearStoredSession();
      window.dispatchEvent(new Event('tlbm_auth_changed'));
    }
  },

  /**
   * Lấy phiên đăng nhập hiện tại từ localStorage
   */
  getSession(): UserSession | null {
    try {
      const sessionStr = localStorage.getItem('tlbm_session');
      return sessionStr ? JSON.parse(sessionStr) : null;
    } catch {
      return null;
    }
  },

  /**
   * Kiểm tra người dùng đã có token hợp lệ hay chưa
   */
  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token'));
  },

  /**
   * Lấy Access Token hiện tại
   */
  getAccessToken(): string | null {
    return localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  },

  /**
   * Lấy Refresh Token hiện tại
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('tlbm_refresh_token');
  },

  /**
   * Xác thực mật khẩu tài khoản hiện tại để mở khóa màn hình hoặc xác nhận bảo mật.
   */
  async verifyPassword(password: string): Promise<boolean> {
    try {
      const data = await apiClient.post<{ success: boolean; valid: boolean }>('/api/auth/verify-password/', {
        password,
      });
      return Boolean(data?.valid ?? data?.success);
    } catch {
      return false;
    }
  },
};

export default authService;
