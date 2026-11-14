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
  is_2fa_enabled?: boolean;
  has_usable_credential?: boolean;
}

export interface TwoFactorChallenge {
  tempToken: string;
  method: 'totp';
  authProvider: string;
  username: string;
}

export interface TwoFactorStatus {
  enabled: boolean;
  backup_codes_remaining: number;
  has_usable_credential: boolean;
}

export interface TwoFactorSetupPayload {
  secret_key: string;
  otpauth_uri: string;
  qr_code: string;
  setup_token: string;
  expires_in: number;
}

export interface TwoFactorConfirmResult {
  success: boolean;
  enabled: boolean;
  backup_codes: string[];
  backup_codes_remaining: number;
}

export interface TwoFactorRegenerateResult {
  success: boolean;
  backup_codes: string[];
  backup_codes_remaining: number;
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
