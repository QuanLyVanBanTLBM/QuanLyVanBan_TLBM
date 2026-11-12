import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'profile', path: '/profile', matches: (pathname) => pathname === '/profile' },
  { id: 'password_change', path: '/password-change', matches: (pathname) => pathname === '/password-change' },
] satisfies ModulePage[];
