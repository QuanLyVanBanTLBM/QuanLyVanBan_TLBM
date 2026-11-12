import TasksPage from './pages/TasksPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/tasks', Component: TasksPage },
] satisfies ModuleRoute[];
