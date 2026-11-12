import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'resources', path: '/resources', matches: (pathname) => pathname.startsWith('/resources') },
] satisfies ModulePage[];
