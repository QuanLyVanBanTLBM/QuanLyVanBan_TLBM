/** Tiến trình ký của một lượt trình: cấp mở tuần tự, người trong cấp ký song song (#80 mục B, E). */
import { Badge } from '@components/common';
import { dinhDangNgay, trangThaiNguoiKy } from '@lib/signing/dinhDang';
import { useSigningT } from '@lib/signing/i18n';
import type { LuotTrinh } from '@lib/signing/types';
import { TrangThaiBadge } from './ChungUI';

export default function TienTrinh({ luot, toiId }: { luot: LuotTrinh; toiId?: number }) {
  const { t, lang } = useSigningT();
  return (
    <ol className="space-y-3" aria-label={t('chiTiet.tienTrinh')}>
      {luot.cap_ky.map((cap) => {
        const qua_han = cap.trang_thai === 'DANG_KY' && cap.han_xu_ly && new Date(cap.han_xu_ly) < new Date();
        return (
          <li key={cap.id} className={`rounded-lg border p-3 ${
            cap.trang_thai === 'DANG_KY' ? 'border-primary-border bg-primary-subtle/40' : 'border-border-subtle'}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-bold text-base text-main">
                {cap.cap_ky}. {cap.ten_cap_ky}
              </div>
              <div className="flex items-center gap-2">
                {cap.han_xu_ly && (
                  <span className={`text-sm ${qua_han ? 'text-danger font-bold' : 'text-secondary'}`}>
                    <i className="fa-regular fa-clock mr-1" aria-hidden="true" />
                    {t('chiTiet.han')}: {dinhDangNgay(cap.han_xu_ly, lang)}
                  </span>
                )}
                <TrangThaiBadge trangThai={cap.trang_thai} nhom="trangThaiCap" />
              </div>
            </div>
            <ul className="mt-2 space-y-1.5">
              {cap.nguoi_ky.map((n) => (
                <li key={n.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <span className={`font-semibold ${n.nguoi_ky === toiId ? 'text-primary' : 'text-main'}`}>
                      {n.ten_nguoi_ky}
                    </span>
                    {n.ten_chuc_vu && <span className="text-secondary"> · {n.ten_chuc_vu}</span>}
                    <span className="text-muted"> · {t(`vaiTro.${n.vai_tro_ky}`)}</span>
                    {n.chu_ky?.ghi_chu_ky && <div className="text-xs text-secondary italic break-words">“{n.chu_ky.ghi_chu_ky}”</div>}
                    {n.ly_do_tu_choi && <div className="text-xs text-danger break-words">{n.ly_do_tu_choi}</div>}
                  </div>
                  <div className="flex items-center gap-2">
                    {n.chu_ky?.ky_tre_han && <Badge variant="danger" size="sm">{t('chiTiet.treHan')}</Badge>}
                    {n.ngay_ky && <span className="text-xs text-secondary">{dinhDangNgay(n.ngay_ky, lang)}</span>}
                    <TrangThaiBadge trangThai={trangThaiNguoiKy(luot.trang_thai, n.trang_thai, Boolean(n.thoi_diem_mo))} />
                  </div>
                </li>
              ))}
            </ul>
          </li>
        );
      })}
    </ol>
  );
}
