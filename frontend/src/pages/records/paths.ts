import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'record_types', path: '/records/document-types', matches: (pathname) => pathname === '/records/document-types' || /^\/records\/[^/]+\/document-types$/.test(pathname) },
  { id: 'records', path: '/records', matches: (pathname) => pathname.startsWith('/records') },
] satisfies ModulePage[];
