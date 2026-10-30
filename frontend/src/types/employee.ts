/**
 * Kiểu dữ liệu cho Phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
 * Tác giả: Lê Duy Khánh (leduykhanhdevs).
 */

export type EmployeeStatus = 'LAM_VIEC' | 'NGHI_VIEC';

export interface EmployeeGroup {
  id: number;
  name: string;
}

export interface EmployeeAssignmentItem {
  id?: number;
  don_vi_id: number;
  don_vi_ten?: string;
  khoi_ten?: string;
  chuc_vu_id: number;
  chuc_vu_ten?: string;
  chuc_danh?: string;
}

export interface Employee {
  id: number;
  username: string;
  email: string;
  ho_ten: string;
  ngay_sinh: string | null;
  ngay_sinh_iso?: string | null;
  is_birthday_masked: boolean;
  don_vi_id: number | null;
  don_vi_ten: string;
  khoi_ten: string;
  chuc_vu_id: number | null;
  chuc_vu_ten: string;
  chuc_danh: string | null;
  sdt: string | null;
  trang_thai: EmployeeStatus;
  trang_thai_display: string;
  is_active: boolean;
  is_public: boolean;
  ghi_chu: string | null;
  nhom_quyen: EmployeeGroup[];
  has_sensitive_permission: boolean;
  temporary_password?: string | null;
  assignments?: EmployeeAssignmentItem[];
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: number;
  display_order: number;
  name: string;
  is_public: boolean;
  note: string | null;
}

export interface GroupSimple {
  id: number;
  name: string;
  code?: string;
  ma_nhom_quyen?: string;
}

export interface EmployeeCreatePayload {
  ho_ten: string;
  email: string;
  username?: string;
  password?: string;
  ngay_sinh: string;
  don_vi_id?: number | null;
  chuc_vu_id?: number | null;
  chuc_danh?: string;
  sdt?: string;
  nhom_quyen_ids?: number[];
  trang_thai?: EmployeeStatus;
  is_public?: boolean;
  ghi_chu?: string;
  assignments?: Array<{
    don_vi_id: number;
    chuc_vu_id: number;
    chuc_danh?: string;
  }>;
}

export interface EmployeeUpdatePayload {
  ho_ten?: string;
  email?: string;
  ngay_sinh?: string | null;
  don_vi_id?: number | null;
  chuc_vu_id?: number | null;
  chuc_danh?: string;
  sdt?: string;
  nhom_quyen_ids?: number[];
  trang_thai?: EmployeeStatus;
  is_public?: boolean;
  ghi_chu?: string;
  assignments?: Array<{
    don_vi_id: number;
    chuc_vu_id: number;
    chuc_danh?: string;
  }>;
}

export interface ExcelImportError {
  row: number;
  field?: string;
  code?: string;
  value?: string;
  message: string;
}

export interface ExcelImportResponse {
  success: boolean;
  message: string;
  created_count?: number;
  errors?: ExcelImportError[];
  total_errors?: number;
}

export interface ExcelImportJob {
  job_id: string;
  status: 'queued' | 'processing' | 'done' | 'failed';
  phase: 'queued' | 'validation' | 'saving' | 'complete' | 'failed';
  processed: number;
  total: number;
  created_count: number;
  message: string;
  errors: ExcelImportError[];
}
