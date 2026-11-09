import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ScreenLockModal from './ScreenLockModal';

// Mock Logo component
vi.mock('@components/common/Logo', () => ({
  default: () => <div data-testid="mock-logo">Logo</div>,
}));

// Mock authService
vi.mock('@lib/authService', () => ({
  default: {
    logout: vi.fn(),
  },
}));

describe('ScreenLockModal Component', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('renders nothing when isLocked is false', () => {
    const { container } = render(<ScreenLockModal isLocked={false} onUnlock={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders lock screen modal when isLocked is true', () => {
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({
        fullName: 'Nguyễn Văn A',
        username: 'nguyenvana',
        roleTitle: 'Chuyên viên',
      })
    );

    render(<ScreenLockModal isLocked={true} onUnlock={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Nguyễn Văn A')).toBeInTheDocument();
    expect(screen.getByText('Chuyên viên')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Nhập mật khẩu để mở khóa...')).toBeInTheDocument();
  });

  it('calls onUnlock when unlock form is submitted', () => {
    const handleUnlock = vi.fn();
    render(<ScreenLockModal isLocked={true} onUnlock={handleUnlock} />);

    const unlockButton = screen.getByRole('button', { name: /mở khóa làm việc/i });
    fireEvent.click(unlockButton);

    expect(handleUnlock).toHaveBeenCalledTimes(1);
  });

  it('logs out and redirects to /login when logout button is clicked', async () => {
    const handleUnlock = vi.fn();
    render(<ScreenLockModal isLocked={true} onUnlock={handleUnlock} />);

    const logoutButton = screen.getByRole('button', { name: /đăng xuất tài khoản khác/i });
    fireEvent.click(logoutButton);

    expect(handleUnlock).toHaveBeenCalledTimes(1);
  });
});
