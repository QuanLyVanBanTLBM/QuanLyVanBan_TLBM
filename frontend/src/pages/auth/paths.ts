import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'login', path: '/login', matches: (pathname) => pathname === '/login' },
] satisfies ModulePage[];
