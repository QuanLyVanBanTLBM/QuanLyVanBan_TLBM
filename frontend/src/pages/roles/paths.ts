import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'roles', path: '/roles', matches: (pathname) => pathname.startsWith('/roles') },
] satisfies ModulePage[];
