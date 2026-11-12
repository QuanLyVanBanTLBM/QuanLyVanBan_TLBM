import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'documents_incoming', path: '/documents/incoming', matches: (pathname) => pathname.startsWith('/documents/incoming') },
  { id: 'documents_outgoing', path: '/documents/outgoing', matches: (pathname) => pathname.startsWith('/documents/outgoing') },
  { id: 'documents_confidential', path: '/documents/confidential', matches: (pathname) => pathname.startsWith('/documents/confidential') },
] satisfies ModulePage[];
