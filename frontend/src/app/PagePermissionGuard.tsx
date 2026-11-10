import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { usePermissions } from '@lib/permissions';
import { PAGE_VIEW_PERMISSION } from '@lib/navPermissions';
import { pathToPageId } from '@lib/routes';

/**
 * Chặn mở trang bằng URL khi thiếu quyền xem: menu đã ẩn mục tương ứng (`navPermissions`),
 * guard này áp cùng bảng quyền cho đường dẫn gõ trực tiếp, thay vì chỉ ẩn ở menu.
 * Backend vẫn là lớp kiểm quyền thật ở mọi API.
 */
export default function PagePermissionGuard({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const { loaded, can } = usePermissions();
  const required = PAGE_VIEW_PERMISSION[pathToPageId(pathname)];

  if (!required) return <>{children}</>;
  if (!loaded) return null;
  if (!can(required)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
