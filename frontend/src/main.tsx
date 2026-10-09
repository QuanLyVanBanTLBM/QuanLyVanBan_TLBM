import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './app/App';

const rootElement = document.getElementById('root');
if (rootElement) {
  // Dev helper: auto-inject admin tokens for local testing
  if (import.meta.env.DEV) {
    try {
      // Inject tokens created dynamically by the developer script if available
      const DEV_ACCESS = import.meta.env.VITE_DEV_ACCESS_TOKEN || localStorage.getItem('tlbm_access_token');
      const DEV_REFRESH = import.meta.env.VITE_DEV_REFRESH_TOKEN || localStorage.getItem('tlbm_refresh_token');
      if (DEV_ACCESS) localStorage.setItem('tlbm_access_token', DEV_ACCESS);
      if (DEV_REFRESH) localStorage.setItem('tlbm_refresh_token', DEV_REFRESH);

      // Bảo toàn session nếu người dùng đã đăng nhập hợp lệ, chỉ fallback session admin nếu trống hoặc lỗi '1'
      const rawSession = localStorage.getItem('tlbm_session');
      let isValidSession = false;
      try {
        const parsed = rawSession ? JSON.parse(rawSession) : null;
        if (parsed && typeof parsed === 'object' && (parsed.username || parsed.fullName)) {
          isValidSession = true;
        }
      } catch {
        isValidSession = false;
      }

      const token = DEV_ACCESS || localStorage.getItem('tlbm_access_token');
      if (!isValidSession && token) {
        let matchedUser = {
          username: 'admin',
          fullName: 'Quản Trị Viên (Admin)',
          role: 'admin',
          roleTitle: 'Quản trị viên tối cao',
          email: 'admin@taphuan.gov.vn',
        };
        try {
          const payloadBase64 = token.split('.')[1];
          if (payloadBase64) {
            const decoded = JSON.parse(atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')));
            const uid = String(decoded.user_id || '');
            if (uid === '2') {
              matchedUser = {
                username: 'canbo',
                fullName: 'Tấn Lộc Khiêm Nguyễn',
                role: 'staff',
                roleTitle: 'Cán bộ nhân viên',
                email: 'canbo@taphuan.gov.vn',
              };
            } else if (uid === '3') {
              matchedUser = {
                username: 'canbo2',
                fullName: 'Lê Cán Bộ 2',
                role: 'staff',
                roleTitle: 'Cán bộ nhân viên',
                email: 'canbo2@taphuan.gov.vn',
              };
            }
          }
        } catch {
          // ignore
        }
        localStorage.setItem('tlbm_session', JSON.stringify(matchedUser));
      }
      window.dispatchEvent(new Event('tlbm_auth_changed'));
    } catch {
      // ignore
    }
  }
  createRoot(rootElement).render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>
  );
}

