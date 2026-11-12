import ResourceManagementPage from './ResourceManagementPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/resources', Component: ResourceManagementPage },
] satisfies ModuleRoute[];
