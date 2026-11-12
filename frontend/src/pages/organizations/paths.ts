import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'organizations', path: '/organizations', matches: (pathname) => pathname.startsWith('/organizations') },
] satisfies ModulePage[];
