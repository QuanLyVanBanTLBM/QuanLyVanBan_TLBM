import SettingsPage from './SettingsPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/settings', Component: SettingsPage },
] satisfies ModuleRoute[];
