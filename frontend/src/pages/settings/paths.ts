import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'settings', path: '/settings', matches: (pathname) => pathname === '/settings' },
] satisfies ModulePage[];
