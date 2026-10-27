/**
 * Thanh phân trang của danh sách hồ sơ và trang văn bản công khai (cùng kiểu các module khác: trang trước/sau, "Trang x/y", khoảng đang xem).
 * Chỉ hiện khi có hơn một trang.
 */
import { Button } from '@components/common';
import { useSigningT } from '@lib/signing/i18n';

export function PhanTrang({ trang, soMoiTrang, tong, onDoi, khoaTomTat = 'phanTrang.tomTat' }: {
  trang: number; soMoiTrang: number; tong: number; onDoi: (trang: number) => void;
  /** Khóa i18n của dòng "Hiển thị x–y trên z …" (mặc định đếm hồ sơ) */
  khoaTomTat?: string;
}) {
  const { t } = useSigningT();
  const tongTrang = Math.max(1, Math.ceil(tong / soMoiTrang));
  if (tongTrang <= 1) return null;
  const dau = (trang - 1) * soMoiTrang + 1;
  const cuoi = Math.min(trang * soMoiTrang, tong);
  return (
    <nav className="flex flex-col gap-3 border-t border-border-subtle pt-3 sm:flex-row sm:items-center sm:justify-between"
      aria-label={t('phanTrang.nhan')}>
      <p className="m-0 text-xs text-muted">{t(khoaTomTat, { dau, cuoi, tong })}</p>
      <div className="flex items-center gap-2">
        <Button type="button" size="sm" variant="secondary" icon="fa-chevron-left" disabled={trang <= 1}
          onClick={() => onDoi(trang - 1)}>
          {t('phanTrang.truoc')}
        </Button>
        <span className="min-w-20 text-center text-xs font-bold text-secondary" aria-current="page">
          {t('phanTrang.trang', { trang, tong: tongTrang })}
        </span>
        <Button type="button" size="sm" variant="secondary" icon="fa-chevron-right" iconPosition="right"
          disabled={trang >= tongTrang} onClick={() => onDoi(trang + 1)}>
          {t('phanTrang.sau')}
        </Button>
      </div>
    </nav>
  );
}
