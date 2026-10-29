/**
 * Trang tài liệu: mọi tệp của các hồ sơ người dùng được xem — bản dự thảo, tệp từng lượt trình, tệp hoàn tất — kèm tìm
 * kiếm, lọc loại tệp và khoảng ngày, tải về (kiểm quyền ở máy chủ). Phân trang phía server như danh sách hồ sơ
 * (10 tệp mỗi trang; đổi bộ lọc thì về trang 1). Tệp lưu ở máy chủ theo trinh_ky/ và hoan_tat/<năm>/<tháng>/.
 */
import { useEffect, useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { Badge, Button, Card } from '@components/common';
import type { BadgeProps } from '@components/common/Badge';
import { DangTai, KhungModal, LoiTai, Rong, ThongBao } from '@components/signing/ChungUI';
import LocKhoangNgay from '@components/signing/LocKhoangNgay';
import { PhanTrang } from '@components/signing/PhanTrang';
import XemPdf from '@components/signing/XemPdf';
import { docLoi, SO_HO_SO_MOI_TRANG, signingApi } from '@lib/signing/api';
import { dinhDangNgay, LOP_O_NHAP, moTaVanBan, taiXuong, tenTepTaiVe } from '@lib/signing/dinhDang';
import { useTai } from '@lib/signing/hooks';
import { useSigningT, type HamDich } from '@lib/signing/i18n';
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
const TRE_TIM_KIEM_MS = 300;
const LOP_NHAN = 'mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-secondary';


function layTep(tep: TepTaiLieu): Promise<Blob> {
  if (tep.loai === 'HOAN_TAT') return signingApi.tepHoanTat(tep.trinh_ky);
  if (tep.loai === 'LUOT' && tep.luot) return signingApi.tepCuaLuot(tep.trinh_ky, tep.luot);
  return signingApi.tepGoc(tep.trinh_ky);
}

function nhanTep(tep: TepTaiLieu, t: HamDich): string {
  if (tep.loai === 'LUOT') {
    return tep.so_luot != null
      ? t('taiLieu.tenTep.LUOT', { so: tep.so_luot })
      : t('taiLieu.tenTep.luotKhongRo');
  }
  return t(`taiLieu.tenTep.${tep.loai}`);
}

export default function TaiLieuPage() {
  const { t, loi, lang } = useSigningT();
  const [loc, setLoc] = useState<BoLocTaiLieu>({});
  const [tuKhoa, setTuKhoa] = useState('');
  const [tepXem, setTepXem] = useState<TepTaiLieu | null>(null);
  const [duLieuXem, setDuLieuXem] = useState<{ buf: ArrayBuffer | null; dangTai: boolean; loi: unknown } | null>(null);
  const [taiVe, setTaiVe] = useState<{ dang: boolean; loi: unknown }>({ dang: false, loi: null });
  const [trang, setTrang] = useState(1);
  const nhanId = useId();
  const ds = useTai(() => signingApi.taiLieu(loc, trang).catch((err) => {
    if (trang > 1 && docLoi(err).status === 404) setTrang(1);  // trang cuối không còn: về trang 1
    throw err;
  }), [loc, trang]);
  const dsTep = ds.duLieu?.results;
  const dat = (thay_doi: BoLocTaiLieu) => {
    setLoc((cu) => ({ ...cu, ...thay_doi }));
    setTrang(1);
  };
  const coLoc = Object.values(loc).some(Boolean);

  // Gõ xong thì tự áp dụng (như danh sách hồ sơ); nút Lọc hoặc Enter áp dụng ngay
  useEffect(() => {
    const q = tuKhoa.trim();
    if (q === (loc.q ?? '')) return undefined;
    const hen = setTimeout(() => {
      setLoc((cu) => ({ ...cu, q }));
      setTrang(1);
    }, TRE_TIM_KIEM_MS);
    return () => clearTimeout(hen);
  }, [tuKhoa, loc.q]);

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
    setTaiVe({ dang: false, loi: null });
  };

  // Cùng nguồn với lúc xem (kiểm quyền ở máy chủ) và cùng tên tệp với cột "Tệp"
  const taiTepXem = async () => {
    if (!tepXem || taiVe.dang) return;
    setTaiVe({ dang: true, loi: null });
    try {
      taiXuong(await layTep(tepXem), tenTepTaiVe(tepXem.trinh_ky, tepXem.loai, tepXem.so_luot));
      setTaiVe({ dang: false, loi: null });
    } catch (err) {
      setTaiVe({ dang: false, loi: err });
    }
  };

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
          <LocKhoangNgay tuNgay={loc.tu_ngay} denNgay={loc.den_ngay} onDoi={dat} lopO="lg:col-span-2" />
          <div className="flex gap-2 lg:col-span-2">
            <Button type="submit" size="sm" icon="fa-filter">{t('danhSach.loc')}</Button>
            {coLoc && (
              <Button type="button" size="sm" variant="secondary" icon="fa-rotate-left" onClick={() => { setTuKhoa(''); setLoc({}); setTrang(1); }}>
                {t('danhSach.xoaLoc')}
              </Button>
            )}
          </div>
        </form>
      </Card>
      <Card className="p-4 space-y-3">
        {ds.dangTai && <DangTai />}
        {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
        {!ds.dangTai && !ds.loi && dsTep?.length === 0 && (
          <Rong icon="fa-folder-open">{t(coLoc ? 'taiLieu.khongKhopLoc' : 'taiLieu.rong')}</Rong>
        )}
        {!ds.dangTai && !ds.loi && !!dsTep?.length && (
          <>
          {/* Dưới 1280px: dạng thẻ (bảng 7 cột cần bề rộng đủ để không cắt ngày và tên tệp) */}
          <ul className="divide-y divide-border-subtle xl:hidden">
            {dsTep.map((tep) => (
              <li key={`the-${tep.loai}-${tep.trinh_ky}-${tep.luot ?? 0}`} className="space-y-1 py-3">
                <div className="flex items-start justify-between gap-2">
                  <button type="button" onClick={() => xemChiTiet(tep)}
                    className="min-w-0 break-words text-left font-semibold text-main hover:text-primary hover:underline line-clamp-3"
                    title={moTaVanBan(tep.van_ban, t)}>
                    {moTaVanBan(tep.van_ban, t)}
                  </button>
                  <Badge variant="info" size="sm">{t(`taiLieu.loai.${tep.loai}`)}</Badge>
                </div>
                <button type="button" onClick={() => xemChiTiet(tep)} title={t('chiTiet.xemChiTiet')}
                  className="block break-all text-left text-xs text-secondary hover:text-primary hover:underline">{nhanTep(tep, t)}</button>
                <div className="flex flex-wrap gap-x-2 text-xs text-muted">
                  <Link to={`/approvals/${tep.trinh_ky}`} className="font-medium text-secondary hover:text-primary hover:underline">{t('danhSach.maHoSo')} #{tep.trinh_ky}</Link>
                  <span>{tep.ten_quy_trinh}</span>
                  <span>{dinhDangNgay(tep.thoi_diem, lang)}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto xl:block">
            <table className="w-full min-w-[60rem] text-sm table-fixed">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-elevated/70 text-xs font-bold uppercase tracking-wider text-muted">
                  <th className="px-3 py-2.5 text-center whitespace-nowrap w-[11%]">{t('taiLieu.soHieu')}</th>
                  <th className="px-3.5 py-2.5 text-center w-[26%]">{t('taiLieu.trichYeu')}</th>
                  <th className="px-3 py-2.5 text-center whitespace-nowrap w-[17%]">{t('taiLieu.tep')}</th>
                  <th className="px-2.5 py-2.5 text-center whitespace-nowrap w-[9%]">{t('taiLieu.loaiTep')}</th>
                  <th className="px-3 py-2.5 text-center whitespace-nowrap w-[11%]">{t('danhSach.maHoSo')}</th>
                  <th className="px-3 py-2.5 text-center whitespace-nowrap w-[14%]">{t('danhSach.quyTrinh')}</th>
                  <th className="px-3 py-2.5 text-center whitespace-nowrap w-[12%]">{t('taiLieu.ngay')}</th>
                </tr>
              </thead>
              <tbody className="divide-y border-border-subtle">
                {dsTep.map((tep) => (
                  <tr key={`${tep.loai}-${tep.trinh_ky}-${tep.luot ?? 0}`} className="hover:bg-surface-hover/80 transition-colors">
                    <td className="px-3 py-3 text-center whitespace-nowrap" title={tep.van_ban.so_hieu}>
                      {tep.van_ban.so_hieu ? (
                        <button
                          type="button"
                          onClick={() => xemChiTiet(tep)}
                          className="font-semibold text-main hover:text-primary hover:underline cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded max-w-full truncate inline-block text-center"
                          title={t('chiTiet.xemChiTiet')}
                        >
                          <span className="truncate">{tep.van_ban.so_hieu}</span>
                        </button>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-3.5 py-3 text-left text-main" title={tep.van_ban.trich_yeu}>
                      <div className="line-clamp-2 break-words" title={tep.van_ban.trich_yeu}>
                        {tep.van_ban.trich_yeu || '—'}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <button
                        type="button"
                        onClick={() => xemChiTiet(tep)}
                        className="group inline-flex items-center justify-center gap-1.5 max-w-full text-secondary hover:text-primary transition-colors cursor-pointer rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-primary text-xs"
                        title={t('chiTiet.xemChiTiet')}
                      >
                        <i className={`fa-solid ${BIEU_TUONG[tep.loai]} text-xs shrink-0 opacity-70 group-hover:opacity-100 transition-opacity`} aria-hidden="true" />
                        <span className="truncate group-hover:underline underline-offset-2">{nhanTep(tep, t)}</span>
                      </button>
                    </td>
                    <td className="px-2.5 py-3 text-center whitespace-nowrap"><Badge variant={MAU_LOAI_TEP[tep.loai]} size="sm">{t(`taiLieu.loai.${tep.loai}`)}</Badge></td>
                    <td className="px-3 py-3 text-center whitespace-nowrap font-medium text-secondary">
                      <Link to={`/approvals/${tep.trinh_ky}`} className="hover:text-primary hover:underline">{t('danhSach.maHoSo')} #{tep.trinh_ky}</Link>
                    </td>
                    <td className="px-3 py-3 text-center text-secondary" title={tep.ten_quy_trinh}>
                      <div className="line-clamp-2 break-words">{tep.ten_quy_trinh}</div>
                    </td>
                    <td className="px-3 py-3 text-center text-muted whitespace-nowrap text-xs">
                      <span>{dinhDangNgay(tep.thoi_diem, lang)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PhanTrang trang={trang} soMoiTrang={SO_HO_SO_MOI_TRANG} tong={ds.duLieu?.count ?? 0} onDoi={setTrang}
            khoaTomTat="phanTrang.tomTatTep" />
          </>
        )}
      </Card>
      {tepXem && (
        <KhungModal nhanId={nhanId} onDong={dongXem} lopNen="p-2 sm:p-4"
          lopKhung="flex flex-col w-full max-w-5xl h-[92vh] rounded-2xl border border-border-subtle bg-surface-elevated overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3.5 bg-surface shrink-0">
              <div className="min-w-0 flex-1 pr-4">
                <div className="flex items-center gap-2">
                  <i className={`fa-solid ${BIEU_TUONG[tepXem.loai]} text-lg shrink-0`} aria-hidden="true" />
                  <h2 id={nhanId} className="text-base sm:text-lg font-bold text-main truncate">{nhanTep(tepXem, t)}</h2>
                  <Badge variant={MAU_LOAI_TEP[tepXem.loai]} size="sm">{t(`taiLieu.loai.${tepXem.loai}`)}</Badge>
                </div>
                <div className="text-xs text-secondary truncate mt-0.5">
                  <Link to={`/approvals/${tepXem.trinh_ky}`} className="font-bold text-primary hover:underline mr-2">
                    {t('danhSach.maHoSo')} #{tepXem.trinh_ky}
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
            <div className="flex items-center justify-end gap-2 border-t border-border-subtle px-5 py-2.5 bg-surface text-xs text-muted shrink-0">
              {taiVe.loi != null && <div className="mr-auto min-w-0"><ThongBao>{loi(taiVe.loi)}</ThongBao></div>}
              <Button size="sm" variant="secondary" icon="fa-download" isLoading={taiVe.dang} onClick={taiTepXem}>
                {t('chung.taiVe')}
              </Button>
              <Button size="sm" variant="ghost" onClick={dongXem}>
                {t('chung.dong')}
              </Button>
            </div>
        </KhungModal>
      )}
    </div>
  );
}
