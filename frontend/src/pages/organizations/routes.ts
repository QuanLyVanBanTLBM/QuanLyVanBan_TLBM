import OrganizationsPage from './OrganizationsPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/organizations', Component: OrganizationsPage },
] satisfies ModuleRoute[];
