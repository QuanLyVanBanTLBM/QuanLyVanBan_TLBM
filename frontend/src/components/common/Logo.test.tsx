import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Logo } from './Logo';

describe('Logo Component', () => {
  it('renders auto variant with responsive dark/light images', () => {
    const { container } = render(<Logo size="md" />);
    const images = container.querySelectorAll('img');
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute('src', '/baolong-logo.png');
    expect(images[1]).toHaveAttribute('src', '/baolong-logo-color.png');
  });

  it('renders single white variant image', () => {
    render(<Logo variant="white" alt="Bảo Long Trắng" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/baolong-logo.png');
    expect(img).toHaveAttribute('alt', 'Bảo Long Trắng');
  });

  it('renders single dark variant image (color logo for light mode)', () => {
    render(<Logo variant="dark" alt="Bảo Long Xanh Vàng" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/baolong-logo-color.png');
    expect(img).toHaveAttribute('alt', 'Bảo Long Xanh Vàng');
  });

  it('renders single color variant image', () => {
    render(<Logo variant="color" alt="Bảo Long Xanh Vàng" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/baolong-logo-color.png');
    expect(img).toHaveAttribute('alt', 'Bảo Long Xanh Vàng');
  });

  it('renders icon only mode correctly', () => {
    render(<Logo iconOnly variant="white" alt="Icon Bảo Long" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', '/baolong-icon.png');
    expect(img).toHaveClass('h-8');
    expect(img).toHaveClass('w-8');
  });

  it('renders fallback badge on image error', () => {
    render(<Logo variant="white" alt="Lỗi Logo" />);
    const img = screen.getByRole('img');
    fireEvent.error(img);

    expect(screen.getByText('BL')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
});

