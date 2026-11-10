import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeMode } from '@app-types/theme';
import MainLayout from '@layouts/MainLayout';
import type { ModuleRoute } from './moduleRoutes';
import { MODULE_ROUTES } from './moduleRouteTable';

function renderModuleRoute(route: ModuleRoute) {
  const element =
    'redirectTo' in route ? (
      <Navigate to={route.redirectTo} replace />
    ) : (
      <React.Suspense fallback={null}>
        <route.Component />
      </React.Suspense>
    );
  return <Route key={route.path} path={route.path} element={element} />;
}

const isPublicRoute = (route: ModuleRoute) => 'Component' in route && route.public === true;

interface RouterProps {
  currentTheme: ThemeMode;
  onSelectTheme: (theme: ThemeMode) => void;
  onToggleTheme?: () => void;
  preferredLightTheme?: ThemeMode;
  preferredDarkTheme?: ThemeMode;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const checkAuth = () => {
    const hasToken = Boolean(localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token'));
    const hasSession = Boolean(localStorage.getItem('tlbm_session'));
    return hasToken && hasSession;
  };

  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean>(checkAuth);

  React.useEffect(() => {
    const handleAuth = () => {
      setIsAuthenticated(checkAuth());
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
      {/* Route công khai (màn hình Đăng nhập), không qua layout và ProtectedRoute */}
      {MODULE_ROUTES.filter(isPublicRoute).map(renderModuleRoute)}

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
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        {MODULE_ROUTES.filter((route) => !isPublicRoute(route)).map(renderModuleRoute)}

        {/* Fallback cho các đường dẫn chưa đăng ký */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
