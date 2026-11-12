import type { ModulePage } from '@app/moduleRoutes';

export default [
  { id: 'ai_assistant', path: '/ai-assistant', matches: (pathname) => pathname === '/ai-assistant' },
] satisfies ModulePage[];
