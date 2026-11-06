/**
 * Luồng khóa ký server-side: client tạo khóa Ed25519 một lần, gửi PKCS#8 cùng PIN qua HTTPS để server mã hóa;
 * mỗi lần ký, server giải mã trong bộ nhớ và tự tạo chữ ký. Private key không được giữ trong IndexedDB/file.
 */
import { signingApi } from './api';
import { b64, kiemTraPin, sinhCapKhoa, taoThamSoKdf, kyBytes } from './khoaKy';
import type { KhoaKy } from './types';

export function khoaHoatDong(danh_sach: KhoaKy[]): KhoaKy | undefined {
  return danh_sach.find((k) => k.trang_thai === 'HOAT_DONG');
}

/** Tạo khóa mới, chứng minh sở hữu, mã hóa private key server-side rồi kích hoạt/xoay vòng khóa. */
export async function dangKyKhoaThietBi(
  userId: number, pin: string, khoa_hien_co: KhoaKy[],
): Promise<KhoaKy> {
  const loiPin = kiemTraPin(pin);
  if (loiPin || pin.length !== 6) throw new Error(loiPin || 'pin_khong_hop_le');

  const cap = await sinhCapKhoa();
  let khoa: KhoaKy | null = null;
  let batDauKichHoat = false;
  try {
    const ma_khoa = `TB-${userId}-${Date.now()}`;
    khoa = await signingApi.dangKyKhoa(ma_khoa, cap.khoaCongKhai);
    const { thach_thuc } = await signingApi.thachThuc(khoa.id);
    await signingApi.xacMinhKhoa(
      khoa.id, thach_thuc, await kyBytes(cap.privatePkcs8, new TextEncoder().encode(thach_thuc)),
    );
    const tham_so = taoThamSoKdf();
    await signingApi.datPin(khoa.id, pin, b64(cap.privatePkcs8), tham_so);

    const cu = khoaHoatDong(khoa_hien_co);
    // Khi request kích hoạt/rotate đã được gửi, response mất mạng có thể chỉ là lỗi sau commit.
    // Không thu hồi key mới khi chưa biết trạng thái server để tránh thu hồi luôn key đang hoạt động.
    batDauKichHoat = true;
    return cu ? await signingApi.xoayVongKhoa(cu.id, khoa.id) : await signingApi.kichHoatKhoa(khoa.id);
  } catch (err) {
    if (khoa && !batDauKichHoat) {
      try {
        await signingApi.thuHoiKhoa(khoa.id, 'Hủy đăng ký khóa chưa hoàn tất.');
      } catch {
        // Giữ lỗi gốc; nếu mạng gián đoạn, khóa chờ được giữ lại để quản trị viên xử lý.
      }
    }
    throw err;
  } finally {
    cap.privatePkcs8.fill(0);
  }
}

/** Đổi PIN: máy chủ mở khóa cũ và mã hóa lại private key bằng salt mới. */
export async function doiPin(khoa: KhoaKy, pin_cu: string, pin_moi: string): Promise<void> {
  const loiPin = kiemTraPin(pin_moi);
  if (loiPin || pin_moi.length !== 6) throw new Error(loiPin || 'pin_khong_hop_le');
  await signingApi.doiPin(khoa.id, pin_cu, pin_moi, taoThamSoKdf());
}
