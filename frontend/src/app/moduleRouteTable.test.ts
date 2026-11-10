import { describe, expect, it } from 'vitest';
import { MODULE_ROUTES } from './moduleRouteTable';

describe('module route table', () => {
  it('registers every application route exactly once', () => {
    const paths = MODULE_ROUTES.map((route) => route.path).sort();
    expect(paths).toEqual(
      [
        '/login',
        '/dashboard',
        '/documents/incoming',
        '/documents/outgoing',
        '/documents/confidential',
        '/records',
        '/records/:dossierId/document-types',
        '/records/document-types',
        '/records/:dossierId/documents',
        '/resources',
        '/approvals/*',
        '/tasks',
        '/meetings',
        '/birthdays',
        '/organizations',
        '/employees',
        '/positions',
        '/roles',
        '/ai-assistant',
        '/profile',
        '/password-change',
        '/settings',
      ].sort()
    );
  });

  it('keeps only the login screen outside the protected layout', () => {
    const publicPaths = MODULE_ROUTES.filter((route) => 'Component' in route && route.public).map((route) => route.path);
    expect(publicPaths).toEqual(['/login']);
  });

  it('keeps the legacy dossier documents path as a redirect', () => {
    expect(MODULE_ROUTES.find((route) => route.path === '/records/:dossierId/documents')).toEqual({
      path: '/records/:dossierId/documents',
      redirectTo: '/records/document-types',
    });
  });
});
