/**
 * Phân hệ Trình ký duyệt nội bộ (Nhóm 5, #80 mục E) dưới đường dẫn /approvals/*.
 * Tab chỉ là bộ lọc hiển thị; quyền đọc/ghi do server kiểm ở từng API.
 */
import { lazy, Suspense, useMemo } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { DangTai, LoiTai } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { coQuyen, SigningContext, useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';

const DanhSachPage = lazy(() => import('./DanhSachPage'));
const TaoHoSoPage = lazy(() => import('./TaoHoSoPage'));
const ChiTietPage = lazy(() => import('./ChiTietPage'));
const QuyTrinhPage = lazy(() => import('./QuyTrinhPage'));
const KhoaPage = lazy(() => import('./KhoaPage'));

export default function SigningModule() {
  const { t, loi } = useSigningT();
  const toi = useTai(() => signingApi.toi());
  const ngu_canh = useMemo(() => ({ toi: toi.duLieu, taiLaiToi: toi.tai }), [toi.duLieu, toi.tai]);

  const tab = [
    { den: '/approvals', nhan: t('nav.canToiKy'), icon: 'fa-pen-nib', end: true },
    { den: '/approvals/toi-gui', nhan: t('nav.toiGui'), icon: 'fa-paper-plane' },
    { den: '/approvals/tat-ca', nhan: t('nav.tatCa'), icon: 'fa-folder-open' },
    ...(coQuyen(toi.duLieu, 'add_trinhky') ? [{ den: '/approvals/tao-moi', nhan: t('nav.taoMoi'), icon: 'fa-plus' }] : []),
    ...(coQuyen(toi.duLieu, 'manage_signing_process') || coQuyen(toi.duLieu, 'view_trinhky')
      ? [{ den: '/approvals/quy-trinh', nhan: t('nav.quyTrinh'), icon: 'fa-diagram-project' }] : []),
    ...(coQuyen(toi.duLieu, 'sign_trinhky') ? [{ den: '/approvals/khoa', nhan: t('nav.khoaCuaToi'), icon: 'fa-key' }] : []),
  ];

  return (
    <SigningContext.Provider value={ngu_canh}>
      <div className="mx-auto max-w-7xl space-y-4 p-4 md:p-6">
        <header className="space-y-1">
          <h1 className="text-xl font-bold text-main">
            <i className="fa-solid fa-file-signature mr-2 text-primary" aria-hidden="true" />{t('tieuDe')}
          </h1>
          <p className="text-sm text-secondary">{t('moTa')}</p>
        </header>
        <nav className="flex flex-wrap gap-1 border-b border-border-subtle" aria-label={t('tieuDe')}>
          {tab.map((m) => (
            <NavLink key={m.den} to={m.den} end={m.end}
              className={({ isActive }) => `-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-semibold transition-colors duration-fast ${
                isActive ? 'border-primary text-primary' : 'border-transparent text-secondary hover:text-main'}`}>
              <i className={`fa-solid ${m.icon}`} aria-hidden="true" />{m.nhan}
            </NavLink>
          ))}
        </nav>
        {toi.dangTai && !toi.duLieu && <DangTai />}
        {toi.loi && <LoiTai thongBao={loi(toi.loi)} onThuLai={toi.tai} />}
        {toi.duLieu && (
          <Suspense fallback={<DangTai />}>
            <Routes>
              <Route index element={<DanhSachPage hop="can_toi_ky" />} />
              <Route path="toi-gui" element={<DanhSachPage hop="toi_gui" />} />
              <Route path="tat-ca" element={<DanhSachPage hop="tat_ca" />} />
              <Route path="tao-moi" element={<TaoHoSoPage />} />
              <Route path="quy-trinh" element={<QuyTrinhPage />} />
              <Route path="khoa" element={<KhoaPage />} />
              <Route path=":id" element={<ChiTietPage />} />
            </Routes>
          </Suspense>
        )}
      </div>
    </SigningContext.Provider>
  );
}
