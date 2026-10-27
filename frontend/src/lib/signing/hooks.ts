import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { taoKhoaChongTrung } from './api';
import type { NguoiDungHienTai } from './types';

/**
 * Tải dữ liệu bất đồng bộ; `tai()` để tải lại. "Đang tải" suy ra từ khóa (phụ thuộc + số lần tải lại) chưa có
 * kết quả, nên effect chỉ đặt state trong callback bất đồng bộ. Khi tải lại vẫn giữ dữ liệu cũ để hiển thị.
 */
export function useTai<T>(ham: () => Promise<T>, phu_thuoc: unknown[] = []) {
  const [lan, setLan] = useState(0);
  const [ket_qua, setKetQua] = useState<{ khoa: string; duLieu: T | null; loi: unknown } | null>(null);
  const hamRef = useRef(ham);
  useEffect(() => {
    hamRef.current = ham;
  });
  const khoa = `${JSON.stringify(phu_thuoc)}#${lan}`;

  useEffect(() => {
    let huy = false;
    hamRef.current().then(
      (duLieu) => !huy && setKetQua({ khoa, duLieu, loi: null }),
      (loi) => !huy && setKetQua((cu) => ({ khoa, duLieu: cu?.duLieu ?? null, loi })),
    );
    return () => {
      huy = true;
    };
  }, [khoa]);

  const tai = useCallback(() => setLan((n) => n + 1), []);
  const setDuLieu = useCallback((duLieu: T) => setKetQua((cu) => ({ khoa: cu?.khoa ?? '', duLieu, loi: null })), []);
  const xong = ket_qua?.khoa === khoa;
  return { duLieu: ket_qua?.duLieu ?? null, setDuLieu, loi: xong ? ket_qua.loi : null, dangTai: !xong, tai };
}

/**
 * Khóa chống trùng cho một thao tác: giữ nguyên khi bấm lại hoặc thử lại sau lỗi mạng (server trả kết quả lần
 * trước), đổi mới sau khi thao tác thành công hoặc đóng hộp thoại.
 */
export function useKhoaChongTrung() {
  const ref = useRef<string>(taoKhoaChongTrung());
  return {
    lay: () => ref.current,
    lamMoi: () => {
      ref.current = taoKhoaChongTrung();
    },
  };
}

export const SigningContext = createContext<{
  toi: NguoiDungHienTai | null;
  taiLaiToi: () => void;
  /** Trang Thông báo báo đã xem để tab cập nhật số thông báo mới. */
  daXemThongBao?: () => void;
  /** Sau khi ký, từ chối, hủy… trên hồ sơ: tải lại số "Cần tôi ký duyệt" và số thông báo mới ở thanh tab. */
  lamMoiDem?: () => void;
}>({
  toi: null,
  taiLaiToi: () => undefined,
});

export function useToi() {
  return useContext(SigningContext);
}

export function coQuyen(toi: NguoiDungHienTai | null, ma: string): boolean {
  return Boolean(toi?.quyen?.[ma]);
}

// Thông báo mới: so thời điểm tạo với lần xem trang Thông báo gần nhất, lưu trên trình duyệt (tiện ích hiển thị,
// không phải trạng thái nghiệp vụ; bảng signing_notification chưa có cột đã đọc).
const KHOA_DA_XEM = 'tlbm_signing_thong_bao_xem_luc';

export function lanXemThongBao(userId: number): number {
  try {
    return Number(localStorage.getItem(`${KHOA_DA_XEM}:${userId}`)) || 0;
  } catch {
    return 0;
  }
}

export function danhDauDaXemThongBao(userId: number): void {
  try {
    localStorage.setItem(`${KHOA_DA_XEM}:${userId}`, String(Date.now()));
  } catch {
    // trình duyệt chặn lưu trữ: bỏ qua, chỉ mất số thông báo mới
  }
}

export function soThongBaoMoi(ds: { created_at: string }[] | null, userId: number | undefined): number {
  if (!ds || userId == null) return 0;
  const moc = lanXemThongBao(userId);
  return ds.filter((tb) => new Date(tb.created_at).getTime() > moc).length;
}
