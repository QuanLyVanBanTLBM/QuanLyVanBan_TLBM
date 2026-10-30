/**
 * Danh sách hồ sơ: "Cần tôi ký duyệt", "Tôi đã gửi trình", "Văn bản theo quyền" (#80 mục E) kèm bộ lọc:
 * thẻ trạng thái có số lượng (#275 mục 5: đang chờ ký, quá hạn, đã ký xong, trả lại để sửa; hồ sơ nháp, không đồng ý,
 * đã hủy chỉ hiện ở "Tất cả"), ô tìm kiếm tự áp dụng và phần "Lọc thêm" thu gọn (quy trình, khoảng ngày).
 * Hộp rỗng và chưa lọc thì không hiện khối lọc.
 * Danh sách phân trang phía server (10 hồ sơ mỗi trang); đổi bộ lọc thì về trang 1 (mỗi hộp là một route riêng).
 */
import { useCallback, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import TaiLieuPage from './TaiLieuPage';
import { Card } from '@components/common';
import BoLocHoSo from '@components/signing/BoLocHoSo';
import { BoLocKhung } from '@components/signing/BoLocTrinhKy';
import { DangTai, LoiTai, Rong, TrangThaiHoSo } from '@components/signing/ChungUI';
import { PhanTrang } from '@components/signing/PhanTrang';
import { docLoi, SO_HO_SO_MOI_TRANG, signingApi } from '@lib/signing/api';
import { dinhDangNgay, moTaVanBan } from '@lib/signing/dinhDang';
import { useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { BoLocHoSo as BoLocHoSoState } from '@lib/signing/types';

type Hop = 'can_toi_ky' | 'toi_gui' | 'tat_ca';

export default function DanhSachPage({ hop }: { hop: Hop }) {
  const { t, loi, lang } = useSigningT();
  const [searchParams, setSearchParams] = useSearchParams();
  const cheDo = hop === 'tat_ca' && searchParams.get('che_do') === 'tep' ? 'tep' : 'ho_so';

  const doiCheDo = (mode: 'ho_so' | 'tep') => {
    const params = new URLSearchParams(searchParams);
    if (mode === 'tep') {
      params.set('che_do', 'tep');
    } else {
      params.delete('che_do');
    }
    setSearchParams(params);
  };

  const [loc, setLoc] = useState<BoLocHoSoState>({});
  const [trang, setTrang] = useState(1);
  // Số trên các thẻ theo cùng từ khóa, quy trình, đơn vị và khoảng ngày với danh sách (không theo thẻ đang chọn)
  const dem = useTai(() => signingApi.thongKe(hop, {
    q: loc.q, quy_trinh: loc.quy_trinh, don_vi_ap_dung: loc.don_vi_ap_dung, tu_ngay: loc.tu_ngay, den_ngay: loc.den_ngay,
  }), [hop, loc.q, loc.quy_trinh, loc.don_vi_ap_dung, loc.tu_ngay, loc.den_ngay]);
  // Trang đang xem không còn (dữ liệu giảm sau khi tải trang) thì về trang 1 thay vì báo lỗi
  const ds = useTai(() => signingApi.danhSach(hop, loc, trang).catch((err) => {
    if (trang > 1 && docLoi(err).status === 404) setTrang(1);
    throw err;
  }), [hop, loc, trang]);
  const hoSo = ds.duLieu?.results;
  const rong = { can_toi_ky: 'danhSach.rongCanToiKy', toi_gui: 'danhSach.rongToiGui', tat_ca: 'danhSach.rongTatCa' }[hop];
  const coLoc = Object.values(loc).some(Boolean);
  const hopRong = dem.duLieu?.tat_ca === 0 && !coLoc;
  const capNhat = useCallback((thay_doi: BoLocHoSoState) => {
    setLoc((cu) => ({ ...cu, ...thay_doi }));
    setTrang(1);
  }, []);
  const xoaHet = useCallback(() => {
    setLoc({});
    setTrang(1);
  }, []);

  return (
    <div className="space-y-4">
      {hop === 'tat_ca' && (
        <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
          <div className="inline-flex rounded-lg bg-surface-subtle p-1 border border-border-subtle">
            <button
              type="button"
              onClick={() => doiCheDo('ho_so')}
              className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                cheDo === 'ho_so'
                  ? 'bg-primary text-white shadow-xs'
                  : 'text-secondary hover:text-main hover:bg-surface'
              }`}
            >
              <i className="fa-solid fa-folder-open text-xs" aria-hidden="true" />
              <span>{t('danhSach.cheDoHoSo')}</span>
            </button>
            <button
              type="button"
              onClick={() => doiCheDo('tep')}
              className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                cheDo === 'tep'
                  ? 'bg-primary text-white shadow-xs'
                  : 'text-secondary hover:text-main hover:bg-surface'
              }`}
            >
              <i className="fa-solid fa-folder-tree text-xs" aria-hidden="true" />
              <span>{t('danhSach.cheDoTep')}</span>
            </button>
          </div>
        </div>
      )}

      {cheDo === 'tep' ? (
        <TaiLieuPage />
      ) : (
        <>
          {!hopRong && (
            <BoLocKhung>
              <BoLocHoSo hop={hop} thongKe={dem.duLieu} loc={loc} capNhat={capNhat} xoaHet={xoaHet} />
            </BoLocKhung>
          )}
          <Card className="p-4 space-y-3">
            {ds.dangTai && <DangTai />}
            {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
            {!ds.dangTai && !ds.loi && hoSo?.length === 0 && <Rong>{t(coLoc ? 'danhSach.khongKhopLoc' : rong)}</Rong>}
            {!ds.dangTai && !ds.loi && !!hoSo?.length && (
          <>
          {/* Dưới 1024px (điện thoại, máy tính bảng): thẻ thay cho bảng để luôn thấy trạng thái, người đang chờ, hạn chót */}
          <ul className="space-y-2 lg:hidden" aria-label={t('danhSach.vanBan')}>
            {hoSo.map((h) => (
              <li key={h.id} className="rounded-lg border border-border-subtle p-3">
                <Link to={`/approvals/${h.id}`} title={moTaVanBan(h.van_ban, t)}
                  className="block font-semibold text-main hover:text-primary break-words line-clamp-3">
                  {moTaVanBan(h.van_ban, t)}
                  {h.van_ban_id == null && <span className="ml-2 rounded-full bg-info-subtle px-2 py-0.5 text-xs text-info">{t('danhSach.taiLieuDocLap')}</span>}
                </Link>
                <div className="text-xs text-muted break-words">{t('danhSach.maHoSo')} #{h.id} · {h.ten_quy_trinh}</div>
                <div className="flex flex-wrap items-center gap-2"><TrangThaiHoSo hoSo={h} /></div>
                <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1.5 text-xs text-secondary pt-1 border-t border-border-subtle">
                  <dt>{t('danhSach.dangCho')}</dt>
                  <dd className="text-main break-words">
                    {h.dang_cho.length > 0 ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-elevated text-main border border-border-subtle px-2 py-0.5 text-xs font-medium">
                        <i className="fa-regular fa-clock text-warning text-xs shrink-0" aria-hidden="true" />
                        <span>{h.dang_cho.map((d) => d.ten_nguoi_ky).join(', ')}</span>
                      </span>
                    ) : (
                      '—'
                    )}
                  </dd>
                  <dt>{t('danhSach.nguoiTao')}</dt><dd className="text-main break-words">{h.ten_nguoi_tao}</dd>
                  <dt>{t('danhSach.hanChot')}</dt>
                  <dd className="text-main">
                    {dinhDangNgay(h.han_chot, lang)}
                    {!h.han_chot && h.han_xu_ly_cap && (
                      <span className="block text-xs text-secondary">{t('danhSach.hanCap')}: {dinhDangNgay(h.han_xu_ly_cap, lang)}</span>
                    )}
                  </dd>
                </dl>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full text-sm text-left table-fixed min-w-[48rem]">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-elevated/70 text-xs font-bold uppercase tracking-wider text-muted">
                  <th className="px-3.5 py-2 text-center w-[44%]">{t('danhSach.vanBan')}</th>
                  <th className="px-2 py-2 text-center whitespace-nowrap w-[14%]">{t('danhSach.trangThai')}</th>
                  <th className="px-2 py-2 text-center whitespace-nowrap w-[16%]">{t('danhSach.dangCho')}</th>
                  <th className="px-2.5 py-2 text-center whitespace-nowrap w-[13%]">{t('danhSach.nguoiTao')}</th>
                  <th className="px-2.5 py-2 text-center whitespace-nowrap w-[13%]">{t('danhSach.hanChot')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {hoSo.map((h) => (
                  <tr key={h.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-3.5 py-2 truncate">
                      <Link to={`/approvals/${h.id}`} className="font-semibold text-main hover:text-primary transition-colors flex items-center gap-1.5 text-base truncate" title={moTaVanBan(h.van_ban, t)}>
                        <i className="fa-solid fa-file-contract text-primary/70 text-sm shrink-0" aria-hidden="true" />
                        <span className="truncate">{moTaVanBan(h.van_ban, t)}</span>
                        {h.van_ban_id == null && <span className="shrink-0 rounded-full bg-info-subtle px-2 py-0.5 text-xs text-info">{t('danhSach.taiLieuDocLap')}</span>}
                      </Link>
                      <div className="mt-0.5 truncate text-xs text-muted" title={h.ten_quy_trinh}>{t('danhSach.maHoSo')} #{h.id} · {h.ten_quy_trinh}</div>
                    </td>
                    <td className="px-2 py-2 text-center"><TrangThaiHoSo hoSo={h} /></td>
                    <td className="px-2 py-2 text-center whitespace-nowrap truncate">
                      {h.dang_cho.length > 0 ? (
                        <div className="inline-flex items-center justify-center max-w-full truncate">
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-elevated text-main border border-border-subtle px-2.5 py-0.5 text-xs font-medium max-w-full truncate shadow-2xs">
                            <i className="fa-regular fa-clock text-warning text-xs shrink-0" aria-hidden="true" />
                            <span className="truncate" title={h.dang_cho.map((d) => d.ten_nguoi_ky).join(', ')}>
                              {h.dang_cho.map((d) => d.ten_nguoi_ky).join(', ')}
                            </span>
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-2.5 py-2 text-secondary whitespace-nowrap truncate text-center">
                      <div className="flex items-center justify-center gap-1.5 truncate">
                        <i className="fa-regular fa-user text-muted text-xs shrink-0" aria-hidden="true" />
                        <span className="truncate">{h.ten_nguoi_tao}</span>
                      </div>
                    </td>
                    <td className="px-2.5 py-2 text-secondary whitespace-nowrap text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <i className="fa-regular fa-calendar text-muted text-xs shrink-0" aria-hidden="true" />
                        <span>{dinhDangNgay(h.han_chot, lang)}</span>
                      </div>
                      {/* Hồ sơ không đặt hạn chót: vẫn cho biết hạn xử lý của cấp đang ký */}
                      {!h.han_chot && h.han_xu_ly_cap && (
                        <div className="mt-0.5 text-xs text-muted text-center">{t('danhSach.hanCap')}: {dinhDangNgay(h.han_xu_ly_cap, lang)}</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PhanTrang trang={trang} soMoiTrang={SO_HO_SO_MOI_TRANG} tong={ds.duLieu?.count ?? 0} onDoi={setTrang} />
          </>
        )}
      </Card>
        </>
      )}
    </div>
  );
}
