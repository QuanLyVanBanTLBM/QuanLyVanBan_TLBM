/**
 * TypeScript types for Organization & Department Management (Module 7.3 - Nhóm 7).
 * Author: Lê Duy Khánh.
 */

export interface KhoiKhuVuc {
  id: number;
  ten: string;
  thu_tu_hien_thi: number;
  don_vi_count?: number;
  created_at: string;
  updated_at: string;
}

export interface DonVi {
  id: number;
  khoi_id: number;
  khoi_ten: string;
  stt_uu_tien: number;
  ten: string;
  dia_chi: string;
  dien_thoai: string;
  email: string;
  is_public: boolean;
  ghi_chu: string;
  created_at: string;
  updated_at: string;
}

export interface DonViPaginationResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: DonVi[];
}

export interface CreateKhoiPayload {
  ten: string;
  thu_tu_hien_thi?: number;
}

export interface CreateDonViPayload {
  khoi_id: number;
  ten: string;
  stt_uu_tien?: number | null;
  dia_chi?: string;
  dien_thoai?: string;
  email?: string;
  is_public?: boolean;
  ghi_chu?: string;
}
