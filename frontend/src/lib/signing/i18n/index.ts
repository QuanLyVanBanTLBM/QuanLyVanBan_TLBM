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
    const ban_dich = ma ? tra(TU_DIEN[currentLang], `loi.${ma}`) : undefined;
    if (ban_dich) return ban_dich;
    if (l.status === 0 && !l.code && err instanceof TypeError) return t('chung.loiMang');
    if (l.status === 403) return t('chung.khongCoQuyen');
    return l.detail || t('chung.loiMang');
  };
  return { t, loi, lang: currentLang };
}
