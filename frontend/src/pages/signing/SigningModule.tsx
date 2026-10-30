/**
 * Phân hệ Trình ký duyệt nội bộ (Nhóm 5, #80 mục E) dưới đường dẫn /approvals/*.
 * Tab chỉ là bộ lọc hiển thị; quyền đọc/ghi do server kiểm ở từng API.
 */
import { Component, type ErrorInfo, lazy, type ReactNode, Suspense, useEffect, useMemo, useRef } from 'react';
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { DangTai, KhongTimThay, LoiTai } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { coQuyen, SigningContext, useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import './signing.css';

const DanhSachPage = lazy(() => import('./DanhSachPage'));
const TaoHoSoPage = lazy(() => import('./TaoHoSoPage'));
const ChiTietPage = lazy(() => import('./ChiTietPage'));
const QuyTrinhPage = lazy(() => import('./QuyTrinhPage'));
const KhoaPage = lazy(() => import('./KhoaPage'));

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackMessage: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class SigningErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('SigningErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 my-4 rounded-xl border border-danger/20 bg-danger-subtle text-danger space-y-2">
          <div className="flex items-center gap-2 font-bold">
            <i className="fa-solid fa-triangle-exclamation" aria-hidden="true" />
            <span>{this.props.fallbackMessage}</span>
          </div>
          <p className="text-sm opacity-90">{this.state.error?.message || String(this.state.error)}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function SigningModule() {
  const { t, loi } = useSigningT();
  const toi = useTai(() => signingApi.toi());
  const dieuHuong = useNavigate();
  const location = useLocation();
  const { pathname } = location;
  // Màn hẹp: thanh tab cuộn ngang, đưa tab đang xem vào vùng nhìn thấy (vd. vào thẳng "Cấu hình khóa ký")
  const thanhTab = useRef<HTMLElement>(null);
  useEffect(() => {
    thanhTab.current?.querySelector('[aria-current="page"]')?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  }, [pathname, toi.duLieu]);
  const canKy = useTai(() => signingApi.thongKe('can_toi_ky'), [pathname]);
  // Hồ sơ chờ tôi ký gồm cả hồ sơ đã quá hạn (bộ lọc tách hai nhóm)
  const soCanKy = canKy.duLieu ? canKy.duLieu.cho_ky + canKy.duLieu.qua_han : undefined;
  const { tai: lamMoiDem } = canKy;
  const ngu_canh = useMemo(() => ({ toi: toi.duLieu, taiLaiToi: toi.tai, lamMoiDem }),
    [toi.duLieu, toi.tai, lamMoiDem]);

  const tabChinh = [
    { den: '/approvals', nhan: t('nav.canToiKy'), icon: 'fa-pen-nib', end: true, so: soCanKy },
    { den: '/approvals/toi-gui', nhan: t('nav.toiGui'), icon: 'fa-paper-plane' },
    { den: '/approvals/tat-ca', nhan: t('nav.tatCa'), icon: 'fa-folder-open' },
  ];
  const tabPhu = [
    ...(coQuyen(toi.duLieu, 'manage_signing_process') || coQuyen(toi.duLieu, 'view_trinhky')
      ? [{ den: '/approvals/quy-trinh', nhan: t('nav.quyTrinh'), icon: 'fa-diagram-project' }] : []),
    ...(coQuyen(toi.duLieu, 'sign_trinhky') ? [{ den: '/approvals/khoa', nhan: t('nav.khoaCuaToi'), icon: 'fa-key' }] : []),
  ];
  const tieuDeRoute = pathname === '/approvals' || pathname === '/approvals/' ? t('nav.canToiKy')
    : pathname === '/approvals/toi-gui' ? t('nav.toiGui')
      : pathname === '/approvals/tat-ca' ? t('nav.tatCa')
        : pathname === '/approvals/tao-moi' ? t('nav.taoMoi')
          : pathname === '/approvals/quy-trinh' ? t('nav.quyTrinh')
            : pathname === '/approvals/khoa' ? t('nav.khoaCuaToi')
              : pathname === '/approvals/tai-lieu' ? t('nav.taiLieu')
                : /^\/approvals\/\d+$/.test(pathname) ? t('chiTiet.tienTrinh') : t('chung.trangKhongTonTai');

  return (
    <SigningContext.Provider value={ngu_canh}>
      {/* pb-24: chừa chỗ cho nút trợ lý AI nổi ở góc dưới để không che nút hành động cuối trang */}
      <div className="signing-scope space-y-3.5 pb-24">
        <h1 className="sr-only">{t('tieuDe')}</h1>
        <h2 className="sr-only">{tieuDeRoute}</h2>

        <div className="flex items-end justify-between gap-3 border-b border-border-subtle">
          <nav
            ref={thanhTab}
            className="signing-nav-scroll -mb-px flex items-end gap-x-1 overflow-x-auto flex-nowrap whitespace-nowrap touch-pan-x scroll-smooth overscroll-x-contain min-w-0 flex-1 -mx-4 px-4 sm:mx-0 sm:px-0"
            aria-label={t('tieuDe')}
          >
            <div className="flex flex-nowrap items-end gap-1 shrink-0">
              {tabChinh.map((m) => {
                const isChiTiet = /^\/approvals\/\d+$/.test(pathname);
                const hopHienTai = ((location.state as { hop?: string } | null)?.hop) || 'can_toi_ky';
                const tabActive = isChiTiet
                  ? (m.den === '/approvals' && hopHienTai === 'can_toi_ky') ||
                    (m.den === '/approvals/toi-gui' && hopHienTai === 'toi_gui') ||
                    (m.den === '/approvals/tat-ca' && hopHienTai === 'tat_ca')
                  : undefined;

                return (
                  <NavLink
                    key={m.den}
                    to={m.den}
                    end={m.end}
                    className={({ isActive }) => {
                      const active = tabActive !== undefined ? tabActive : isActive;
                      return `-mb-px flex items-center gap-2 border-b-2 px-3 sm:px-4 py-2 text-sm font-semibold transition-colors duration-fast whitespace-nowrap shrink-0 ${
                        active
                          ? 'border-primary text-primary'
                          : 'border-transparent text-secondary hover:text-main hover:border-border'
                      }`;
                    }}
                  >
                    <i className={`fa-solid ${m.icon}`} aria-hidden="true" />
                    <span>{m.nhan}</span>
                    {!!m.so && (
                      <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-xs font-bold text-primary">
                        {m.so}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
            <div className="mx-1.5 mb-2.5 h-4 w-px bg-border-subtle shrink-0" aria-hidden="true" />
            <div className="flex flex-nowrap items-end gap-1 shrink-0">
              {tabPhu.map((m) => (
                <NavLink
                  key={m.den}
                  to={m.den}
                  className={({ isActive }) =>
                    `-mb-px flex items-center gap-2 border-b-2 px-3 sm:px-4 py-2 text-sm font-semibold transition-colors duration-fast whitespace-nowrap shrink-0 ${
                      isActive
                        ? 'border-primary text-primary'
                        : 'border-transparent text-secondary hover:text-main hover:border-border'
                    }`
                  }
                >
                  <i className={`fa-solid ${m.icon}`} aria-hidden="true" />
                  <span>{m.nhan}</span>
                </NavLink>
              ))}
            </div>
          </nav>
          {coQuyen(toi.duLieu, 'add_trinhky') && (
            <Button
              size="sm"
              icon="fa-plus"
              className="shrink-0 shadow-xs mb-1.5"
              onClick={() => dieuHuong('/approvals/tao-moi')}
            >
              {t('nav.taoMoi')}
            </Button>
          )}
        </div>
        {toi.dangTai && !toi.duLieu && <DangTai />}
        {toi.loi && <LoiTai thongBao={loi(toi.loi)} onThuLai={toi.tai} />}
        {toi.duLieu && (
          <SigningErrorBoundary fallbackMessage={t('chung.loiTai')}>
            <Suspense fallback={<DangTai />}>
              <Routes>
                <Route index element={<DanhSachPage key="can_toi_ky" hop="can_toi_ky" />} />
                <Route path="toi-gui" element={<DanhSachPage key="toi_gui" hop="toi_gui" />} />
                <Route path="tat-ca" element={<DanhSachPage key="tat_ca" hop="tat_ca" />} />
                <Route path="tao-moi" element={<TaoHoSoPage />} />
                <Route path="quy-trinh" element={<QuyTrinhPage />} />
                <Route path="khoa" element={<KhoaPage />} />
                {/* Tab Thông báo đã bỏ: giữ đường dẫn cũ để liên kết lưu sẵn không rơi vào 404 */}
                <Route path="thong-bao" element={<Navigate to="/approvals" replace />} />
                <Route path="tai-lieu" element={<Navigate to="/approvals/tat-ca?che_do=tep" replace />} />
                <Route path=":id" element={<ChiTietPage />} />
                <Route path="*" element={<KhongTimThay thongBao={t('chung.trangKhongTonTai')} />} />
              </Routes>
            </Suspense>
          </SigningErrorBoundary>
        )}
      </div>
    </SigningContext.Provider>
  );
}
