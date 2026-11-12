import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'birthdays', path: '/birthdays', matches: (pathname) => pathname.startsWith('/birthdays') },
] satisfies ModulePage[];
