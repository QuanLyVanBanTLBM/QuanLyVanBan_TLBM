/**
 * Trang tài liệu: mọi tệp của các hồ sơ người dùng được xem — bản dự thảo, tệp từng lượt trình, tệp hoàn tất — kèm tìm
 * kiếm, lọc loại tệp và khoảng ngày, tải về (kiểm quyền ở máy chủ). Tệp lưu ở máy chủ theo trinh_ky/ và hoan_tat/<năm>/<tháng>/.
 */
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { Badge, Button, Card } from '@components/common';
import type { BadgeProps } from '@components/common/Badge';
import { DangTai, LoiTai, Rong } from '@components/signing/ChungUI';
import XemPdf from '@components/signing/XemPdf';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { BoLocTaiLieu, LoaiTepTaiLieu, TepTaiLieu } from '@lib/signing/types';

const LOAI: LoaiTepTaiLieu[] = ['DU_THAO', 'LUOT', 'HOAN_TAT'];
const BIEU_TUONG: Record<LoaiTepTaiLieu, string> = {
  DU_THAO: 'fa-file-pen text-warning-text',
  LUOT: 'fa-file-pdf text-primary',
  HOAN_TAT: 'fa-file-circle-check text-success',
};
const MAU_LOAI_TEP: Record<LoaiTepTaiLieu, BadgeProps['variant']> = {
  DU_THAO: 'warning',
  LUOT: 'primary',
  HOAN_TAT: 'success',
};
const LOP_NHAN = 'mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-secondary';


function layTep(tep: TepTaiLieu): Promise<Blob> {
  if (tep.loai === 'HOAN_TAT') return signingApi.tepHoanTat(tep.trinh_ky);
  if (tep.loai === 'LUOT' && tep.luot) return signingApi.tepCuaLuot(tep.trinh_ky, tep.luot);
  return signingApi.tepGoc(tep.trinh_ky);
}

