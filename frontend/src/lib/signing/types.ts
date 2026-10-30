/**
 * Kiểu dữ liệu API Trình ký (Nhóm 5) — khớp backend `apps/signing` (/api/v1/signing/).
 */

export type TrangThaiHoSo = 'NHAP' | 'CHO_KY' | 'HOAN_THANH' | 'TU_CHOI' | 'HUY';
export type TrangThaiLuot = 'CHO_KY' | 'YEU_CAU_SUA' | 'HOAN_THANH' | 'TU_CHOI' | 'HUY';
export type TrangThaiCap = 'CHUA_MO' | 'DANG_KY' | 'TAM_DUNG' | 'HOAN_THANH';
export type TrangThaiNguoiKy = 'CHO_KY' | 'DA_KY' | 'TU_CHOI' | 'YEU_CAU_SUA';
export type TrangThaiTepHoanTat = 'DANG_XU_LY' | 'LOI' | 'THANH_CONG' | null;
export type VaiTroKy = 'KY_CHINH';
export type PhamViQuyTrinh = 'CONG_TY' | 'PHONG_BAN';

export interface NguoiDungHienTai {
  id: number;
  ten: string;
  don_vi_id: number | null;
  quyen: Record<string, boolean>;
  la_quan_tri: boolean;
  la_lanh_dao_don_vi: boolean;
}

/** Khung ký: tỷ lệ % theo trang, gốc góc trên-trái. Số thập phân dạng chuỗi. */
export interface ViTriKy {
  trang_ky: number;
  toa_do_x: string;
  toa_do_y: string;
  chieu_rong_khung: string;
  chieu_cao_khung: string;
}

export interface NguoiKyCauHinh {
  id: number;
  nguoi_ky: number | null;
  ten_nguoi_ky: string | null;
  chuc_vu_id: number | null;
  /** Tên chức vụ theo Danh mục chức vụ (CBNV) khi cấu hình theo chức vụ */
  ten_chuc_vu: string | null;
  pham_vi_chuc_vu: string | null;
  vai_tro_ky: VaiTroKy;
  thu_tu: number;
}

export interface CapKyQuyTrinh {
  id: number;
  cap_ky: number;
  ten_cap_ky: string;
  thu_tu: number;
  don_vi_id: number | null;
  so_gio_xu_ly: number | null;
  nguoi_ky: NguoiKyCauHinh[];
}

export interface QuyTrinh {
  id: number;
  ma_quy_trinh: string;
  ten_quy_trinh: string;
  mo_ta: string;
  phien_ban: number;
  trang_thai: 'NHAP' | 'HOAT_DONG' | 'NGUNG';
  pham_vi: PhamViQuyTrinh;
  don_vi_ap_dung_id: number | null;
  ten_don_vi_ap_dung: string | null;
  cap_ky: CapKyQuyTrinh[];
  /** Số hồ sơ trình ký (mọi trạng thái) dùng phiên bản này; khác 0 thì không xóa được */
  so_ho_so: number;
}

export interface ChuKyTomTat {
  id: number;
  ngay_ky: string;
  ghi_chu_ky: string;
  ky_tre_han: boolean;
  so_giay_tre: number | null;
  trang_thai_xac_minh: string;
  co_anh_chu_ky: boolean;
}

export interface NguoiKyLuot {
  id: number;
  nguoi_ky: number;
  ten_nguoi_ky: string;
  ten_chuc_vu: string | null;
  vai_tro_ky: VaiTroKy;
  trang_thai: TrangThaiNguoiKy;
  /** Backend policy projection for the current user; missing means not eligible. */
  thoi_diem_mo: string | null;
  ngay_ky: string | null;
  ngay_tu_choi: string | null;
  ly_do_tu_choi: string;
  trang_ky: number | null;
  toa_do_x: string | null;
  toa_do_y: string | null;
  chieu_rong_khung: string | null;
  chieu_cao_khung: string | null;
  chu_ky: ChuKyTomTat | null;
}

