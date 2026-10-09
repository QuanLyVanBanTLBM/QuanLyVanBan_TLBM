export type HieuLucType = 'CON_HIEU_LUC' | 'CON_HIEU_LUC_1_PHAN' | 'HET_HIEU_LUC' | 'HET_VA_THAY_THE';
export type HienThiType = 'TAT_CA' | 'NOI_BO_PHONG_BAN';

export interface ResourceItem {
  id: number;
  dm_tai_lieu: number;
  dm_tai_lieu_name?: string;
  loai_tai_lieu: number[];
  loai_tai_lieu_names?: string[];
  ky_hieu?: string;
  tieu_de: string;
  ngay_dang: string;
  noi_ban_hanh?: string;
  hieu_luc: HieuLucType;
  ngay_het_hieu_luc?: string;
  link_thay_the?: string;
  ghi_chu?: string;
  file_dinh_kem: string;
  hien_thi: HienThiType;
  don_vi_id?: number;
  nguoi_tao_name?: string;
  attachments?: ResourceAttachment[];
}

export interface ResourceAttachment {
  id?: number;
  name: string;
  path?: string;
  file_size?: number;
  mime_type?: string;
}

export interface ResourceCategory {
  id: number;
  stt_uu_tien: number;
  ky_hieu?: string;
  ten_tai_lieu: string;
  ghi_chu?: string;
  ngay_lap?: string;
  nguoi_lap_name?: string;
}

export interface ResourceType {
  id: number;
  dm_tai_lieu: number;
  ten_loai: string;
  is_public: boolean;
  ghi_chu?: string;
  ngay_lap?: string;
}

export interface ResourceFilterState {
  dm_tai_lieu?: number;
  loai_tai_lieu?: number;
  hieu_luc?: HieuLucType;
  nam?: number;
  don_vi_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface ResourcePaginationResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ResourceItem[];
}
