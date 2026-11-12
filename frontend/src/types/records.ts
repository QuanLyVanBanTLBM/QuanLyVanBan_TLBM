export type EntityId = number | string;

export interface Dossier {
  id: EntityId;
  stt_uu_tien?: number | null;
  so_ky_hieu: string;
  ten_ho_so: string;
  nguoi_lap?: string | { id?: EntityId; full_name?: string; ho_ten?: string; username?: string } | null;
  ngay_lap?: string | null;
  ghi_chu?: string | null;
  is_he_thong?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DossierPayload {
  stt_uu_tien: number | null;
  so_ky_hieu: string;
  ten_ho_so: string;
  ngay_lap: string | null;
  ghi_chu: string;
}

export interface DocumentType {
  id: EntityId;
  ho_so?: EntityId | Dossier;
  ten_loai: string;
  ten_ho_so?: string;
  ngay_lap?: string | null;
  ghi_chu?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentTypePayload {
  ten_loai: string;
  ngay_lap: string | null;
  ghi_chu: string;
}

export interface PageResult<T> {
  items: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

export interface ListQuery {
  search?: string;
  year?: string;
  page?: number;
  pageSize?: number;
}
