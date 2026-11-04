/**
 * Luồng khóa ký trên thiết bị: đăng ký khóa (proof-of-possession, đặt PIN, kích hoạt hoặc xoay vòng), ký bằng PIN,
 * đổi PIN. Bản bọc lưu ở IndexedDB của thiết bị và xuất được ra file khóa (`fileKhoa.ts`); ký bằng bản bọc của
 * thiết bị hoặc bằng file khóa tải lên, cả hai đều cần PIN. Khóa đang hoạt động là một khóa (plan mục 3.4).
 */
import { signingApi } from './api';
import { kiemTraFileKhop } from './fileKhoa';
import {
  type BanBocKhoa, bocKhoa, danXuatPin, kyBytes, layBanBoc, luuBanBoc, moBanBoc, sinhCapKhoa, taoThamSoKdf, tuHex,
} from './khoaKy';
import type { KhoaKy } from './types';

export function khoaHoatDong(danh_sach: KhoaKy[]): KhoaKy | undefined {
  return danh_sach.find((k) => k.trang_thai === 'HOAT_DONG');
}

/**
 * Đăng ký khóa mới cho thiết bị này; khóa đang hoạt động (thiết bị cũ) được xoay vòng sang khóa mới.
 * Trả khóa đã kích hoạt và bản bọc để xuất file khóa.
 */
export async function dangKyKhoaThietBi(
  userId: number, pin: string, khoa_hien_co: KhoaKy[],
): Promise<{ khoa: KhoaKy; banBoc: BanBocKhoa }> {
  const cap = await sinhCapKhoa();
  const ma_khoa = `TB-${userId}-${Date.now()}`;
  const khoa = await signingApi.dangKyKhoa(ma_khoa, cap.khoaCongKhai);
  const { thach_thuc } = await signingApi.thachThuc(khoa.id);
  await signingApi.xacMinhKhoa(khoa.id, thach_thuc, await kyBytes(cap.privatePkcs8, new TextEncoder().encode(thach_thuc)));

  const tham_so = taoThamSoKdf();
  const pin_dx = await danXuatPin(pin, tham_so);
  const { manh_bi_mat } = await signingApi.datPin(khoa.id, pin_dx.verifier, tham_so);
  const ban = await bocKhoa(cap.privatePkcs8, pin_dx.master, manh_bi_mat);
  const ban_boc: BanBocKhoa = {
    ma: `${userId}:${khoa.id}`, userId, keyId: khoa.id, maKhoa: ma_khoa, khoaCongKhai: cap.khoaCongKhai, ...ban,
    thamSoKdf: tham_so, taoLuc: new Date().toISOString(),
  };
  await luuBanBoc(ban_boc);

  const cu = khoaHoatDong(khoa_hien_co);
  const kich_hoat = cu ? await signingApi.xoayVongKhoa(cu.id, khoa.id) : await signingApi.kichHoatKhoa(khoa.id);
  return { khoa: kich_hoat, banBoc: ban_boc };
}

/** Bản bọc dùng để ký: file khóa tải lên (kiểm đúng người, đúng khóa) hoặc bản lưu trên thiết bị. */
async function banBocDeKy(userId: number, khoa: KhoaKy, ban_tu_file?: BanBocKhoa): Promise<BanBocKhoa> {
  if (ban_tu_file) {
    kiemTraFileKhop(ban_tu_file, userId, khoa);
    return ban_tu_file;
  }
  const ban = await layBanBoc(userId, khoa.id);
  if (!ban) throw new Error('thieu_ban_boc_thiet_bi');
  return ban;
}

/** Nhập file khóa vào thiết bị này (để ký không cần tải file mỗi lần); kiểm đúng người và khóa đang hoạt động. */
export async function nhapFileKhoa(userId: number, khoa: KhoaKy, ban: BanBocKhoa): Promise<void> {
  kiemTraFileKhop(ban, userId, khoa);
  await luuBanBoc(ban);
}

/**
 * Mở khóa bằng PIN rồi ký raw SHA-256 của tài liệu. `ban_tu_file`: bản bọc đọc từ file khóa tải lên; bỏ trống thì
 * dùng bản lưu trên thiết bị. Ném lỗi API (sai PIN, khóa PIN), file không khớp hoặc thiếu bản bọc.
 */
export async function kyBangPin(
  userId: number, khoa: KhoaKy, pin: string, hashHex: string, ban_tu_file?: BanBocKhoa,
): Promise<string> {
  const ban = await banBocDeKy(userId, khoa, ban_tu_file);
  const pin_dx = await danXuatPin(pin, ban.thamSoKdf);
  const { manh_bi_mat } = await signingApi.moKhoaKy(khoa.id, pin_dx.verifier);
  const pkcs8 = await moBanBoc(ban, pin_dx.master, manh_bi_mat);
  return kyBytes(pkcs8, tuHex(hashHex));
}

/**
 * Đổi PIN: mở bản bọc bằng k_srv cũ, bọc lại bằng PIN mới và k_srv mới (server xoay vòng k_srv). File khóa cũ
 * không còn dùng được; trả bản bọc mới để xuất lại file.
 */
export async function doiPin(
  userId: number, khoa: KhoaKy, pin_cu: string, pin_moi: string, ban_tu_file?: BanBocKhoa,
): Promise<BanBocKhoa> {
  const ban = await banBocDeKy(userId, khoa, ban_tu_file);
  const cu = await danXuatPin(pin_cu, ban.thamSoKdf);
  const tham_so_moi = taoThamSoKdf();
  const moi = await danXuatPin(pin_moi, tham_so_moi);
  const kq = await signingApi.doiPin(khoa.id, cu.verifier, moi.verifier, tham_so_moi);
  const pkcs8 = await moBanBoc(ban, cu.master, kq.manh_bi_mat_cu);
  const ban_moi = { ...ban, ...(await bocKhoa(pkcs8, moi.master, kq.manh_bi_mat)), thamSoKdf: tham_so_moi };
  await luuBanBoc(ban_moi);
  return ban_moi;
}
