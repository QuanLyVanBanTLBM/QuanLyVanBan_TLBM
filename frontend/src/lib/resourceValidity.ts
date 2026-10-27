import { HieuLucType } from '@app-types/resource';

export interface EffectiveValidity {
  status: HieuLucType;
  isExpired: boolean;
  isScheduled: boolean;
  expirationDate?: string | null;
}

/**
 * Lấy chuỗi ngày hôm nay theo giờ địa phương: YYYY-MM-DD
 */
export function getTodayLocalDateString(): string {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Tính toán trạng thái hiệu lực thực tế dựa trên ngày hiện tại và ngày hết hiệu lực.
 * - Nếu ngay_het_hieu_luc ở tương lai (> today): Văn bản vẫn CÒN HIỆU LỰC (đã lên lịch hết hạn).
 * - Nếu ngay_het_hieu_luc ở quá khứ hoặc hôm nay (<= today): Văn bản HẾT HIỆU LỰC.
 * - Nếu không có ngay_het_hieu_luc: Theo trạng thái hieu_luc lưu trong dữ liệu.
 */
export function computeEffectiveStatus(
  hieuLuc?: HieuLucType | string | null,
  ngayHetHieuLuc?: string | null,
  linkThayThe?: string | null,
  todayStr?: string
): EffectiveValidity {
  const today = todayStr || getTodayLocalDateString();
  const rawExpDate = ngayHetHieuLuc ? String(ngayHetHieuLuc).trim() : '';
  const expDate = rawExpDate ? rawExpDate.slice(0, 10) : '';

  if (expDate) {
    if (expDate > today) {
      // Ngày hết hiệu lực ở tương lai -> Hiện tại vẫn CÒN HIỆU LỰC (đã lên lịch hết hạn)
      const status: HieuLucType =
        hieuLuc === 'CON_HIEU_LUC_1_PHAN' ? 'CON_HIEU_LUC_1_PHAN' : 'CON_HIEU_LUC';
      return {
        status,
        isExpired: false,
        isScheduled: true,
        expirationDate: expDate,
      };
    } else {
      // Ngày hết hiệu lực đã đến hoặc đã qua -> HẾT HIỆU LỰC
      const status: HieuLucType =
        hieuLuc === 'HET_VA_THAY_THE' || (linkThayThe && linkThayThe.trim().length > 0)
          ? 'HET_VA_THAY_THE'
          : 'HET_HIEU_LUC';
      return {
        status,
        isExpired: true,
        isScheduled: false,
        expirationDate: expDate,
      };
    }
  }

  // Không thiết lập ngày hết hiệu lực
  const baseStatus = (hieuLuc as HieuLucType) || 'CON_HIEU_LUC';
  const isExpired = baseStatus === 'HET_HIEU_LUC' || baseStatus === 'HET_VA_THAY_THE';
  return {
    status: baseStatus,
    isExpired,
    isScheduled: false,
    expirationDate: null,
  };
}
