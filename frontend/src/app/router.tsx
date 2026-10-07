import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeMode } from '@app-types/theme';
import MainLayout from '@layouts/MainLayout';
import DashboardPage from '@pages/dashboard/DashboardPage';
import LoginPage from '@pages/auth/LoginPage';
import AiAssistantPage from '@pages/ai/AiAssistantPage';
import ProfilePage from '@pages/profile/ProfilePage';
import PasswordChangePage from '@pages/profile/PasswordChangePage';
import SettingsPage from '@pages/settings/SettingsPage';
import SyllabusPreview from '@components/common/SyllabusPreview';

interface RouterProps {
  currentTheme: ThemeMode;
  onSelectTheme: (theme: ThemeMode) => void;
  onToggleTheme?: () => void;
  preferredLightTheme?: ThemeMode;
  preferredDarkTheme?: ThemeMode;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean>(() => {
    return Boolean(localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token'));
  });

  React.useEffect(() => {
    const handleAuth = () => {
      setIsAuthenticated(Boolean(localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token')));
    };
    window.addEventListener('tlbm_auth_changed', handleAuth);
    window.addEventListener('storage', handleAuth);
    return () => {
      window.removeEventListener('tlbm_auth_changed', handleAuth);
      window.removeEventListener('storage', handleAuth);
    };
  }, []);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function AppRouter({
  currentTheme,
  onSelectTheme,
  onToggleTheme,
  preferredLightTheme = 'light',
  preferredDarkTheme = 'dark',
}: RouterProps) {
  return (
    <Routes>
      {/* Route Standalone: Màn hình Đăng Nhập */}
      <Route path="/login" element={<LoginPage />} />

      {/* Routes có Layout chung (được bảo vệ bởi ProtectedRoute - yêu cầu đăng nhập trước) */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout
              currentTheme={currentTheme}
              onSelectTheme={onSelectTheme}
              onToggleTheme={onToggleTheme}
              preferredLightTheme={preferredLightTheme}
              preferredDarkTheme={preferredDarkTheme}
            />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/ai-assistant" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />

        {/* Phân hệ Văn bản (Nhóm 2 phụ trách theo đề cương) */}
        <Route path="/documents/incoming" element={<SyllabusPreview activePage="documents_incoming" />} />
        <Route path="/documents/outgoing" element={<SyllabusPreview activePage="documents_outgoing" />} />
        <Route path="/documents/confidential" element={<SyllabusPreview activePage="documents_confidential" />} />

        {/* Phân hệ Hồ sơ & Tài nguyên (Nhóm 3 & Nhóm 4 phụ trách theo đề cương) */}
        <Route path="/records" element={<SyllabusPreview activePage="records" />} />
        <Route path="/resources" element={<SyllabusPreview activePage="resources" />} />

        {/* Phân hệ Quy trình & Điều hành (Nhóm 5 & Nhóm 6 phụ trách theo đề cương) */}
        <Route path="/approvals" element={<SyllabusPreview activePage="approvals" />} />
        <Route path="/tasks" element={<SyllabusPreview activePage="tasks" />} />
        <Route path="/meetings" element={<SyllabusPreview activePage="meetings" />} />
        <Route path="/birthdays" element={<SyllabusPreview activePage="birthdays" />} />

        {/* Phân hệ Quản trị hệ thống & Nhân sự (Nhóm 7 & Nhóm 8 phụ trách theo đề cương) */}
        <Route path="/organizations" element={<SyllabusPreview activePage="organizations" />} />
        <Route path="/employees" element={<SyllabusPreview activePage="employees" />} />
        <Route path="/positions" element={<SyllabusPreview activePage="positions" />} />
        <Route path="/roles" element={<SyllabusPreview activePage="roles" />} />

        {/* Tiện ích Cá nhân & Trợ lý AI (Nhóm 1 phụ trách) */}
        <Route path="/ai-assistant" element={<AiAssistantPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/password-change" element={<PasswordChangePage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Fallback cho các đường dẫn chưa đăng ký */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}