export interface CapLuot {
  id: number;
  cap_ky: number;
  ten_cap_ky: string;
  thu_tu: number;
  trang_thai: TrangThaiCap;
  han_xu_ly: string | null;
  thoi_diem_mo: string | null;
  thoi_diem_hoan_thanh: string | null;
  nguoi_ky: NguoiKyLuot[];
}

export interface YeuCauSuaThread {
  id: number;
  nguoi_yeu_cau: number;
  tieu_de: string;
  ly_do: string;
  trang_thai: 'DANG_MO' | 'DA_GIAI_QUYET';
  created_at: string;
  thoi_diem_giai_quyet: string | null;
}

export interface LuotTrinh {
  id: number;
  so_luot: number;
  luot_truoc: number | null;
  phien_ban_van_ban: string;
  ma_bam_tai_lieu: string;
  trang_thai: TrangThaiLuot;
  ly_do: string;
  thoi_diem_gui: string | null;
  thoi_diem_hoan_thanh: string | null;
  trang_thai_tep_hoan_tat: TrangThaiTepHoanTat;
  loi_tep_hoan_tat: string;
  ma_bam_tep_hoan_tat: string;
  ma_bam_bang_chung: string | null;
  cap_ky: CapLuot[];
  yeu_cau_sua: YeuCauSuaThread[];
}

export interface NhatKy {
  id: number;
  hanh_dong: string;
  nguoi_thuc_hien: number;
  ten_nguoi_thuc_hien: string;
  trang_thai_truoc: string;
  trang_thai_sau: string;
  chi_tiet: string;
  luot_trinh: number | null;
  created_at: string;
}

export interface DangCho {
  id: number;
  nguoi_ky: number;
  ten_nguoi_ky: string;
  vai_tro_ky: VaiTroKy;
}

export interface HoSo {
  id: number;
  /** Văn bản trình ký: văn bản đi đã đăng ký hoặc PDF dự thảo chưa vào sổ; sau duyệt có thể được liên kết. */
  document_type: string | null;
  van_ban_id: number | null;
  so_hieu_van_ban: string;
  trich_yeu_van_ban: string;
  van_ban: { so_hieu?: string; trich_yeu?: string };
  quy_trinh: number;
  ma_quy_trinh: string;
  ten_quy_trinh: string;
  phien_ban_quy_trinh: number;
  trang_thai: TrangThaiHoSo;
  han_chot: string | null;
  ngay_gui: string | null;
  ngay_hoan_thanh: string | null;
  ly_do_tu_choi: string;
  ly_do_huy: string;
  ghi_chu: string;
  ho_so_goc: number | null;
  phien_ban_van_ban: string;
  ma_bam_tai_lieu: string;
  create_by: number;
  ten_nguoi_tao: string;
  created_at: string;
  dang_cho: DangCho[];
  /** Trạng thái lượt trình hiện hành (YEU_CAU_SUA: đang trả lại để sửa) */
  trang_thai_luot: TrangThaiLuot | null;
  qua_han: boolean;
  qua_han_cap?: boolean;
  han_xu_ly_cap?: string | null;
}

/** Một trang danh sách (phân trang DRF: `page`, `page_size`). */
export interface TrangKetQua<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface HoSoChiTiet extends HoSo {
  luot_trinh: LuotTrinh[];
  lich_su: NhatKy[];
}

export interface TinNhan {
  id: number;
  nguoi_viet: number;
  ten_nguoi_viet?: string;
  noi_dung: string;
  created_at: string;
}

export interface TraoDoi {
  thread: YeuCauSuaThread | null;
  tin_nhan: TinNhan[];
}

export interface KhoaKy {
  id: number;
  ma_khoa: string;
  dau_van_tay: string;
  thuat_toan: string;
  khoa_cong_khai: string;
  trang_thai: 'CHO_KICH_HOAT' | 'HOAT_DONG' | 'DA_XOAY_VONG' | 'THU_HOI' | 'HET_HAN';
  thoi_diem_xac_minh_so_huu: string | null;
  thoi_diem_kich_hoat: string | null;
  ngay_hieu_luc: string;
  created_at: string;
  da_dat_pin: boolean;
}

