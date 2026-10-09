/**
 * Luồng khóa ký trên thiết bị: đăng ký khóa (proof-of-possession, đặt PIN, kích hoạt hoặc xoay vòng), ký bằng PIN,
 * đổi PIN. MVP một khóa hoạt động trên một thiết bị: đổi thiết bị là đăng ký khóa mới và xoay vòng (plan mục 3.4).
 */
import { signingApi } from './api';
import {
  bocKhoa, danXuatPin, kyBytes, layBanBoc, luuBanBoc, moBanBoc, sinhCapKhoa, taoThamSoKdf, tuHex,
} from './khoaKy';
import type { KhoaKy } from './types';

export function khoaHoatDong(danh_sach: KhoaKy[]): KhoaKy | undefined {
  return danh_sach.find((k) => k.trang_thai === 'HOAT_DONG');
}

/** Đăng ký khóa mới cho thiết bị này; khóa đang hoạt động (thiết bị cũ) được xoay vòng sang khóa mới. */
export async function dangKyKhoaThietBi(userId: number, pin: string, khoa_hien_co: KhoaKy[]): Promise<KhoaKy> {
  const cap = await sinhCapKhoa();
  const ma_khoa = `TB-${userId}-${Date.now()}`;
  const khoa = await signingApi.dangKyKhoa(ma_khoa, cap.khoaCongKhai);
  const { thach_thuc } = await signingApi.thachThuc(khoa.id);
  await signingApi.xacMinhKhoa(khoa.id, await kyBytes(cap.privatePkcs8, new TextEncoder().encode(thach_thuc)));

  const tham_so = taoThamSoKdf();
  const pin_dx = await danXuatPin(pin, tham_so);
  const { manh_bi_mat } = await signingApi.datPin(khoa.id, pin_dx.verifier, tham_so);
  const ban = await bocKhoa(cap.privatePkcs8, pin_dx.master, manh_bi_mat);
  await luuBanBoc({
    ma: `${userId}:${khoa.id}`, userId, keyId: khoa.id, maKhoa: ma_khoa, khoaCongKhai: cap.khoaCongKhai, ...ban,
    thamSoKdf: tham_so, taoLuc: new Date().toISOString(),
  });

  const cu = khoaHoatDong(khoa_hien_co);
  return cu ? signingApi.xoayVongKhoa(cu.id, khoa.id) : signingApi.kichHoatKhoa(khoa.id);
}

/** Mở khóa bằng PIN rồi ký raw SHA-256 của tài liệu. Ném lỗi API (sai PIN, khóa PIN) hoặc thiếu bản bọc. */
export async function kyBangPin(userId: number, khoa: KhoaKy, pin: string, hashHex: string): Promise<string> {
  const ban = await layBanBoc(userId, khoa.id);
  if (!ban) throw new Error('thieu_ban_boc_thiet_bi');
  const pin_dx = await danXuatPin(pin, ban.thamSoKdf);
  const { manh_bi_mat } = await signingApi.moKhoaKy(khoa.id, pin_dx.verifier);
  const pkcs8 = await moBanBoc(ban, pin_dx.master, manh_bi_mat);
  return kyBytes(pkcs8, tuHex(hashHex));
}

/** Đổi PIN: mở bản bọc bằng k_srv cũ, bọc lại bằng PIN mới và k_srv mới (server xoay vòng k_srv). */
export async function doiPin(userId: number, khoa: KhoaKy, pin_cu: string, pin_moi: string): Promise<void> {
  const ban = await layBanBoc(userId, khoa.id);
  if (!ban) throw new Error('thieu_ban_boc_thiet_bi');
  const cu = await danXuatPin(pin_cu, ban.thamSoKdf);
  const tham_so_moi = taoThamSoKdf();
  const moi = await danXuatPin(pin_moi, tham_so_moi);
  const kq = await signingApi.doiPin(khoa.id, cu.verifier, moi.verifier, tham_so_moi);
  const pkcs8 = await moBanBoc(ban, cu.master, kq.manh_bi_mat_cu);
  await luuBanBoc({ ...ban, ...(await bocKhoa(pkcs8, moi.master, kq.manh_bi_mat)), thamSoKdf: tham_so_moi });
}
