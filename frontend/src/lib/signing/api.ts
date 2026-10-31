/**
 * Client API Trình ký (Nhóm 5) trên nền `apiClient` dùng chung (JWT, tự làm mới token).
 * Thao tác chuyển trạng thái gửi header `Idempotency-Key`: cùng một lần bấm (kể cả khi thử lại do mạng)
 * dùng cùng khóa, nên server không xử lý trùng.
 */
import apiClient, { ApiError } from '@lib/apiClient';
import { resolveDocumentApiUrl } from '@lib/routes';
import type {
  BangChung, BoLocHoSo, BoLocTaiLieu, CanBo, CanBoChucVu, ChucVu, DonViApDungHoSo, DonViLuaChon, TepTaiLieu, ThongKeHoSo, HoSo, HoSoChiTiet, KhoaKy, LoiNghiepVu, NguoiDungHienTai, QuyTrinh,
  ThamSoKdf, TinNhan, TrangKetQua, TraoDoi, VanBanDi, VanBanDiTepDinhKem, ViTriKy,
} from './types';

export const SIGNING_BASE = '/api/v1/signing';
/** Số hồ sơ (hoặc thông báo) mỗi trang danh sách (server mặc định 10, tối đa 100). */
export const SO_HO_SO_MOI_TRANG = 10;

