import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Toast, ToastNotification } from './Toast';

describe('Toast Component', () => {
  it('renders nothing when toast is null', () => {
    const { container } = render(<Toast toast={null} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders toast message and title correctly via portal on top', () => {
    const mockToast: ToastNotification = {
      id: 1,
      message: 'Đã thêm mới danh mục thành công',
      title: 'Thêm mới Thư mục',
      type: 'success',
    };

    render(<Toast toast={mockToast} onClose={vi.fn()} />);

    expect(screen.getByText('Thêm mới Thư mục')).toBeInTheDocument();
    expect(screen.getByText('Đã thêm mới danh mục thành công')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    const mockToast: ToastNotification = {
      id: 2,
      message: 'Đã xóa tài liệu',
      type: 'danger',
    };

    render(<Toast toast={mockToast} onClose={onClose} />);

    const closeBtn = screen.getByRole('button', { name: /đóng thông báo/i });
    fireEvent.click(closeBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('translates raw roles.messages.permissionDenied and replaces storage error title with permission denied title', () => {
    const mockToast: ToastNotification = {
      id: 3,
      message: 'roles.messages.permissionDenied',
      title: 'Lỗi lưu trữ',
      type: 'danger',
    };

    render(<Toast toast={mockToast} onClose={vi.fn()} />);

    expect(screen.queryByText('roles.messages.permissionDenied')).not.toBeInTheDocument();
    expect(screen.getByText('Bạn không có quyền thực hiện thao tác này.')).toBeInTheDocument();
    expect(screen.queryByText('Lỗi lưu trữ')).not.toBeInTheDocument();
    expect(screen.getByText('Từ chối quyền hạn')).toBeInTheDocument();
  });

  it('renders positioned at top-right corner instead of top-center', () => {
    const mockToast: ToastNotification = {
      id: 4,
      message: 'Thông báo góc phải',
      type: 'info',
    };

    render(<Toast toast={mockToast} onClose={vi.fn()} />);

    const toastElement = screen.getByRole('status');
    expect(toastElement).toBeInTheDocument();
    expect(toastElement.className).toContain('right-5');
    expect(toastElement.className).toContain('sm:right-6');
    expect(toastElement.className).not.toContain('left-1/2');
    expect(toastElement.className).not.toContain('-translate-x-1/2');
  });
});
