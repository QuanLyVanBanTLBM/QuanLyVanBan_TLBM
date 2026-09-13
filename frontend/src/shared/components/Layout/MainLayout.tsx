import React, { useState, useEffect } from 'react';
import AppSidebar from './AppSidebar';
import AppHeader from '../Header/AppHeader';
import ThemeSelector from '../Header/ThemeSelector';
import TopSubNav from '../Navigation/TopSubNav';
import MobileAssistiveTouch from '../Navigation/MobileAssistiveTouch';
import FloatingAIBox from '../AI/FloatingAIBox';
import AppFooter from './AppFooter';
import { ActivePageId } from '../../types/navigation';
import { ThemeMode } from '../../types/theme';

interface MainLayoutProps {
  children: React.ReactNode;
  activePage: ActivePageId;
  committedPage: ActivePageId;
  previewPage: ActivePageId | null;
  currentTheme: ThemeMode;
  onSelectTheme: (theme: ThemeMode) => void;
  onToggleTheme?: () => void;
  preferredLightTheme?: ThemeMode;
  preferredDarkTheme?: ThemeMode;
  onNavigate: (pageId: ActivePageId) => void;
  onHoverPreview: (pageId: ActivePageId) => void;
  onHoverLeave: () => void;
}

export default function MainLayout({
  children,
  activePage,
  committedPage,
  previewPage,
  currentTheme,
  onSelectTheme,
  onToggleTheme,
  preferredLightTheme,
  preferredDarkTheme,
  onNavigate,
  onHoverPreview,
  onHoverLeave,
}: MainLayoutProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Tự động đóng mobile drawer nếu chuyển sang màn hình desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 992) {
        setIsMobileOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const [isSidebarHovered, setIsSidebarHovered] = useState(false);

  // Theo dõi vị trí con trỏ chuột toàn màn hình cho TẤT CẢ CÁC TRANG:
  // - Khi tiến sát mép trái (<= 24px): Tự động trượt xổ sidebar ra
  // - Khi rời khỏi bề ngang thanh sidebar (> 86px): TỰ ĐỘNG THỤT VỀ NGAY LẬP TỨC
  useEffect(() => {
    const handlePointerTrack = (e: MouseEvent) => {
      if (e.clientX <= 24) {
        setIsSidebarHovered(true);
      } else if (e.clientX > 86) {
        setIsSidebarHovered(false);
        onHoverLeave();
      }
    };

    const handleWindowLeave = () => {
      setIsSidebarHovered(false);
      onHoverLeave();
    };

    window.addEventListener('mousemove', handlePointerTrack);
    window.addEventListener('mouseleave', handleWindowLeave);
    window.addEventListener('blur', handleWindowLeave);

    return () => {
      window.removeEventListener('mousemove', handlePointerTrack);
      window.removeEventListener('mouseleave', handleWindowLeave);
      window.removeEventListener('blur', handleWindowLeave);
    };
  }, [onHoverLeave]);

  // Bộ phần tử Sidebar trượt ẩn/hiện dùng chung cho toàn bộ các trang
  const renderSidebarElements = () => (
    <>
      {/* VÙNG CẢM ỨNG MÉP TRÁI: Rê chuột vào mép trái màn hình thì thanh Sidebar trượt xổ ra */}
      <div
        className="sidebar-edge-hotspot"
        onClick={() => setIsSidebarHovered((prev) => !prev)}
        onMouseEnter={() => setIsSidebarHovered(true)}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          width: '20px',
          zIndex: 299,
          cursor: 'pointer',
        }}
        title="Rê chuột hoặc bấm vào mép trái để mở menu"
      />

      {/* Chỉ báo nhỏ ở mép trái giúp người dùng dễ dàng nhận biết vị trí thanh sidebar ẩn */}
      <div
        className="sidebar-edge-indicator"
        onClick={() => setIsSidebarHovered((prev) => !prev)}
        style={{
          position: 'fixed',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: isSidebarHovered ? '8px' : '4px',
          height: '64px',
          borderRadius: '0 6px 6px 0',
          background: 'var(--color-primary)',
          boxShadow: '0 0 10px var(--color-primary-glow)',
          opacity: isSidebarHovered ? 0.9 : 0.45,
          zIndex: 298,
          transition: 'all 0.2s ease',
          pointerEvents: 'auto',
          cursor: 'pointer',
        }}
        title="Bấm để mở menu điều hướng"
      />

      {/* Lớp phủ mờ backdrop khi menu được mở trên mobile/tablet */}
      {isMobileOpen && (
        <div
          className="mobile-sidebar-backdrop"
          onClick={() => {
            setIsMobileOpen(false);
            setIsSidebarHovered(false);
          }}
          aria-label="Đóng menu điều hướng"
        />
      )}

      {/* THANH BÊN TRÁI: Trượt xổ ra mượt mà, z-index 1001 nổi trên backdrop */}
      <div
        className={`sidebar-slide-wrapper ${isMobileOpen ? 'mobile-drawer-open' : ''}`}
        onMouseEnter={() => setIsSidebarHovered(true)}
        onMouseLeave={() => {
          setIsSidebarHovered(false);
          onHoverLeave();
        }}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 1001,
          transform: isSidebarHovered || isMobileOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.28s ease',
          boxShadow: isSidebarHovered || isMobileOpen ? '12px 0 40px rgba(0, 0, 0, 0.55)' : 'none',
          background: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border-subtle)',
          height: '100vh',
          display: 'flex',
          pointerEvents: isSidebarHovered || isMobileOpen ? 'auto' : 'none',
        }}
      >
        <AppSidebar
          isMobileOpen={isMobileOpen}
          onCloseMobile={() => {
            setIsMobileOpen(false);
            setIsSidebarHovered(false);
          }}
          activePage={activePage}
          committedPage={committedPage}
          previewPage={previewPage}
          onNavigate={(pageId) => {
            onNavigate(pageId);
            setIsSidebarHovered(false);
            setIsMobileOpen(false);
          }}
          onHoverPreview={onHoverPreview}
          onHoverLeave={onHoverLeave}
        />
      </div>
    </>
  );

  // 1. Khi vào trang Trợ Lý AI: Tối giản, toàn màn hình, chỉ có nút Theme & Chat
  if (activePage === 'ai_assistant') {
    return (
      <div
        className="ai-immersive-shell"
        style={{
          width: '100vw',
          height: '100vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-app)',
          position: 'relative',
        }}
      >
        {renderSidebarElements()}

        {/* Cụm điều khiển nổi góc trên bên phải: Nút Về Trang Chủ & Nút Sáng/Tối */}
        <div
          className="ai-top-floating-controls"
          style={{
            position: 'fixed',
            top: '12px',
            right: '18px',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          {/* Nút Về Trang Chủ (Home) rõ ràng, tiện lợi */}
          <button
            type="button"
            onClick={() => onNavigate('dashboard')}
            className="ai-home-floating-btn"
            title="Quay về Trang chủ (Dashboard)"
            aria-label="Về trang chủ"
          >
            <i className="fa-solid fa-house ai-home-icon" />
            <span>Trang chủ</span>
          </button>

          {/* Nút chuyển chế độ Sáng / Tối */}
          <ThemeSelector
            currentTheme={currentTheme}
            onSelectTheme={onSelectTheme}
            onToggleTheme={onToggleTheme}
            preferredLightTheme={preferredLightTheme}
            preferredDarkTheme={preferredDarkTheme}
          />
        </div>

        {/* Toàn bộ không gian màn hình dành trọn vẹn 100% tràn viền cho trang Chat AI */}
        <main style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: 0, width: '100%', height: '100%' }}>
          {children}
        </main>

        {/* 3. Phím Home ảo AssistiveTouch dành cho thiết bị di động & điều hướng nhanh */}
        <MobileAssistiveTouch
          activePage={activePage}
          onNavigate={onNavigate}
          currentTheme={currentTheme}
          onSelectTheme={onSelectTheme}
          onToggleTheme={onToggleTheme}
        />
      </div>
    );
  }

  // 2. TẤT CẢ CÁC TRANG CÒN LẠI: Thanh Sidebar bên trái cũng tự động ẩn và trượt xổ ra khi rê chuột
  return (
    <div className="app-shell" style={{ width: '100vw', height: '100vh', overflow: 'hidden', position: 'relative' }}>

      {/* Thanh điều hướng Navbar bên trái: Tự động ẩn kéo sang trái (-100%), rê chuột trượt xổ ra */}
      {renderSidebarElements()}

      {/* 2. Khung nội dung chính & Thanh Header đỉnh (Chiếm trọn vẹn 100% không gian màn hình) */}
      <div className="main-container" style={{ width: '100%', flex: 1, minWidth: 0 }}>
        <AppHeader
          currentTheme={currentTheme}
          onSelectTheme={onSelectTheme}
          onToggleTheme={onToggleTheme}
          preferredLightTheme={preferredLightTheme}
          preferredDarkTheme={preferredDarkTheme}
          onToggleMobileSidebar={() => {
            setIsMobileOpen((prev) => !prev);
            setIsSidebarHovered((prev) => !prev);
          }}
          onNavigate={onNavigate}
        />

        {/* Thanh điều hướng phân hệ phụ nằm ngang */}
        <TopSubNav
          activePage={activePage}
          isHoveredPreview={previewPage !== null}
          onNavigate={onNavigate}
        />

        {/* Viewport nội dung trang động: ổn định, êm ái, chuyên nghiệp */}
        <main className="page-viewport">
          <div className="page-content-wrapper">{children}</div>
          <AppFooter />
        </main>
      </div>

      {/* 3. Phím Home ảo AssistiveTouch dành riêng cho thiết bị di động */}
      <MobileAssistiveTouch
        activePage={activePage}
        onNavigate={onNavigate}
        currentTheme={currentTheme}
        onSelectTheme={onSelectTheme}
        onToggleTheme={onToggleTheme}
      />

      {/* 4. Box AI Trợ Lý nổi tự do có thể kéo thả bất kỳ vị trí nào trên giao diện */}
      <FloatingAIBox onNavigate={onNavigate} />
    </div>
  );
}
