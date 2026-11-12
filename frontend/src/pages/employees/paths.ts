import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'employees', path: '/employees', matches: (pathname) => pathname.startsWith('/employees') },
] satisfies ModulePage[];
