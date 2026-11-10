import InboundDocumentPage from '../InboundDocumentPage';
import OutboundDocumentPage from '../OutboundDocumentPage';
import ConfidentialDocumentPage from '../ConfidentialDocumentPage';
import type { ModuleRoute } from '@app/moduleRoutes';

export default [
  { path: '/documents/incoming', Component: InboundDocumentPage },
  { path: '/documents/outgoing', Component: OutboundDocumentPage },
  { path: '/documents/confidential', Component: ConfidentialDocumentPage },
] satisfies ModuleRoute[];