/** `crypto.randomUUID` chỉ có ở ngữ cảnh an toàn; `getRandomValues` có ở mọi ngữ cảnh (khóa này không phải bí mật). */
export function taoKhoaChongTrung(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
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
  danhSach: (hop: 'can_toi_ky' | 'toi_gui' | 'tat_ca', loc: BoLocHoSo = {}, trang = 1) => {
    const tham_so = new URLSearchParams({ hop, page: String(trang), page_size: String(SO_HO_SO_MOI_TRANG) });
    Object.entries(loc).forEach(([k, v]) => v && tham_so.set(k, v));
    return apiClient.get<TrangKetQua<HoSo>>(`${SIGNING_BASE}/trinh-ky/?${tham_so}`);
  },
  /** Số hồ sơ theo thẻ lọc nhanh; cùng từ khóa, quy trình, đơn vị áp dụng và khoảng ngày với danh sách. */
  thongKe: (hop: 'can_toi_ky' | 'toi_gui' | 'tat_ca', loc: BoLocHoSo = {}) => {
    const tham_so = new URLSearchParams({ hop });
    Object.entries(loc).forEach(([k, v]) => k !== 'nhanh' && v && tham_so.set(k, v));
    return apiClient.get<ThongKeHoSo>(`${SIGNING_BASE}/trinh-ky/thong-ke/?${tham_so}`);
  },
  donViApDungTheoHop: (hop: 'can_toi_ky' | 'toi_gui' | 'tat_ca') =>
    apiClient.get<DonViApDungHoSo[]>(`${SIGNING_BASE}/trinh-ky/don-vi-ap-dung/?${new URLSearchParams({ hop })}`),
  chiTiet: (id: number) => apiClient.get<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/`),
  taoNhap: (form: FormData) => postForm<HoSoChiTiet>('/trinh-ky/', form),
  /** Chi tiết văn bản đi và danh sách tệp để chọn PDF từ đúng bản ghi. */
  chiTietVanBanDi: (id: number) => apiClient.get<VanBanDi & { attachments: VanBanDiTepDinhKem[] }>(resolveDocumentApiUrl(id, 'DI')),
  /** Sau khi hoàn tất duyệt nội bộ, liên kết hồ sơ với văn bản đi đã đăng ký. */
  lienKetVanBanDi: (id: number, van_ban_id: number) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/lien-ket-van-ban-di/`, { van_ban_id }),
  /** Sửa hồ sơ nháp: hạn chót, ghi chú, số hiệu/trích yếu nhập tay, thay tệp (multipart). */
  suaNhap: (id: number, form: FormData) =>
    apiClient<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/`, { method: 'PATCH', body: form }),
  gui: (id: number, khoa: string, chon_nguoi_ky: Record<string, number>, vi_tri_ky: Record<string, ViTriKy>) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/gui/`, { chon_nguoi_ky, vi_tri_ky }, tieuDe(khoa)),
  huy: (id: number, khoa: string, ly_do: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/huy/`, { ly_do }, tieuDe(khoa)),
  trinhLai: (id: number, khoa: string) =>
    apiClient.post<HoSoChiTiet>(`${SIGNING_BASE}/trinh-ky/${id}/trinh-lai/`, {}, tieuDe(khoa)),

  // ── Hành động người ký ───────────────────────────────────────────────────
  ky: (id: number, khoa: string, body: { khoa_ky: number; hash_tai_lieu: string; chu_ky_so: string; ghi_chu_ky: string; anh_chu_ky?: string }) =>
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
  tepCuaLuot: (id: number, luot: number) => layBlob(`/trinh-ky/${id}/tep/?luot=${luot}`),
  tepHoanTat: (id: number) => layBlob(`/trinh-ky/${id}/tep-hoan-tat/`),
  anhChuKy: (id: number, chuKyId: number) => layBlob(`/trinh-ky/${id}/anh-chu-ky/${chuKyId}/`),

  // ── Quy trình ────────────────────────────────────────────────────────────
  quyTrinh: (trang_thai?: string) =>
    apiClient.get<QuyTrinh[]>(`${SIGNING_BASE}/quy-trinh/${trang_thai ? `?trang_thai=${trang_thai}` : ''}`),
  taoQuyTrinh: (body: unknown) => apiClient.post<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/`, body),
  chiTietQuyTrinh: (id: number) => apiClient.get<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/${id}/`),
  suaQuyTrinh: (id: number, body: unknown) => apiClient.put<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/${id}/`, body),
  xoaQuyTrinh: (id: number) => apiClient.delete<unknown>(`${SIGNING_BASE}/quy-trinh/${id}/`),
  thaoTacQuyTrinh: (id: number, thao_tac: 'kich-hoat' | 'ngung' | 'nhan-ban') =>
    apiClient.post<QuyTrinh>(`${SIGNING_BASE}/quy-trinh/${id}/${thao_tac}/`, {}),
  // Dữ liệu cán bộ, chức vụ lấy từ API của phân hệ CBNV (Nhóm 7), không giữ danh sách riêng trong Trình ký
  /**
   * Danh bạ cán bộ đang hoạt động (họ tên, chức vụ, đơn vị) để chọn người ký khi cấu hình quy trình.
   * Lỗi quyền (403, thiếu `view_list_cbnv`) không được che bằng các nguồn dự phòng dưới đây: những nguồn đó có
   * phạm vi khác (không phải toàn bộ CBNV), tự chuyển sang khi thiếu quyền sẽ hiện một danh sách ngắn hơn mà
   * người dùng tưởng là toàn bộ cán bộ nhân viên. Lỗi 403 được báo thật để người dùng biết cần cấp quyền.
   */
  /** Id tài khoản đang hoạt động có quyền ký (`sign_trinhky`); cần quyền quản lý quy trình. */
  nguoiKyCoQuyen: () => apiClient.get<{ ids: number[] }>('/api/v1/signing/nguoi-ky-co-quyen/').then((r) => r.ids),

  danhBaCanBo: () =>
    apiClient
      .get<CanBo[] | { results?: CanBo[] }>('/api/accounts/employees/?all=true')
      .then((res) => {
        const list = Array.isArray(res) ? res : (res && Array.isArray((res as { results?: CanBo[] }).results) ? (res as { results: CanBo[] }).results : []);
        if (list.length > 0) return list;
        return apiClient.get<CanBo[] | { results?: CanBo[] }>('/api/accounts/staffs/').then((s) =>
          Array.isArray(s) ? s : (s && Array.isArray((s as { results?: CanBo[] }).results) ? (s as { results: CanBo[] }).results : [])
        );
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) throw err;
        return apiClient
          .get<CanBo[] | { results?: CanBo[] }>('/api/accounts/staffs/')
          .then((res) => {
            if (Array.isArray(res)) return res;
            if (res && Array.isArray((res as { results?: CanBo[] }).results)) {
              return (res as { results: CanBo[] }).results;
            }
            return [];
          });
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) throw err;
        return apiClient
          .get<
            Array<{
              id: number;
              ten?: string;
              ho_ten?: string;
              ten_dang_nhap?: string;
              username?: string;
              chuc_vu?: string;
              chuc_vu_ten?: string;
              chuc_vu_id?: number | null;
              don_vi?: string;
              don_vi_ten?: string;
              don_vi_id?: number | null;
            }>
          >(`${SIGNING_BASE}/nguoi-dung/`)
          .then((ds) =>
            (Array.isArray(ds) ? ds : []).map((u) => ({
              id: u.id,
              username: u.username || u.ten_dang_nhap || '',
              ho_ten: u.ho_ten || u.ten || '',
              don_vi_id: u.don_vi_id ?? null,
              don_vi_ten: u.don_vi_ten || u.don_vi || '',
              chuc_vu_id: u.chuc_vu_id ?? null,
              chuc_vu_ten: u.chuc_vu_ten || u.chuc_vu || '',
            }))
          );
      }),
  /** Danh mục chức vụ (thứ tự hiển thị của CBNV) để chọn người ký theo chức vụ. */
  chucVu: () =>
    apiClient.get<ChucVu[]>('/api/positions/?all=true').catch(() =>
      apiClient.get<Array<{ id: number; name?: string; ten?: string; display_order?: number; stt?: number }>>(
        `${SIGNING_BASE}/chuc-vu/`
      ).then((ds) =>
        ds.map((c) => ({ id: c.id, name: c.name || c.ten || '', display_order: c.display_order || c.stt || 0 }))
      )
    ),
  /** Cán bộ đang làm việc giữ chức vụ (trong đơn vị nếu có): tên người khớp người ký cấu hình theo chức vụ. */
  canBoTheoChucVu: (chuc_vu: number, don_vi?: number | null) => {
    const tham_so = new URLSearchParams({ chuc_vu: String(chuc_vu) });
    if (don_vi) tham_so.set('don_vi', String(don_vi));
    return apiClient.get<{ count: number; results: CanBoChucVu[] }>(`${SIGNING_BASE}/can-bo-theo-chuc-vu/?${tham_so}`);
  },
  donVi: () => apiClient.get<DonViLuaChon[]>(`${SIGNING_BASE}/don-vi/`),
  taiLieu: (loc: BoLocTaiLieu = {}, trang = 1) => {
    const tham_so = new URLSearchParams({ page: String(trang), page_size: String(SO_HO_SO_MOI_TRANG) });
    Object.entries(loc).forEach(([k, v]) => v && tham_so.set(k, v));
    return apiClient.get<TrangKetQua<TepTaiLieu>>(`${SIGNING_BASE}/tai-lieu/?${tham_so}`);
  },
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
