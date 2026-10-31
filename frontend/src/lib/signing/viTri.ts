/** Khung ký theo tỷ lệ % của trang, gốc trên-trái (cùng hệ tọa độ với backend, plan mục 3.2). */
import type { NguoiKyLuot, ViTriKy } from './types';

export const KHUNG_MAC_DINH = { w: 30, h: 10 };

export const kep = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

const lam_tron = (v: number) => Math.round(v * 100) / 100;

/** Khung mặc định có tâm tại điểm bấm, nằm trọn trong trang. */
export function khungTuDiemBam(trang: number, x: number, y: number): ViTriKy {
  return {
    trang_ky: trang,
    toa_do_x: String(lam_tron(kep(x - KHUNG_MAC_DINH.w / 2, 0, 100 - KHUNG_MAC_DINH.w))),
    toa_do_y: String(lam_tron(kep(y - KHUNG_MAC_DINH.h / 2, 0, 100 - KHUNG_MAC_DINH.h))),
    chieu_rong_khung: String(KHUNG_MAC_DINH.w),
    chieu_cao_khung: String(KHUNG_MAC_DINH.h),
  };
}

export function soKhung(v: ViTriKy) {
  return {
    trang: v.trang_ky, x: Number(v.toa_do_x), y: Number(v.toa_do_y),
    w: Number(v.chieu_rong_khung), h: Number(v.chieu_cao_khung),
  };
}

/** Vị trí đã chụp vào dòng người ký của lượt trình (null khi chưa đặt). */
export function viTriCuaNguoiKy(n: NguoiKyLuot): ViTriKy | null {
  if (n.trang_ky == null) return null;
  return {
    trang_ky: n.trang_ky, toa_do_x: n.toa_do_x, toa_do_y: n.toa_do_y,
    chieu_rong_khung: n.chieu_rong_khung, chieu_cao_khung: n.chieu_cao_khung,
  };
}

interface KhungSo {
  trang: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

const KHOANG_CACH_KHUNG = 1;
const giaoNhau = (a: KhungSo, b: KhungSo) =>
  a.trang === b.trang && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/**
 * Chỉ để hiển thị: khung của các người ký khác nhau trên cùng trang không được đè nhau. Khung xếp trước (theo thứ
 * tự đưa vào, tức thứ tự cấp ký) giữ nguyên vị trí; khung sau bị đẩy xuống dưới (hoặc lên trên khi hết chỗ) tới chỗ
 * trống gần nhất (kề mép một khung đã xếp). Không còn chỗ trống thì giữ vị trí lưu. Vị trí lưu trong hồ sơ không bị thay đổi.
 */
export function xepKhungKhongChong<T extends KhungSo>(khung: T[]): T[] {
  const daXep: T[] = [];
  khung.forEach((k) => {
    const dsUngVien = [k.y];
    daXep.filter((p) => p.trang === k.trang).forEach((p) => {
      dsUngVien.push(p.y + p.h + KHOANG_CACH_KHUNG, p.y - k.h - KHOANG_CACH_KHUNG);
    });
    const y = dsUngVien.find((c) => c >= 0 && c + k.h <= 100 && !daXep.some((p) => giaoNhau({ ...k, y: c }, p)));
    daXep.push(y === undefined || y === k.y ? k : { ...k, y: Math.round(y * 100) / 100 });
  });
  return daXep;
}
