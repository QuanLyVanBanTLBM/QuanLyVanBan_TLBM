import ProfilePage from './ProfilePage';
import PasswordChangePage from './PasswordChangePage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/profile', Component: ProfilePage },
  { path: '/password-change', Component: PasswordChangePage },
] satisfies ModuleRoute[];
