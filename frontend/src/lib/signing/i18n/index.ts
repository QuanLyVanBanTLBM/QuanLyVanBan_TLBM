/**
 * Từ điển vi/en riêng của phân hệ Trình ký; ngôn ngữ theo bộ chọn chung (`@i18n/translate`).
 * Tách riêng để không sửa tệp dịch dùng chung của các nhóm khác.
 */
import { useTranslation } from '@i18n/translate';
import { docLoi } from '../api';
import en from './en.json';
import vi from './vi.json';

const TU_DIEN = { vi, en } as const;

function tra(tu_dien: unknown, khoa: string): string | undefined {
  let cur: unknown = tu_dien;
  for (const p of khoa.split('.')) {
    if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[p];
    } else {
      return undefined;
    }
  }
  return typeof cur === 'string' ? cur : undefined;
}

/** Thông điệp đầu tiên trong `fields` của lỗi validation kèm tên trường cấp trên cùng: [trường, nội dung]. */
function thongDiepDauTien(fields: unknown): [string, string] | null {
  const tim = (gia_tri: unknown): string | null => {
    if (typeof gia_tri === 'string') return gia_tri;
    if (Array.isArray(gia_tri)) return gia_tri.map(tim).find(Boolean) ?? null;
    if (gia_tri && typeof gia_tri === 'object') return Object.values(gia_tri).map(tim).find(Boolean) ?? null;
    return null;
  };
  if (!fields || typeof fields !== 'object') return null;
  for (const [truong, v] of Object.entries(fields)) {
    const nd = tim(v);
    if (nd) return [truong, nd];
  }
  return null;
}

export type HamDich = (khoa: string, thay?: Record<string, string | number>) => string;

export function dich(lang: 'vi' | 'en', khoa: string, thay?: Record<string, string | number>): string {
  let kq = tra(TU_DIEN[lang], khoa) ?? tra(TU_DIEN.vi, khoa) ?? khoa;
  Object.entries(thay || {}).forEach(([k, v]) => {
    kq = kq.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
  });
  return kq;
}

export function useSigningT() {
  const { currentLang } = useTranslation();
  const t: HamDich = (khoa, thay) => dich(currentLang, khoa, thay);
  /** Thông báo cho lỗi API/luồng: theo mã lỗi nếu có bản dịch, không thì chi tiết server. */
  const loi = (err: unknown): string => {
    const l = docLoi(err);
    const ma = l.code || (err instanceof Error ? err.message : '');
    // PIN sai: server trả số lần thử còn lại trước khi khóa (fields.so_lan_con_lai)
    const con_lai = ma === 'pin_khong_dung' ? (l.fields as Record<string, unknown[]> | undefined)?.so_lan_con_lai?.[0] : undefined;
    if (typeof con_lai === 'number') return t('loi.pin_khong_dung_con_lai', { so: con_lai });
    // Dữ liệu không hợp lệ: nêu trường và lý do đầu tiên để người dùng biết sửa chỗ nào
    if (ma === 'du_lieu_khong_hop_le') {
      const dau = thongDiepDauTien(l.fields);
      if (dau) {
        const nhan = tra(TU_DIEN[currentLang], `truong.${dau[0]}`);
        return nhan ? `${nhan}: ${dau[1]}` : dau[1];
      }
    }
    const ban_dich = ma ? tra(TU_DIEN[currentLang], `loi.${ma}`) : undefined;
    if (ban_dich) return ban_dich;
    if (l.status === 0 && !l.code && err instanceof TypeError) return t('chung.loiMang');
    if (l.status === 403) return t('chung.khongCoQuyen');
    return l.detail || t('chung.loiMang');
  };
  return { t, loi, lang: currentLang };
}