export interface ThamSoKdf {
  thuat_toan: 'argon2id';
  m: number;
  t: number;
  p: number;
  phien_ban: number;
  salt: string;
}

export interface BangChung {
  luot_trinh: number;
  ma_bam_bang_chung: string;
  thoi_diem_chot: string;
  xac_minh: {
    hop_le: boolean;
    ma_bam_bang_chung_khop: boolean;
    tep_goc_khop: boolean | null;
    tep_hoan_tat_khop: boolean | null;
    chu_ky: Array<{ ten_nguoi_ky: string; hop_le: boolean; anh_chu_ky_khop: boolean | null }>;
  };
}

export interface VanBanDi {
  id: number;
  so_hieu: string;
  trich_yeu: string;
  attachments?: VanBanDiTepDinhKem[];
}

export interface VanBanDiTepDinhKem {
  id: number;
  name: string;
  file: string | null;
  file_size: number;
  is_deleted: boolean;
}

/** Bộ lọc trạng thái của danh sách hồ sơ (server: tham số `nhanh`): đang chờ ký, quá hạn, đã ký xong, trả lại để sửa. */
export type LocNhanh = 'cho_ky' | 'qua_han' | 'hoan_thanh' | 'tra_lai';

/** Số hồ sơ theo từng thẻ lọc nhanh của hộp (`GET /trinh-ky/thong-ke/`). */
export type ThongKeHoSo = Record<LocNhanh | 'tat_ca', number>;

/** Bộ lọc danh sách hồ sơ (server kiểm tham số; ngày dạng YYYY-MM-DD). */
export interface BoLocHoSo {
  nhanh?: LocNhanh | '';
  trang_thai?: string;
  quy_trinh?: string;
  q?: string;
  tu_ngay?: string;
  den_ngay?: string;
}

export type LoaiTepTaiLieu = 'DU_THAO' | 'LUOT' | 'HOAN_TAT';

/** Một tệp trên trang tài liệu (`GET /tai-lieu/`). */
export interface TepTaiLieu {
  trinh_ky: number;
  trang_thai_ho_so: TrangThaiHoSo;
  ten_quy_trinh: string;
  van_ban: { so_hieu?: string; trich_yeu?: string };
  loai: LoaiTepTaiLieu;
  luot: number | null;
  so_luot: number | null;
  phien_ban: string | null;
  ma_bam: string;
  thoi_diem: string;
  ten_tep: string;
}

export interface BoLocTaiLieu {
  q?: string;
  loai?: LoaiTepTaiLieu | '';
  tu_ngay?: string;
  den_ngay?: string;
}

/** Đơn vị chọn được làm đơn vị áp dụng quy trình PHONG_BAN (Đơn vị của Nhóm 7). */
export interface DonViLuaChon {
  id: number;
  ten: string;
}

/** Chức vụ trong Danh mục chức vụ của phân hệ CBNV (`GET /api/positions/?all=true`). */
export interface ChucVu {
  id: number;
  name: string;
  display_order: number;
}

/** Cán bộ đang giữ một chức vụ (`GET /can-bo-theo-chuc-vu/`), để hiện tên người khớp người ký theo chức vụ. */
export interface CanBoChucVu {
  id: number;
  ten: string;
  chuc_vu: string | null;
  don_vi_id: number | null;
  don_vi: string | null;
}

/** Cán bộ trong danh bạ của phân hệ CBNV (`GET /api/accounts/staffs/`). */
export interface CanBo {
  id: number;
  username: string;
  ho_ten: string;
  don_vi_id: number | null;
  don_vi_ten: string;
  chuc_vu_id: number | null;
  chuc_vu_ten: string;
}

/** Lỗi nghiệp vụ chuẩn của backend: {code, detail, fields}. */
export interface LoiNghiepVu {
  code?: string;
  detail?: string;
  fields?: Record<string, unknown>;
}
