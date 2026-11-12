import LoginPage from './LoginPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/login', Component: LoginPage, public: true },
] satisfies ModuleRoute[];
