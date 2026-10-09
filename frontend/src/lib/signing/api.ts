/**
 * Client API Trình ký (Nhóm 5) trên nền `apiClient` dùng chung (JWT, tự làm mới token).
 * Thao tác chuyển trạng thái gửi header `Idempotency-Key`: cùng một lần bấm (kể cả khi thử lại do mạng)
 * dùng cùng khóa, nên server không xử lý trùng.
 */
import apiClient, { ApiError } from '@lib/apiClient';
import type {
  BangChung, HoSo, HoSoChiTiet, KhoaKy, LoiNghiepVu, NguoiDungHienTai, NguoiDungTim, QuyTrinh, ThamSoKdf, TinNhan,
  TraoDoi, VanBanDi, ViTriKy,
} from './types';

export const SIGNING_BASE = '/api/v1/signing';

export function taoKhoaChongTrung(): string {
  return crypto.randomUUID();
}

function tieuDe(khoa?: string): RequestInit {
  return khoa ? { headers: { 'Idempotency-Key': khoa } } : {};
}

function postForm<T>(duong_dan: string, form: FormData, khoa?: string): Promise<T> {
  return apiClient<T>(`${SIGNING_BASE}${duong_dan}`, { method: 'POST', body: form, ...tieuDe(khoa) });
}

/** Lỗi nghiệp vụ (code, detail, fields) từ ApiError; lỗi khác trả code rỗng. */
export function docLoi(err: unknown): LoiNghiepVu & { status: number } {
  if (err instanceof ApiError) {
    const data = err.data as LoiNghiepVu;
    return { status: err.status, code: data.code, detail: data.detail || err.message, fields: data.fields };
  }
  return { status: 0, detail: err instanceof Error ? err.message : String(err) };
}

