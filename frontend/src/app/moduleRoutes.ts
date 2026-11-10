import type { ComponentType } from 'react';
import type { ActivePageId } from '@app-types/navigation';

/**
 * Trang của module, khai báo trong `<module>/paths.ts`: page id dùng cho menu và tiêu đề,
 * đường dẫn mở trang, điều kiện nhận diện page id từ URL (đã bỏ dấu `/` cuối).
 * Điều kiện của các module không được trùng nhau; trong một module, trang khai báo trước được xét trước.
 */
export interface ModulePage {
  id: ActivePageId;
  path: string;
  matches: (pathname: string) => boolean;
}

/**
 * Route React Router của module, khai báo trong `<module>/routes.ts`.
 * `redirectTo` thay cho `Component` khi route chỉ chuyển hướng; `public` đặt route ngoài layout và ngoài ProtectedRoute.
 */
export type ModuleRoute =
  | { path: string; Component: ComponentType; public?: boolean }
  | { path: string; redirectTo: string };