export default function TaiLieuPage() {
  const { t, loi, lang } = useSigningT();
  const [loc, setLoc] = useState<BoLocTaiLieu>({});
  const [tuKhoa, setTuKhoa] = useState('');
  const [tepXem, setTepXem] = useState<TepTaiLieu | null>(null);
  const [duLieuXem, setDuLieuXem] = useState<{ buf: ArrayBuffer | null; dangTai: boolean; loi: unknown } | null>(null);
  const ds = useTai(() => signingApi.taiLieu(loc), [loc]);
  const dat = (thay_doi: BoLocTaiLieu) => setLoc((cu) => ({ ...cu, ...thay_doi }));
  const coLoc = Object.values(loc).some(Boolean);


  const xemChiTiet = async (tep: TepTaiLieu) => {
    setTepXem(tep);
    setDuLieuXem({ buf: null, dangTai: true, loi: null });
    try {
      const blob = await layTep(tep);
      const buf = await blob.arrayBuffer();
      setDuLieuXem({ buf, dangTai: false, loi: null });
    } catch (err) {
      setDuLieuXem({ buf: null, dangTai: false, loi: err });
    }
  };

  const dongXem = () => {
    setTepXem(null);
    setDuLieuXem(null);
  };

  useEffect(() => {
    if (!tepXem) return undefined;
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && dongXem();
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [tepXem]);

  return (
    <div className="space-y-4">
      <Card className="p-4 sm:p-5">
        <form className="grid grid-cols-1 items-end gap-3 md:grid-cols-2 lg:grid-cols-12"
          onSubmit={(e) => { e.preventDefault(); dat({ q: tuKhoa.trim() }); }}>
          <label className="block lg:col-span-4">
            <span className={LOP_NHAN}><i className="fa-solid fa-magnifying-glass text-primary" aria-hidden="true" />{t('danhSach.timKiem')}</span>
            <span className="relative block">
              <input className={`${LOP_O_NHAP} pl-9`} type="search" value={tuKhoa} placeholder={t('taiLieu.goiYTim')}
                onChange={(e) => setTuKhoa(e.target.value)} />
              <i className="fa-solid fa-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted" aria-hidden="true" />
            </span>
          </label>
          <label className="block lg:col-span-2">
            <span className={LOP_NHAN}><i className="fa-solid fa-file text-primary" aria-hidden="true" />{t('taiLieu.loaiTep')}</span>
            <select className={LOP_O_NHAP} value={loc.loai ?? ''} onChange={(e) => dat({ loai: e.target.value as LoaiTepTaiLieu | '' })}>
              <option value="">{t('danhSach.tatCa')}</option>
              {LOAI.map((l) => <option key={l} value={l}>{t(`taiLieu.loai.${l}`)}</option>)}
            </select>
          </label>
          <label className="block lg:col-span-2">
            <span className={LOP_NHAN}>{t('danhSach.tuNgay')}</span>
            <input className={LOP_O_NHAP} type="date" value={loc.tu_ngay ?? ''} onChange={(e) => dat({ tu_ngay: e.target.value })} />
          </label>
          <label className="block lg:col-span-2">
            <span className={LOP_NHAN}>{t('danhSach.denNgay')}</span>
            <input className={LOP_O_NHAP} type="date" value={loc.den_ngay ?? ''} onChange={(e) => dat({ den_ngay: e.target.value })} />
          </label>
          <div className="flex gap-2 lg:col-span-2">
            <Button type="submit" size="sm" icon="fa-filter">{t('danhSach.loc')}</Button>
            {coLoc && (
              <Button type="button" size="sm" variant="secondary" icon="fa-rotate-left" onClick={() => { setTuKhoa(''); setLoc({}); }}>
                {t('danhSach.xoaLoc')}
              </Button>
            )}
          </div>
        </form>
      </Card>
      <Card className="p-4 space-y-3">
        {ds.dangTai && <DangTai />}
        {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
        {!ds.dangTai && !ds.loi && ds.duLieu?.length === 0 && (
          <Rong icon="fa-folder-open">{t(coLoc ? 'taiLieu.khongKhopLoc' : 'taiLieu.rong')}</Rong>
        )}
        {!ds.dangTai && !ds.loi && !!ds.duLieu?.length && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm table-fixed">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-elevated/70 text-xs font-bold uppercase tracking-wider text-muted">
                  <th className="px-3 py-2.5 text-left whitespace-nowrap w-[13%]">{t('taiLieu.soHieu')}</th>
                  <th className="px-3.5 py-2.5 text-left w-[32%]">{t('taiLieu.trichYeu')}</th>
                  <th className="px-3 py-2.5 text-left whitespace-nowrap w-[17%]">{t('taiLieu.tep')}</th>
                  <th className="px-2.5 py-2.5 text-center whitespace-nowrap w-[9%]">{t('taiLieu.loaiTep')}</th>
                  <th className="px-3 py-2.5 text-left whitespace-nowrap w-[7%]">{t('danhSach.maHoSo')}</th>
                  <th className="px-3 py-2.5 text-left whitespace-nowrap w-[14%]">{t('danhSach.quyTrinh')}</th>
                  <th className="px-3 py-2.5 text-left whitespace-nowrap w-[8%]">{t('taiLieu.ngay')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {ds.duLieu.map((tep) => (
                  <tr key={`${tep.loai}-${tep.trinh_ky}-${tep.luot ?? 0}`} className="hover:bg-surface-hover/80 transition-colors">
                    <td className="px-3 py-3 text-left whitespace-nowrap truncate" title={tep.van_ban.so_hieu}>
                      {tep.van_ban.so_hieu ? (
                        <button
                          type="button"
                          onClick={() => xemChiTiet(tep)}
                          className="font-semibold text-main hover:text-primary hover:underline cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded max-w-full truncate"
                          title={t('chiTiet.xemChiTiet')}
                        >
                          <span className="truncate">{tep.van_ban.so_hieu}</span>
                        </button>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-3.5 py-3 text-left text-main truncate" title={tep.van_ban.trich_yeu}>
                      <div className="truncate text-left">
                        {tep.van_ban.trich_yeu || '—'}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-left whitespace-nowrap truncate">
                      <button
                        type="button"
                        onClick={() => xemChiTiet(tep)}
                        className="group inline-flex items-center gap-1.5 max-w-full text-left text-secondary hover:text-primary transition-colors cursor-pointer rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-primary truncate text-xs"
                        title={t('chiTiet.xemChiTiet')}
                      >
                        <i className={`fa-solid ${BIEU_TUONG[tep.loai]} text-xs shrink-0 opacity-70 group-hover:opacity-100 transition-opacity`} aria-hidden="true" />
                        <span className="truncate group-hover:underline underline-offset-2">{tep.ten_tep}</span>
                      </button>
                    </td>
                    <td className="px-2.5 py-3 text-center whitespace-nowrap"><Badge variant={MAU_LOAI_TEP[tep.loai]} size="sm">{t(`taiLieu.loai.${tep.loai}`)}</Badge></td>
                    <td className="px-3 py-3 text-left whitespace-nowrap font-medium text-secondary">
                      <Link to={`/approvals/${tep.trinh_ky}`} className="hover:text-primary hover:underline">#{tep.trinh_ky}</Link>
                    </td>
                    <td className="px-3 py-3 text-left text-secondary whitespace-nowrap truncate" title={tep.ten_quy_trinh}>
                      {tep.ten_quy_trinh}
                    </td>
                    <td className="px-3 py-3 text-left text-muted whitespace-nowrap text-xs">
                      <span>{dinhDangNgay(tep.thoi_diem, lang)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {tepXem && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-backdrop p-2 sm:p-4 animate-fade-in">
          <div
            role="dialog"
            aria-modal="true"
            className="signing-zoom flex flex-col w-full max-w-5xl h-[92vh] rounded-2xl border border-border-subtle bg-surface-elevated shadow-2xl animate-slide-in-bottom overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3.5 bg-surface shrink-0">
              <div className="min-w-0 flex-1 pr-4">
                <div className="flex items-center gap-2">
                  <i className={`fa-solid ${BIEU_TUONG[tepXem.loai]} text-lg shrink-0`} aria-hidden="true" />
                  <h2 className="text-base sm:text-lg font-bold text-main truncate">{tepXem.ten_tep}</h2>
                  <Badge variant={MAU_LOAI_TEP[tepXem.loai]} size="sm">{t(`taiLieu.loai.${tepXem.loai}`)}</Badge>
                </div>
                <div className="text-xs text-secondary truncate mt-0.5">
                  <Link to={`/approvals/${tepXem.trinh_ky}`} className="font-bold text-primary hover:underline mr-2">
                    #{tepXem.trinh_ky}
                  </Link>
                  {[tepXem.van_ban.so_hieu, tepXem.van_ban.trich_yeu].filter(Boolean).join(' — ') || tepXem.ten_quy_trinh}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={dongXem}
                  className="rounded-full p-2 text-secondary hover:text-main hover:bg-surface-hover transition-colors cursor-pointer"
                  aria-label={t('chung.dong')}
                >
                  <i className="fa-solid fa-xmark text-base" aria-hidden="true" />
                </button>
              </div>
            </div>

            {/* Nội dung tài liệu PDF */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-surface-subtle">
              {duLieuXem?.dangTai && <DangTai />}
              {duLieuXem?.loi && <LoiTai thongBao={loi(duLieuXem.loi)} onThuLai={() => xemChiTiet(tepXem)} />}
              {duLieuXem?.buf && (
                <div className="max-w-4xl mx-auto bg-surface rounded-xl shadow-sm border border-border-subtle p-2 sm:p-4">
                  <XemPdf duLieu={duLieuXem.buf} />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end border-t border-border-subtle px-5 py-2.5 bg-surface text-xs text-muted shrink-0">
              <Button size="sm" variant="ghost" onClick={dongXem}>
                {t('chung.dong')}
              </Button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
