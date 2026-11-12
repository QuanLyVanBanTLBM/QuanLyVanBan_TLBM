import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'positions', path: '/positions', matches: (pathname) => pathname.startsWith('/positions') },
] satisfies ModulePage[];
