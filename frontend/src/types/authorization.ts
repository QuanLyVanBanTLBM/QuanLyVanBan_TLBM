export interface Role {
  id: number;
  name: string;
  ma_nhom_quyen?: string | null;
  user_count: number;
  permission_count?: number;
  permission_ids?: number[];
}

export interface RoleFormData {
  name: string;
  permission_ids: number[];
}

export interface Permission {
  id: number;
  name: string;
  codename: string;
  module_ten: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
