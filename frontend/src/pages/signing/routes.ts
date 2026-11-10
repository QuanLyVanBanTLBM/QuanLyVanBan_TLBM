import { lazy } from 'react';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  // Tải lười để tách phân hệ Trình ký khỏi bundle chính
  { path: '/approvals/*', Component: lazy(() => import('./SigningModule')) },
] satisfies ModuleRoute[];
