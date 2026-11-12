import DossiersPage from './DossiersPage';
import DocumentTypesPage from './DocumentTypesPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/records', Component: DossiersPage },
  { path: '/records/:dossierId/document-types', Component: DocumentTypesPage },
  { path: '/records/document-types', Component: DocumentTypesPage },
  { path: '/records/:dossierId/documents', redirectTo: '/records/document-types' },
] satisfies ModuleRoute[];
