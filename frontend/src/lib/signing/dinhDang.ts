/** Tiện ích hiển thị dùng chung của phân hệ Trình ký. */
import type { HamDich } from './i18n';
import type { LoaiTepTaiLieu, NguoiKyCauHinh } from './types';

export const LOP_O_NHAP =
  'w-full rounded-xl border border-border-subtle bg-surface px-3.5 py-2 text-sm text-main placeholder:text-muted ' +
  'focus:outline-none focus:border-focus focus:ring-2 focus:ring-primary-subtle';

/** Chữ thường, bỏ dấu tiếng Việt (đ -> d) để tìm không phân biệt hoa thường và dấu (như server). */
export function boDau(chuoi: string): string {
  return chuoi.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd');
}

export function dinhDangNgay(iso: string | null | undefined, lang: 'vi' | 'en'): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-GB', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

/** Số hiệu — trích yếu; khi hồ sơ thiếu cả hai thì nêu rõ là văn bản chưa được định danh. */
export function moTaVanBan(
  vb: { so_hieu?: string; trich_yeu?: string } | undefined,
  t: HamDich,
): string {
  const phan = [vb?.so_hieu, vb?.trich_yeu].filter(Boolean);
  if (phan.length) return phan.join(' — ');
  return t('danhSach.vanBanChuaDinhDanh');
}

/** Dịch mã lỗi của tiến trình tạo PDF hoàn tất; mã không nhận diện thì không lộ giá trị nội bộ. */
export function loiTepHoanTatHienThi(ma: string, t: HamDich): string {
  const khoa = `chiTiet.loiTaoTepMa.${ma}`;
  const thongDiep = t(khoa);
  return thongDiep === khoa || thongDiep === '—' ? t('chiTiet.loiTaoTepKhongRo') : thongDiep;
}

/** Tên tệp tải về có nhãn hồ sơ và nội dung dễ nhận biết. */
export function tenTepTaiVe(hoSoId: number, loai: LoaiTepTaiLieu, soLuot?: number | null): string {
  const hoSo = `ho-so-${hoSoId}`;
  if (loai === 'DU_THAO') return `${hoSo}-ban-du-thao.pdf`;
  if (loai === 'HOAN_TAT') return `${hoSo}-ban-hoan-tat.pdf`;
  return soLuot == null ? `${hoSo}-ban-trinh-ky.pdf` : `${hoSo}-luot-${soLuot}.pdf`;
}

export function tenBangChungTaiVe(hoSoId: number): string {
  return `ho-so-${hoSoId}-bang-chung.json`;
}

/** Giới hạn độ dài nhập tay, khớp serializer backend (`serializers.py`). */
export const GIOI_HAN = { trichYeu: 1000, ghiChu: 2000, lyDo: 2000, tinNhan: 2000, tenQuyTrinh: 255, maQuyTrinh: 50, soGio: 24 * 365 } as const;
export const TEP_TOI_DA_BYTE = 20 * 1024 * 1024;
export const MA_QUY_TRINH_HOP_LE = /^[A-Za-z0-9_.-]+$/;

/** Kiểm tệp PDF trước khi gửi: trả khóa i18n của lỗi (không gửi request khi sai), hoặc null khi hợp lệ. */
export function kiemTraTepPdf(tep: { name: string; size: number; type: string }): string | null {
  if (tep.size === 0) return 'tao.loiTepRong';
  if (tep.type !== 'application/pdf' && !tep.name.toLowerCase().endsWith('.pdf')) return 'tao.loiTepDinhDang';
  if (tep.size > TEP_TOI_DA_BYTE) return 'loi.tep_qua_lon';
  return null;
}

/** Giá trị ô datetime-local đã qua (hoặc bằng) thời điểm hiện tại; ô trống thì không lỗi. */
export function hanChotDaQua(gia_tri: string): boolean {
  return Boolean(gia_tri) && new Date(gia_tri).getTime() <= Date.now();
}

export function taiXuong(blob: Blob, ten: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ten;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Người ký chưa ký trên lượt đã kết thúc (từ chối, hủy) không còn phải ký; lượt đang trả sửa thì tạm dừng. */
export function trangThaiNguoiKy(luot: string, nguoi: string, da_mo: boolean): string {
  if (nguoi !== 'CHO_KY') return nguoi;
  if (luot === 'TU_CHOI' || luot === 'HUY') return 'KHONG_CAN_KY';
  if (luot === 'YEU_CAU_SUA') return 'TAM_DUNG';
  return da_mo ? 'CHO_KY' : 'CHUA_MO';
}

/** Tên người ký cấu hình: tài khoản cụ thể, hoặc chức vụ (theo Danh mục chức vụ CBNV) xác định người lúc gửi. */
export function tenNguoiKyCauHinh(n: Pick<NguoiKyCauHinh, 'ten_nguoi_ky' | 'ten_chuc_vu'>, t: HamDich): string {
  if (n.ten_nguoi_ky) return n.ten_nguoi_ky;
  return n.ten_chuc_vu ? t('quyTrinh.theoChucVu', { ten: n.ten_chuc_vu }) : t('tao.theoChucVu');
}
