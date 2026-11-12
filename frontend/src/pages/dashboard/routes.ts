import DashboardPage from './DashboardPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/dashboard', Component: DashboardPage },
] satisfies ModuleRoute[];
