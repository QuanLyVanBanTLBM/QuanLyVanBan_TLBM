import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '@components/common/Badge';

describe('Badge UI Component', () => {
  it('renders label correctly', () => {
    render(<Badge>Mật</Badge>);
    expect(screen.getByText('Mật')).toBeInTheDocument();
  });

  it('renders with semantic variants', () => {
    const { rerender } = render(<Badge variant="danger">Tuyệt mật</Badge>);
    expect(screen.getByText('Tuyệt mật')).toHaveClass('text-danger');

    rerender(<Badge variant="success">Hoàn thành</Badge>);
    expect(screen.getByText('Hoàn thành')).toHaveClass('text-success');

    rerender(<Badge variant="warning">Đang xử lý</Badge>);
    expect(screen.getByText('Đang xử lý')).toHaveClass('text-warning-text');
  });

  it('renders with dot indicator when withDot is true', () => {
    const { container } = render(<Badge variant="primary" withDot>Trực tuyến</Badge>);
    const dot = container.querySelector('span.rounded-full');
    expect(dot).toBeInTheDocument();
  });
});

