/**
 * Types & Interfaces cho Phân hệ Quản lý Văn bản (Module 02_Documents).
 * Đồng bộ 100% với Django Serializers:
 * - DocumentListSerializer
 * - DocumentDetailSerializer
 * - DocumentAttachmentSerializer
 * - DocumentViewLogSerializer
 */

export type DocumentType = 'DEN' | 'DI' | 'MAT';

export type DocumentStatus = 'CON_HIEU_LUC' | 'CON_HIEU_LUC_1_PHAN' | 'HET_HIEU_LUC' | 'HET_VA_THAY_THE';

/**
 * File đính kèm văn bản (PDF, Word, Ảnh).
 */
export interface DocumentAttachment {
  id: number;
  file: string;
  file_name: string;
  file_size: number;
  uploaded_at: string;
}

/**
 * Cán bộ nhận văn bản (nguoi_nhan).
 */
export interface DocumentRecipient {
  id: number;
  username: string;
  full_name: string;
}

/**
 * Thông tin văn bản hiển thị trên bảng danh sách (GET /api/documents/).
 * Khớp 100% với DocumentListSerializer.
 */
export interface DocumentItem {
  id: number;
  loai: DocumentType;
  loai_display: string;
  nam: number;
  so_hieu: string;
  so_thu_tu?: number | null;
  ngay_den?: string | null;
  ngay_ban_hanh?: string | null;
  ngay_van_ban?: string | null;
  trich_yeu: string;
  noi_ban_hanh?: string;
  nguoi_ky?: string;
  hieu_luc: DocumentStatus;
  hieu_luc_display: string;
  ngay_het_hieu_luc?: string | null;
  link_thay_the?: string;
  danh_sach_thay_the?: string[];
  thay_the_cho?: string[];
  bi_thay_boi?: string[];
  hien_thi: boolean;
  pham_vi?: 'NOI_BO' | 'HAN_CHE';
  pham_vi_display?: string;
  nguoi_tao_name?: string | null;
  nguoi_tao_username?: string | null;
  can_edit?: boolean;
  can_delete?: boolean;
  attachment_count: number;
  created_at: string;
}

/**
 * Thông tin chi tiết đầy đủ của văn bản (GET /api/documents/{id}/).
 * Kế thừa DocumentItem và bổ sung các trường nâng cao khớp với DocumentDetailSerializer.
 */
export interface DocumentDetail extends DocumentItem {
  chuc_vu?: string;
  ngay_het_hieu_luc?: string | null;
  link_thay_the?: string;
  ghi_chu?: string;
  gui_mail_toan_he_thong: boolean;
  attachments: DocumentAttachment[];
  nguoi_nhan_list?: DocumentRecipient[];
  updated_at: string;
}

/**
 * Lịch sử người đã xem văn bản (GET /api/documents/{id}/viewers/).
 * Khớp với DocumentViewLogSerializer.
 */
export interface DocumentViewer {
  id: number;
  user_id: number;
  username: string;
  full_name: string;
  chuc_danh?: string;
  don_vi?: string;
  viewed_at: string;
}

/**
 * Các tham số lọc danh sách văn bản (query params cho API).
 * Khớp với DocumentFilter trong Django.
 */
export interface DocumentFilterParams {
  q?: string;
  nam?: number | string;
  tu_ngay?: string;
  den_ngay?: string;
  hieu_luc?: DocumentStatus | 'HIEU_LUC' | '';
  page?: number;
  page_size?: number;
  loai?: DocumentType;
  loai_van_ban?: string | number;
}

/**
 * Cấu trúc phân trang chuẩn từ Django REST Framework.
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
