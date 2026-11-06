import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { signingApi, taoKhoaChongTrung } from './api';
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
  /** Sau khi ký, từ chối, hủy… trên hồ sơ: tải lại số "Cần tôi ký duyệt" ở thanh tab. */
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

/**
 * Ảnh chữ ký cá nhân dưới dạng object URL, tải qua apiClient có Bearer (thẻ img trần không gửi Authorization).
 * Trả null khi chưa có ảnh, đang tải hoặc tải lỗi (401/404...): giao diện hiển thị trạng thái trống.
 * Object URL được thu hồi khi đổi ảnh hoặc gỡ component.
 */
export function useAnhChuKyCaNhan(coAnh: boolean | undefined, nguoiId: number | undefined): string | null {
  const khoa = coAnh ? `${nguoiId}` : null;
  const [ket_qua, setKetQua] = useState<{ khoa: string; url: string } | null>(null);

  useEffect(() => {
    if (!khoa) return undefined;
    let huy = false;
    let url: string | null = null;
    Promise.resolve()
      .then(() => signingApi.tepAnhChuKyCaNhan())
      .then(
        (blob) => {
          if (huy) return;
          url = URL.createObjectURL(blob);
          setKetQua({ khoa, url });
        },
        () => !huy && setKetQua(null),
      );
    return () => {
      huy = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [khoa]);

  return khoa && ket_qua?.khoa === khoa ? ket_qua.url : null;
}
