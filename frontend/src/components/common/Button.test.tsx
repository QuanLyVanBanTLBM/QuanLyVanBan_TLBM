import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@components/common/Button';

describe('Button UI Component', () => {
  it('renders children correctly', () => {
    render(<Button>Xác nhận văn bản</Button>);
    expect(screen.getByText('Xác nhận văn bản')).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Bấm để gửi</Button>);
    fireEvent.click(screen.getByText('Bấm để gửi'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders with different variants', () => {
    const { rerender } = render(<Button variant="primary">Lưu</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-primary');

    rerender(<Button variant="danger">Xóa</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-danger');

    rerender(<Button variant="outline">Hủy</Button>);
    expect(screen.getByRole('button')).toHaveClass('border-primary');
  });

  it('disables button when disabled or isLoading is true', () => {
    const { rerender } = render(<Button disabled>Không khả dụng</Button>);
    expect(screen.getByRole('button')).toBeDisabled();

    rerender(<Button isLoading>Đang lưu...</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText('Đang lưu...')).toBeInTheDocument();
  });

  it('renders with icon when provided', () => {
    const { container } = render(<Button icon="fa-solid fa-plus">Thêm mới</Button>);
    const iconEl = container.querySelector('i.fa-plus');
    expect(iconEl).toBeInTheDocument();
  });
});

