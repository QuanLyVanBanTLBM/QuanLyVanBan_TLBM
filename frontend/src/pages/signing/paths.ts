import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'approvals', path: '/approvals', matches: (pathname) => pathname.startsWith('/approvals') },
] satisfies ModulePage[];
