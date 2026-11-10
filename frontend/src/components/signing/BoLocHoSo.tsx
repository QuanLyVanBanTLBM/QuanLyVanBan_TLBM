import { useEffect, useState } from 'react';
import { Button } from '@components/common';
import LocKhoangNgay from '@components/signing/LocKhoangNgay';
import { TruongLoc } from '@components/signing/BoLocTrinhKy';
import { signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { BoLocHoSo as BoLocHoSoState, LocNhanh, ThongKeHoSo } from '@lib/signing/types';

type Hop = 'can_toi_ky' | 'toi_gui' | 'tat_ca';

const THE_NHANH: { khoa: LocNhanh | ''; icon: string }[] = [
  { khoa: '', icon: 'fa-layer-group' },
  { khoa: 'cho_ky', icon: 'fa-hourglass-half' },
  { khoa: 'qua_han', icon: 'fa-triangle-exclamation' },
  { khoa: 'hoan_thanh', icon: 'fa-circle-check' },
  { khoa: 'tra_lai', icon: 'fa-rotate-left' },
];
const TRE_TIM_KIEM_MS = 300;

function TheNhanh({ thongKe, chon, onChon }: {
  thongKe: ThongKeHoSo | null; chon: string; onChon: (khoa: LocNhanh | '') => void;
}) {
  const { t } = useSigningT();
  return (
    <div className="flex flex-wrap gap-1.5 sm:gap-2" role="group" aria-label={t('danhSach.locNhanh')}>
      {THE_NHANH.map(({ khoa, icon }) => {
        const so = thongKe ? thongKe[khoa || 'tat_ca'] : undefined;
        const dangChon = chon === khoa;
        return (
          <button key={khoa || 'tat_ca'} type="button" aria-pressed={dangChon} onClick={() => onChon(khoa)}
            className={`flex items-center gap-1.5 sm:gap-2 rounded-full border px-2.5 sm:px-3.5 py-1 sm:py-1.5 text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              dangChon
                ? 'border-primary bg-primary text-white shadow-sm'
                : 'border-border-subtle bg-surface text-secondary hover:border-primary/40 hover:text-main hover:bg-surface-hover'}`}>
            <i className={`fa-solid ${icon}`} aria-hidden="true" />
            <span>{t(`danhSach.nhanh.${khoa || 'tat_ca'}`)}</span>
            {so !== undefined && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                dangChon ? 'bg-white/20 text-white' : 'bg-surface-elevated text-secondary'}`}>
                {so}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default function BoLocHoSo({ hop, thongKe, loc, capNhat, xoaHet }: {
  hop: Hop;
  thongKe: ThongKeHoSo | null;
  loc: BoLocHoSoState;
  capNhat: (thay_doi: BoLocHoSoState) => void;
  xoaHet: () => void;
}) {
  const { t } = useSigningT();
  const [tuKhoa, setTuKhoa] = useState(loc.q ?? '');
  const [moLocThem, setMoLocThem] = useState(false);
  const quyTrinh = useTai(() => signingApi.quyTrinh(), []);
  const donViApDung = useTai(() => signingApi.donViApDungTheoHop(hop), [hop]);
  const coLoc = Object.values(loc).some(Boolean);
  const soLocThem = [loc.quy_trinh, loc.don_vi_ap_dung, loc.tu_ngay, loc.den_ngay].filter(Boolean).length;

  useEffect(() => {
    const q = tuKhoa.trim();
    if (q === (loc.q ?? '')) return undefined;
    const hen = setTimeout(() => capNhat({ q }), TRE_TIM_KIEM_MS);
    return () => clearTimeout(hen);
  }, [tuKhoa, loc.q, capNhat]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 basis-full lg:flex-1 lg:basis-0">
          <TheNhanh thongKe={thongKe} chon={loc.nhanh ?? ''} onChon={(khoa) => capNhat({ nhanh: khoa })} />
        </div>
        <div className="relative block w-full sm:w-72">
          <TruongLoc nhan={t('danhSach.timKiem')} icon="fa-magnifying-glass">
            <span className="relative block">
              <input className={`${LOP_O_NHAP} pl-9 pr-8`} type="search" value={tuKhoa} placeholder={t('danhSach.goiYTim')}
                onChange={(e) => setTuKhoa(e.target.value)} />
              <i className="fa-solid fa-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted" aria-hidden="true" />
            </span>
          </TruongLoc>
          {tuKhoa && (
            <button type="button" className="absolute bottom-2 right-2.5 p-1 text-xs text-muted hover:text-main"
              aria-label={t('danhSach.xoaTuKhoa')} onClick={() => { setTuKhoa(''); capNhat({ q: '' }); }}>
              <i className="fa-solid fa-xmark" aria-hidden="true" />
            </button>
          )}
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Button type="button" size="sm" variant="secondary" icon="fa-sliders" aria-expanded={moLocThem}
            className="flex-1 justify-center sm:flex-initial"
            onClick={() => setMoLocThem((m) => !m)}>
            {t('danhSach.locThem')}{soLocThem > 0 && ` (${soLocThem})`}
          </Button>
          {coLoc && (
            <Button type="button" size="sm" variant="secondary" icon="fa-rotate-left"
              className="flex-1 justify-center sm:flex-initial"
              onClick={() => { setTuKhoa(''); xoaHet(); }}>
              {t('danhSach.xoaLoc')}
            </Button>
          )}
        </div>
      </div>
      {moLocThem && (
        <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <TruongLoc nhan={t('danhSach.quyTrinh')} icon="fa-diagram-project">
            <select className={LOP_O_NHAP} value={loc.quy_trinh ?? ''} onChange={(e) => capNhat({ quy_trinh: e.target.value })}>
              <option value="">{t('danhSach.tatCa')}</option>
              {quyTrinh.duLieu?.map((q) => <option key={q.id} value={String(q.id)}>{q.ten_quy_trinh} (v{q.phien_ban})</option>)}
            </select>
          </TruongLoc>
          <TruongLoc nhan={t('danhSach.donViApDung')} icon="fa-building">
            <select className={LOP_O_NHAP} value={loc.don_vi_ap_dung ?? ''}
              onChange={(e) => capNhat({ don_vi_ap_dung: e.target.value })}>
              <option value="">{t('danhSach.tatCa')}</option>
              {donViApDung.duLieu?.map((dv) => (
                <option key={dv.id} value={String(dv.id)}>{dv.ten} ({dv.ten_khoi})</option>
              ))}
            </select>
          </TruongLoc>
          <LocKhoangNgay tuNgay={loc.tu_ngay} denNgay={loc.den_ngay} onDoi={capNhat} />
        </div>
      )}
    </div>
  );
}
