import React from 'react';
import { MAIN_MODULES } from '../../utils/constants';
import { ActivePageId } from '../../types/navigation';

interface AppSidebarProps {
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  activePage: ActivePageId;
  committedPage: ActivePageId;
  previewPage: ActivePageId | null;
  onNavigate: (pageId: ActivePageId) => void;
  onHoverPreview: (pageId: ActivePageId) => void;
  onHoverLeave: () => void;
}

export default function AppSidebar({
  isMobileOpen,
  onCloseMobile,
  committedPage,
  previewPage,
  onNavigate,
  onHoverPreview,
  onHoverLeave,
}: AppSidebarProps) {
  return (
    <aside
      className={`app-sidebar ${isMobileOpen ? 'mobile-open' : ''}`}
      onMouseLeave={onHoverLeave}
    >
      {/* 1. Header của Sidebar Drawer (Logo + Nút đóng X) */}
      <div className="sidebar-drawer-header">
        <div className="brand-logo">
          <div className="brand-icon-box">
            <i className="fa-solid fa-file-shield" />
          </div>
          <div className="brand-text">
            <span className="brand-title">TLBM SYSTEM</span>
            <span className="brand-subtitle">Quản Lý Văn Bản &amp; TL</span>
          </div>
        </div>

        <button
          type="button"
          className="sidebar-close-mobile-btn"
          onClick={onCloseMobile}
          title="Đóng menu điều hướng"
          aria-label="Đóng menu"
        >
          <i className="fa-solid fa-xmark" />
        </button>
      </div>

      {/* 2. Dãy 6 Icon Phân Hệ Chuẩn Dock Nổi */}
      <div className="sidebar-nav-container-distributed">
        <div className="sidebar-nav-scroll-viewport">
          {MAIN_MODULES.map((mod) => {
            const isCommittedActive = mod.subItems.some((item) => item.id === committedPage);
            const isPreviewHovered =
              previewPage !== null && mod.subItems.some((item) => item.id === previewPage);

            let btnClasses = 'nav-item-btn';
            if (isCommittedActive) {
              btnClasses += ' committed-active active';
            }
            if (isPreviewHovered && !isCommittedActive) {
              btnClasses += ' hover-preview-lighter';
            }

            // Tính tổng số lượng badge thông báo
            const numericBadges = mod.subItems
              .map((s) => (typeof s.badge === 'number' ? s.badge : 0))
              .reduce((a, b) => a + b, 0);

            return (
              <div key={mod.id} className="nav-item-wrapper">
                <button
                  type="button"
                  className={btnClasses}
                  onMouseEnter={() => onHoverPreview(mod.defaultPage)}
                  onClick={() => {
                    onNavigate(mod.defaultPage);
                    onCloseMobile();
                  }}
                  title={`${mod.label} (Rê chuột để xem trước, Bấm để ở lại trang)`}
                >
                  <span className="nav-item-icon">
                    <i className={`fa-solid ${mod.icon}`} />
                    {numericBadges > 0 && (
                      <span className="nav-item-mini-badge">{numericBadges}</span>
                    )}
                  </span>
                  <span className="nav-item-mobile-label">
                    <span className="mobile-label-title">{mod.label}</span>
                    <span className="mobile-label-team">{mod.teamTag}</span>
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Phía dưới cùng: Trạng thái trực tuyến mini */}
      <div className="sidebar-collapsed-bottom">
        <div
          className="sidebar-bottom-status-dot"
          title="Hệ thống trực tuyến v2.0 (Nhóm 1)"
        >
          <span className="live-status-ping" />
        </div>
      </div>
    </aside>
  );
}
