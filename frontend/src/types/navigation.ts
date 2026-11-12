export type ActivePageId =
  | 'dashboard'
  | 'login'
  | 'profile'
  | 'password_change'
  | 'settings'
  | 'documents_incoming'
  | 'documents_outgoing'
  | 'documents_confidential'
  | 'records'
  | 'record_types'
  | 'resources'
  | 'approvals'
  | 'tasks'
  | 'meetings'
  | 'birthdays'
  | 'organizations'
  | 'employees'
  | 'positions'
  | 'roles'
  | 'ai_assistant';

export interface NavItem {
  id: ActivePageId;
  label: string;
  icon: string;
  badge?: string | number;
  badgeColor?: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple';
}

export interface NavGroup {
  id: string;
  groupTitle: string;
  teamTag?: string; // Nhóm 1, Nhóm 2, etc.
  items: NavItem[];
}

// ==========================================
// CẤU TRÚC ĐIỀU HƯỚNG 2 TẦNG (TWO-TIER NAVIGATION)
// Tầng 1: Sidebar dọc (6 Module lớn)
// Tầng 2: Thanh Tab ngang phụ ở đỉnh (Các trang con tương ứng)
// ==========================================
export type MainModuleId =
  | 'dashboard'
  | 'documents'
  | 'records_resources'
  | 'workflow'
  | 'system'
  | 'ai';

export interface SubNavItem {
  id: ActivePageId;
  label: string;
  icon: string;
  badge?: string | number;
  badgeColor?: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple';
  description?: string;
}

export interface MainModule {
  id: MainModuleId;
  label: string;
  shortLabel: string;
  icon: string;
  teamTag: string;
  defaultPage: ActivePageId;
  subItems: SubNavItem[];
}