async function layBlobMotLan(duong_dan: string): Promise<Response> {
  const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
  return fetch(`${import.meta.env.VITE_API_URL || ''}${SIGNING_BASE}${duong_dan}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

/** Tải tệp có xác thực (PDF, ảnh chữ ký). Hết hạn token thì làm mới qua apiClient rồi thử lại một lần. */
export async function layBlob(duong_dan: string): Promise<Blob> {
  let res = await layBlobMotLan(duong_dan);
  if (res.status === 401) {
    await apiClient.get(`${SIGNING_BASE}/toi/`);
    res = await layBlobMotLan(duong_dan);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, data);
  }
  return res.blob();
}

export const signingApi = {
  toi: () => apiClient.get<NguoiDungHienTai>(`${SIGNING_BASE}/toi/`),

  // ── Hồ sơ ────────────────────────────────────────────────────────────────
  danhSach: (hop: 'can_toi_ky' | 'toi_gui' | 'tat_ca', trang_thai?: string) =>
    apiClient.get<HoSo[]>(`${SIGNING_BASE}/trinh-ky/?hop=${hop}${trang_thai ? `&trang_thai=${trang_thai}` : ''}`),
  chiTiet: (id: number) => apiClient.get<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/`),
  taoNhap: (form: FormData) => postForm<HoSoChiTiet>('/trinh-ky/', form),
  gui: (id: number, khoa: string, chon_nguoi_ky: Record<string, number>, vi_tri_ky: Record<string, ViTriKy>) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/gui/`, { chon_nguoi_ky, vi_tri_ky }, tieuDe(khoa)),
  huy: (id: number, khoa: string, ly_do: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/huy/`, { ly_do }, tieuDe(khoa)),
  trinhLai: (id: number, khoa: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/trinh-lai/`, {}, tieuDe(khoa)),

  // ── Hành động người ký ───────────────────────────────────────────────────
  ky: (id: number, khoa: string, body: { khoa_ky: number; hash_tai_lieu: string; chu_ky_so: string; ghi_chu_ky: string }) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/ky/`, body, tieuDe(khoa)),
  tuChoi: (id: number, khoa: string, ly_do_tu_choi: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/tu-choi/`, { ly_do_tu_choi }, tieuDe(khoa)),
  thuHoi: (id: number, khoa: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/thu-hoi/`, {}, tieuDe(khoa)),
  yeuCauSua: (id: number, khoa: string, tieu_de: string, ly_do: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/yeu-cau-sua/`, { tieu_de, ly_do }, tieuDe(khoa)),

  // ── Trả lại để sửa ───────────────────────────────────────────────────────
  traoDoi: (id: number) => apiClient.get<TraoDoi>(`${SIGNING_BASE}/trinh-ky/${id}/trao-doi/`),
  guiTinNhan: (id: number, noi_dung: string) =>
    apiClient.post<TinNhan>(`${SIGNING_BASE}/trinh-ky/${id}/trao-doi/`, { noi_dung }),
  giaiQuyet: (id: number, khoa: string, tep: File, vi_tri_ky?: Record<string, ViTriKy>) => {
    const form = new FormData();
    form.append('tep', tep);
    if (vi_tri_ky && Object.keys(vi_tri_ky).length) form.append('vi_tri_ky', JSON.stringify(vi_tri_ky));
    return postForm<HoSoChiTiet>(`/trinh-ky/${id}/giai-quyet/`, form, khoa);
  },

  // ── Kết quả ──────────────────────────────────────────────────────────────
  bangChung: (id: number) => apiClient.get<BangChung>(`${SIGNING_BASE}/trinh-ky/${id}/bang-chung/`),
  taoLaiTepHoanTat: (id: number) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/tao-lai-tep-hoan-tat/`, {}),
  tepGoc: (id: number) => layBlob(`/trinh-ky/${id}/tep/`),
  tepHoanTat: (id: number) => layBlob(`/trinh-ky/${id}/tep-hoan-tat/`),
  anhChuKy: (id: number, chuKyId: number) => layBlob(`/trinh-ky/${id}/anh-chu-ky/${chuKyId}/`),

  // ── Quy trình ────────────────────────────────────────────────────────────
  quyTrinh: (trang_thai?: string) =>
    apiClient.get<QuyTrinh[]>(`${SIGNING_BASE}/quy-trinh/${trang_thai ? `?trang_thai=${trang_thai}` : ''}`),
  taoQuyTrinh: (body: unknown) => apiClient.post<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/`, body),
  thaoTacQuyTrinh: (id: number, thao_tac: 'kich-hoat' | 'ngung' | 'nhan-ban') =>
    apiClient.post<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/${id}/${thao_tac}/`, {}),
  timNguoiDung: (q: string) =>
    apiClient.get<NguoiDungTim[]>(`${SIGNING_BASE}/nguoi-dung/?q=${encodeURIComponent(q)}`),
  timVanBanDi: (q: string) => apiClient.get<VanBanDi[]>(`${SIGNING_BASE}/van-ban-di/?q=${encodeURIComponent(q)}`),

  // ── Khóa ký, PIN ─────────────────────────────────────────────────────────
  khoa: () => apiClient.get<KhoaKy[]>(`${SIGNING_BASE}/khoa/`),
  dangKyKhoa: (ma_khoa: string, khoa_cong_khai: string) =>
    apiClient.post<KhoaKy>(`${SIGNING_BASE}/khoa/`, { ma_khoa, khoa_cong_khai, ngay_hieu_luc: new Date().toISOString() }),
  thachThuc: (id: number) => apiClient.get<{ thach_thuc: string }>(`${SIGNING_BASE}/khoa/${id}/thach-thuc/`),
  xacMinhKhoa: (id: number, chu_ky_so: string) =>
    apiClient.post<KhoaKy>(`${SIGNING_BASE}/khoa/${id}/xac-minh/`, { chu_ky_so }),
  kichHoatKhoa: (id: number) => apiClient.post<KhoaKy>(`${SIGNING_BASE}/khoa/${id}/kich-hoat/`, {}),
  /** Đổi thiết bị: khóa cũ DA_XOAY_VONG, khóa mới (đã xác minh) thành HOAT_DONG. */
  xoayVongKhoa: (id: number, khoa_moi: number) =>
    apiClient.post<KhoaKy>(`${SIGNING_BASE}/khoa/${id}/xoay-vong/`, { khoa_moi }),
  thuHoiKhoa: (id: number, ly_do: string) => apiClient.post<KhoaKy>(`${SIGNING_BASE}/khoa/${id}/thu-hoi/`, { ly_do }),
  datPin: (id: number, xac_minh_pin: string, tham_so_kdf: ThamSoKdf) =>
    apiClient.post<{ manh_bi_mat: string; tham_so_kdf: ThamSoKdf }>(
      `${SIGNING_BASE}/khoa/${id}/dat-pin/`, { xac_minh_pin, tham_so_kdf }),
  moKhoaKy: (id: number, xac_minh_pin: string) =>
    apiClient.post<{ manh_bi_mat: string; tham_so_kdf: ThamSoKdf }>(`${SIGNING_BASE}/khoa/${id}/mo-khoa-ky/`, { xac_minh_pin }),
  doiPin: (id: number, xac_minh_pin_cu: string, xac_minh_pin_moi: string, tham_so_kdf: ThamSoKdf) =>
    apiClient.post<{ manh_bi_mat: string; manh_bi_mat_cu: string; tham_so_kdf: ThamSoKdf }>(
      `${SIGNING_BASE}/khoa/${id}/doi-pin/`, { xac_minh_pin_cu, xac_minh_pin_moi, tham_so_kdf }),
};
