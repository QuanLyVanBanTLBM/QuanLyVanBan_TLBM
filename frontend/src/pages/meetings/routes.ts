import MeetingsPage from './MeetingsPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/meetings', Component: MeetingsPage },
] satisfies ModuleRoute[];
