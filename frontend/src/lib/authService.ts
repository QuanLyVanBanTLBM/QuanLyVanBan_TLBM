import { UserSession } from '@app-types/auth';
import apiClient, { ApiError } from './apiClient';

export interface LoginResponse {
  success: boolean;
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
    [key: string]: unknown;
  };
  error?: string;
  detail?: string;
  message?: string;
}

export const authService = {
  /**
   * Đăng nhập người dùng bằng tài khoản thật từ Backend Django.
   * Cấp Access Token + Refresh Token và lưu Session.
   */
  async login(credentials: { username: string; password: string }): Promise<UserSession> {
    const payload = {
      username: credentials.username.trim(),
      password: credentials.password,
    };

    const data = await apiClient.post<LoginResponse>('/api/auth/login/', payload);

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
      username: rawUser.username || credentials.username.trim(),
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
    };

    // Lưu trữ token và session
    localStorage.setItem('tlbm_access_token', accessToken);
    localStorage.setItem('tlbm_token', accessToken);
    if (refreshToken) {
      localStorage.setItem('tlbm_refresh_token', refreshToken);
    }
    localStorage.setItem('tlbm_session', JSON.stringify(session));

    // Thông báo cho toàn ứng dụng cập nhật trạng thái auth
    window.dispatchEvent(new Event('tlbm_auth_changed'));

    return session;
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
      localStorage.removeItem('tlbm_access_token');
      localStorage.removeItem('tlbm_token');
      localStorage.removeItem('tlbm_refresh_token');
      localStorage.removeItem('tlbm_session');
      window.dispatchEvent(new Event('tlbm_auth_changed'));
    }
  },

  /**
   * Lấy phiên đăng nhập hiện tại từ localStorage
   */
  getSession(): UserSession | null {
    try {
      const sessionStr = localStorage.getItem('tlbm_session');
      if (!sessionStr) return null;
      const parsed = JSON.parse(sessionStr);
      if (parsed && typeof parsed === 'object' && (parsed.username || parsed.fullName)) {
        return parsed;
      }
      return null;
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
   * Kiểm tra người dùng hiện tại có vai trò Quản trị viên (Admin) hay không
   */
  isAdmin(): boolean {
    const session = this.getSession();
    if (session?.role === 'admin' || session?.username === 'admin') {
      return true;
    }
    const token = this.getAccessToken();
    if (token) {
      try {
        const payloadBase64 = token.split('.')[1];
        if (payloadBase64) {
          const decoded = JSON.parse(atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')));
          return decoded.user_id === '1' || decoded.user_id === 1;
        }
      } catch {
        // ignore
      }
    }
    return false;
  },
};

export default authService;
