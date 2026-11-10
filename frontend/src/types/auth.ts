export type AuthRole = 'admin' | 'staff';

export interface UserSession {
  id?: number;
  username: string;
  fullName: string;
  role: AuthRole;
  roleTitle: string;
  avatar?: string;
  token?: string;
  don_vi_id?: number;
  donViId?: number;
  department?: string;
  unit?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface QuickLoginProfile {
  role: AuthRole;
  label: string;
  username: string;
  password: string;
  subtitle: string;
}
