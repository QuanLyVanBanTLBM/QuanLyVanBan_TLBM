import React, { useState, useEffect } from 'react';
import { MAIN_MODULES } from '@lib/constants';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import { Logo } from '@components/common/Logo';

interface AppSidebarProps {
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  activePage: ActivePageId;
  committedPage: ActivePageId;
  previewPage: ActivePageId | null;
  onNavigate: (pageId: ActivePageId) => void;
  onHoverPreview?: (pageId: ActivePageId) => void;
  onHoverLeave?: () => void;
  sidebarStyle?: 'facebook' | 'dock';
  onToggleSidebarStyle?: (style: 'facebook' | 'dock') => void;
  isCollapsed?: boolean;
  onExpandSidebar?: () => void;
  isPinned?: boolean;
  onTogglePin?: () => void;
}

export default function AppSidebar({
  onCloseMobile,
  committedPage,
  previewPage,
  onNavigate,
  onHoverPreview = () => {},
  onHoverLeave = () => {},
  isCollapsed = false,
  onExpandSidebar,
  isPinned = false,
  onTogglePin,
}: AppSidebarProps) {
  const { t } = useTranslation();

  // Trạng thái mở accordion của các module
  const [expandedModIds, setExpandedModIds] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    MAIN_MODULES.forEach((mod) => {
      if (mod.subItems.some((s) => s.id === committedPage)) {
        initial[mod.id] = true;
      }
    });
    return initial;
  });

  // Tự động mở accordion của module khi committedPage thay đổi
  useEffect(() => {
    MAIN_MODULES.forEach((mod) => {
      if (mod.subItems.some((s) => s.id === committedPage)) {
        setExpandedModIds((prev) => ({ ...prev, [mod.id]: true }));
      }
    });
  }, [committedPage]);

  const toggleExpand = (modId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setExpandedModIds((prev) => ({
      ...prev,
      [modId]: !prev[modId],
    }));
  };

  const getModuleLabel = (modId: string, fallback: string) => {
    return t(`navigation.${modId}`) !== `navigation.${modId}` ? t(`navigation.${modId}`) : fallback;
  };

  const getSubItemLabel = (subId: string, fallback: string) => {
    const navKey = `navigation.${subId}`;
    const pageTitleKey = `pages.${subId}.title`;
    if (t(navKey) !== navKey) return t(navKey);
    if (t(pageTitleKey) !== pageTitleKey) return t(pageTitleKey);
    return fallback;
  };

  // Xác định mục đang active
  const activeModule = MAIN_MODULES.find((mod) => {
    const isDirect = mod.id === 'dashboard' || mod.subItems.length <= 1;
    return isDirect
      ? committedPage === mod.defaultPage || committedPage === mod.id || previewPage === mod.defaultPage || previewPage === mod.id
      : mod.subItems.some((s) => s.id === committedPage || s.id === previewPage);
  });
  const activeId = committedPage === 'settings' ? 'settings' : (activeModule?.id || 'dashboard');

  // =========================================================================
  // TRẠNG THÁI THU GỌN (COLLAPSED RAIL): 72px PHÂN BỔ ĐỀU, TỐI GIẢN CHUẨN XÁC
  // RÊ CHUỘT VÀO SẼ TỰ ĐỘNG XỔ MENU RA (XỬ LÝ QUA ONMOUSEENTER Ở WRAPPER)
  // =========================================================================
  if (isCollapsed) {
    return (
      <aside
        className="w-full h-full flex flex-col items-center justify-between bg-sidebar border-r border-subtle rounded-none select-none py-3 px-1.5 transition-all duration-300 overflow-hidden"
        aria-label="Thanh điều hướng thu gọn"
      >
        {/* 1. Header: Nút mở rộng menu điều hướng (tránh trùng Logo với Header) */}
        <div className="w-10 h-10 flex items-center justify-center shrink-0">
          <button
            type="button"
            className="w-10 h-10 rounded-xl flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors cursor-pointer"
            onClick={() => {
              onExpandSidebar?.();
            }}
            title="Mở rộng menu điều hướng"
            aria-label="Mở rộng menu điều hướng"
          >
            <i className="fa-solid fa-bars text-base" />
          </button>
        </div>

        {/* 2. Danh sách các icon - LUÔN PHÂN BỔ ĐỀU & NỀN XANH TỐI GIẢN, CHUẨN TÂM 100% */}
        <div className="flex-1 w-full flex flex-col justify-evenly items-center my-2">
          {MAIN_MODULES.map((mod) => {
            const isDirectPage = mod.id === 'dashboard' || mod.subItems.length <= 1;
            const isActive = activeId === mod.id;
            const modLabel = getModuleLabel(mod.id, mod.label);
            const totalBadges = mod.subItems
              .map((s) => (typeof s.badge === 'number' ? s.badge : 0))
              .reduce((a, b) => a + b, 0);

            return (
              <div
                key={mod.id}
                className="relative flex items-center justify-center w-full"
              >
                <button
                  type="button"
                  className={`w-11 h-11 rounded-2xl flex items-center justify-center cursor-pointer transition-all duration-200 relative ${
                    isActive
                      ? 'bg-primary text-white shadow-md shadow-primary/25 scale-105'
                      : 'text-text-main hover:bg-surface-hover hover:text-primary'
                  }`}
                  onClick={() => {
                    if (isDirectPage) {
                      onNavigate(mod.defaultPage);
                    } else {
                      setExpandedModIds((prev) => ({ ...prev, [mod.id]: true }));
                    }
                    onExpandSidebar?.();
                  }}
                  onMouseEnter={() => {
                    setExpandedModIds((prev) => ({ ...prev, [mod.id]: true }));
                    onHoverPreview(mod.defaultPage);
                  }}
                  title={modLabel}
                  aria-label={modLabel}
                >
                  <i
                    className={`fa-solid ${mod.icon} text-base transition-transform ${
                      isActive ? 'text-white' : ''
                    }`}
                  />
                  {totalBadges > 0 && (
                    <span
                      className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center shadow-xs ${
                        isActive
                          ? 'bg-white text-primary'
                          : 'bg-primary text-white'
                      }`}
                    >
                      {totalBadges}
                    </span>
                  )}
                </button>
              </div>
            );
          })}

          {/* Thông tin phiên bản ở cuối dải Icon Rail */}
          <div
            className="relative flex flex-col items-center justify-center w-full pt-2.5 border-t border-subtle/60 cursor-default"
            title="Phiên bản hệ thống: TLBM v2.0 (2026)"
          >
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-surface border border-subtle text-text-muted select-none">
              v2.0
            </span>
          </div>
        </div>
      </aside>
    );
  }

  // =========================================================================
  // TRẠNG THÁI MỞ RỘNG (EXPANDED SIDEBAR): BỐ CỤC ỔN ĐỊNH, CHUẨN UX CHUYÊN NGHIỆP
  // =========================================================================
  return (
    <aside
      className="w-[248px] h-full flex flex-col bg-sidebar border-r border-subtle rounded-none select-none overflow-hidden"
      aria-label="Thanh điều hướng mở rộng"
      onMouseLeave={onHoverLeave}
    >
      {/* Header Sidebar: Logo Bảo Long & Nút điều khiển (Ghim / Thu gọn) */}
      <div className="sidebar-header h-16 px-3.5 border-b border-subtle flex items-center justify-between shrink-0 bg-sidebar rounded-none">
        <div
          className="flex items-center gap-2 px-1 cursor-pointer transition-transform hover:scale-[1.03]"
          onClick={() => {
            onNavigate('dashboard');
            onCloseMobile();
          }}
          title="Bảo Long Insurance - Về Trang Chủ"
        >
          <Logo size="md" className="h-7 sm:h-8" />
        </div>
        <div className="flex items-center gap-1.5">
          {/* Nút Ghim cố định Sidebar (chỉ hiển thị trên Desktop >= 1024px) */}
          {onTogglePin && (
            <button
              type="button"
              className={`hidden lg:flex w-7 h-7 rounded-lg border border-subtle items-center justify-center text-xs cursor-pointer transition-all duration-200 ${
                isPinned
                  ? 'bg-primary-subtle text-primary border-primary/30 rotate-45 shadow-2xs'
                  : 'bg-surface text-text-muted hover:text-text-main hover:bg-surface-hover'
              }`}
              onClick={onTogglePin}
              aria-label={isPinned ? 'Bỏ ghim thanh điều hướng' : 'Ghim thanh điều hướng cố định'}
              title={isPinned ? 'Bỏ ghim thanh điều hướng (bấm để thu gọn tự do)' : 'Ghim thanh điều hướng (giữ mở để làm việc liên tục)'}
            >
              <i className="fa-solid fa-thumbtack text-[11px]" />
            </button>
          )}
          {/* Nút Thu gọn Sidebar về Icon Rail */}
          <button
            type="button"
            className="w-7 h-7 rounded-lg bg-surface border border-subtle text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center text-xs cursor-pointer transition-colors"
            onClick={onCloseMobile}
            aria-label="Thu gọn menu về dải biểu tượng"
            title="Thu gọn menu về dải biểu tượng (Icon Rail)"
          >
            <i className="fa-solid fa-chevron-left text-[11px]" />
          </button>
        </div>
      </div>

      {/* Danh sách 6 phân hệ chính (Tầng 1) - Bố cục ổn định, thoải mái, không bị nhảy vị trí */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
        {MAIN_MODULES.map((mod) => {
          const isDirectPage = mod.id === 'dashboard' || mod.subItems.length <= 1;
          const isModActive = isDirectPage
            ? committedPage === mod.defaultPage || committedPage === mod.id || previewPage === mod.defaultPage || previewPage === mod.id
            : mod.subItems.some((s) => s.id === committedPage || s.id === previewPage);
          const isExpanded = !isDirectPage && !!expandedModIds[mod.id];
          const modLabel = getModuleLabel(mod.id, mod.label);

          const totalBadges = mod.subItems
            .map((s) => (typeof s.badge === 'number' ? s.badge : 0))
            .reduce((a, b) => a + b, 0);

          // TRƯỜNG HỢP 1: MỤC ĐƠN (Ví dụ: Dashboard)
          if (isDirectPage) {
            return (
              <div key={mod.id} className="relative flex items-center">
                <button
                  type="button"
                  className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-left cursor-pointer transition-all duration-200 ${
                    isModActive
                      ? 'bg-primary text-white font-bold shadow-md shadow-primary/25'
                      : 'text-text-main hover:bg-surface-hover group'
                  }`}
                  onClick={() => {
                    onNavigate(mod.defaultPage);
                    onCloseMobile();
                  }}
                  onMouseEnter={() => onHoverPreview(mod.defaultPage)}
                  title={modLabel}
                >
                  <i
                    className={`fa-solid ${mod.icon} text-base w-5 text-center transition-colors ${
                      isModActive
                        ? 'text-white'
                        : 'text-text-main group-hover:text-primary'
                    }`}
                  />
                  <span
                    className={`text-sm font-semibold truncate flex-1 transition-colors ${
                      isModActive
                        ? 'text-white'
                        : 'text-text-main group-hover:text-primary'
                    }`}
                  >
                    {modLabel}
                  </span>
                  {totalBadges > 0 && (
                    <span
                      className={`min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold flex items-center justify-center shrink-0 ${
                        isModActive
                          ? 'bg-white/20 text-white'
                          : 'bg-primary text-white'
                      }`}
                    >
                      {totalBadges}
                    </span>
                  )}
                </button>
              </div>
            );
          }

          // TRƯỜNG HỢP 2: PHÂN HỆ ĐANG MỞ RỘNG (DẠNG THẺ NỔI TRẮNG)
          if (isExpanded) {
            return (
              <div
                key={mod.id}
                className="bg-surface rounded-2xl border border-primary/25 shadow-sm p-2 space-y-1 transition-all duration-200"
              >
                {/* Header của thẻ phân hệ */}
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-2.5 py-2 rounded-xl text-left cursor-pointer hover:bg-primary-subtle/40 transition-colors"
                  onClick={() => toggleExpand(mod.id)}
                  title={`${modLabel} (Bấm để thu gọn)`}
                >
                  <i className={`fa-solid ${mod.icon} text-base w-5 text-center text-primary`} />
                  <span className="text-sm font-bold text-primary truncate flex-1">
                    {modLabel}
                  </span>
                  <i className="fa-solid fa-chevron-up text-xs text-primary" />
                </button>

                {/* Danh sách các mục con bên trong thẻ nổi */}
                <div className="space-y-0.5 pt-0.5">
                  {mod.subItems.map((sub) => {
                    const isSubActive = committedPage === sub.id || previewPage === sub.id;
                    const subLabel = getSubItemLabel(sub.id, sub.label);

                    return (
                      <div
                        key={sub.id}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 ${
                          isSubActive
                            ? 'bg-primary-subtle text-primary font-bold shadow-2xs'
                            : 'text-text-main hover:bg-primary-subtle/30 hover:text-primary font-medium group hover:translate-x-0.5'
                        }`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate(sub.id);
                          onCloseMobile();
                        }}
                        onMouseEnter={() => onHoverPreview(sub.id)}
                        role="button"
                        tabIndex={0}
                        title={subLabel}
                      >
                        <i
                          className={`fa-solid ${sub.icon} text-xs w-4 text-center transition-colors ${
                            isSubActive
                              ? 'text-primary'
                              : 'text-text-secondary group-hover:text-primary'
                          }`}
                        />
                        <span className="text-xs truncate flex-1">{subLabel}</span>
                        {sub.badge !== undefined && (
                          <span
                            className={`min-w-[18px] h-4 px-1 rounded-full text-[10px] font-bold flex items-center justify-center shrink-0 ${
                              isSubActive
                                ? 'bg-primary text-white'
                                : 'bg-primary-subtle text-primary'
                            }`}
                          >
                            {sub.badge}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }

          // TRƯỜNG HỢP 3: PHÂN HỆ ĐANG THU GỌN (COLLAPSED)
          return (
            <div key={mod.id} className="relative flex items-center">
              <button
                type="button"
                className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-left cursor-pointer transition-all duration-200 ${
                  isModActive
                    ? 'bg-primary text-white font-bold shadow-md shadow-primary/25'
                    : 'text-text-main hover:bg-surface-hover group'
                }`}
                onClick={() => toggleExpand(mod.id)}
                onMouseEnter={() => onHoverPreview(mod.defaultPage)}
                title={`${modLabel} (Bấm để mở rộng)`}
              >
                <i
                  className={`fa-solid ${mod.icon} text-base w-5 text-center transition-colors ${
                    isModActive
                      ? 'text-white'
                      : 'text-text-main group-hover:text-primary'
                  }`}
                />
                <span
                  className={`text-sm font-semibold truncate flex-1 transition-colors ${
                    isModActive
                      ? 'text-white'
                      : 'text-text-main group-hover:text-primary'
                  }`}
                >
                  {modLabel}
                </span>
                {totalBadges > 0 && (
                  <span
                    className={`min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold flex items-center justify-center shrink-0 mr-1 ${
                      isModActive
                        ? 'bg-white/20 text-white'
                        : 'bg-primary text-white'
                    }`}
                  >
                    {totalBadges}
                  </span>
                )}
                <i
                  className={`fa-solid fa-chevron-down text-xs transition-colors ${
                    isModActive
                      ? 'text-white/80'
                      : 'text-text-muted group-hover:text-text-main'
                  }`}
                />
              </button>
            </div>
          );
        })}
      </div>

      {/* VÙNG THÔNG TIN PHIÊN BẢN CỐ ĐỊNH Ở ĐÁY (PINNED BOTTOM VERSION INFO) */}
      <div className="sidebar-footer shrink-0 border-t border-subtle px-4 py-3 bg-sidebar/95 backdrop-blur-xs flex items-center justify-between rounded-none">
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" title="Hệ thống trực tuyến" />
            <span className="text-xs font-semibold text-text-main truncate">Bảo Long TLBM</span>
          </div>
          <span className="text-[11px] text-text-muted mt-0.5">Phiên bản v2.0</span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-surface border border-subtle text-text-muted font-semibold shrink-0">
          2026
        </span>
      </div>
    </aside>
  );
}



