import BirthdayPage from './BirthdayPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/birthdays', Component: BirthdayPage },
] satisfies ModuleRoute[];
