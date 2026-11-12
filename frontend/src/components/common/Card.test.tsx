import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@components/common/Card';

describe('Card UI Component', () => {
  it('renders Card with nested elements', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Văn bản đến mới</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Nội dung chi tiết tài liệu...</p>
        </CardContent>
        <CardFooter>
          <span>Nhóm 1</span>
        </CardFooter>
      </Card>
    );

    expect(screen.getByText('Văn bản đến mới')).toBeInTheDocument();
    expect(screen.getByText('Nội dung chi tiết tài liệu...')).toBeInTheDocument();
    expect(screen.getByText('Nhóm 1')).toBeInTheDocument();
  });

  it('applies glass and hover effects', () => {
    const { container } = render(<Card glass hoverEffect>Thẻ kính</Card>);
    expect(container.firstChild).toHaveClass('backdrop-blur-md');
    expect(container.firstChild).toHaveClass('hover:-translate-y-1');
  });
});

