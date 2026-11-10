import EmployeesPage from './EmployeesPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/employees', Component: EmployeesPage },
] satisfies ModuleRoute[];
