import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'tasks', path: '/tasks', matches: (pathname) => pathname.startsWith('/tasks') },
] satisfies ModulePage[];
