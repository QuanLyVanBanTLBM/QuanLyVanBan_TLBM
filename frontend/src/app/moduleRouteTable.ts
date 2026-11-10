import type { ModuleRoute } from './moduleRoutes';

// Mỗi module khai báo route của mình trong `routes.ts` (pages/<module>/routes.ts, modules/<module>/routes.ts).
export const MODULE_ROUTES: ModuleRoute[] = Object.values(
  import.meta.glob<ModuleRoute[]>(['../pages/*/routes.ts', '../modules/*/routes.ts'], { eager: true, import: 'default' })
).flat();
