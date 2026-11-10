import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AppHeader from './AppHeader';

describe('AppHeader Logo Visibility & Sidebar Coordination', () => {
  const defaultProps = {
    currentTheme: 'light' as const,
    onSelectTheme: () => {},
    onToggleSidebar: () => {},
  };

  it('renders Logo and hamburger button when sidebar is collapsed (isSidebarOpen=false)', () => {
    render(
      <MemoryRouter>
        <AppHeader {...defaultProps} isSidebarOpen={false} />
      </MemoryRouter>
    );

    // Phải có nút hamburger
    const menuBtn = screen.getByRole('button', { name: /mở menu điều hướng/i });
    expect(menuBtn).toBeInTheDocument();

    // Phải có Logo
    const headerLogoImages = screen.getAllByAltText('Bảo Long Insurance');
    expect(headerLogoImages.length).toBeGreaterThan(0);
  });

  it('hides Logo and hamburger button when sidebar is expanded (isSidebarOpen=true) to prevent duplicate logos', () => {
    render(
      <MemoryRouter>
        <AppHeader {...defaultProps} isSidebarOpen={true} />
      </MemoryRouter>
    );

    // Không có nút hamburger
    const menuBtn = screen.queryByRole('button', { name: /mở menu điều hướng/i });
    expect(menuBtn).not.toBeInTheDocument();

    // Không có Logo ở Header
    const headerLogoImages = screen.queryAllByAltText('Bảo Long Insurance');
    expect(headerLogoImages.length).toBe(0);
  });

  it('renders dynamic Home button and search slot when scrolled on dashboard', () => {
    const handleScrollToTop = vi.fn();
    const { container } = render(
      <MemoryRouter>
        <AppHeader
          {...defaultProps}
          activePage="dashboard"
          isScrolled={true}
          onScrollToTop={handleScrollToTop}
        />
      </MemoryRouter>
    );

    // Có nút Home trên Header
    const homeBtn = screen.getByRole('button', { name: /Trang Chủ|Home/i });
    expect(homeBtn).toBeInTheDocument();

    // Click nút Home kích hoạt cuộn lên đầu trang
    homeBtn.click();
    expect(handleScrollToTop).toHaveBeenCalledTimes(1);

    // Có slot header-search-slot
    const searchSlot = container.querySelector('#header-search-slot');
    expect(searchSlot).toBeInTheDocument();
  });

  it('renders dynamic breadcrumbs and sub-items on other pages when scrolled', () => {
    const handleNavigate = vi.fn();
    render(
      <MemoryRouter>
        <AppHeader
          {...defaultProps}
          activePage="documents_incoming"
          isScrolled={true}
          onNavigate={handleNavigate}
        />
      </MemoryRouter>
    );

    // Có breadcrumb và tên phân hệ văn bản đến
    expect(screen.getAllByText(/Văn Bản Đến|Incoming/i).length).toBeGreaterThan(0);
    // Có nút về Trang Chủ
    const homeBtn = screen.getByRole('button', { name: /Trang Chủ|Home/i });
    expect(homeBtn).toBeInTheDocument();
  });
});

