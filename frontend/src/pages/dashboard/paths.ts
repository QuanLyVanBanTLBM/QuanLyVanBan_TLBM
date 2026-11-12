import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'dashboard', path: '/dashboard', matches: (pathname) => pathname === '/dashboard' },
] satisfies ModulePage[];
