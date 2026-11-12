import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'meetings', path: '/meetings', matches: (pathname) => pathname.startsWith('/meetings') },
] satisfies ModulePage[];
