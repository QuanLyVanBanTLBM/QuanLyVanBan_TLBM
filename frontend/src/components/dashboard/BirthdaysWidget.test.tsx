import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import BirthdaysWidget from './BirthdaysWidget';

describe('BirthdaysWidget', () => {
  it('renders nothing when the dashboard API omits birthday data', () => {
    const { container } = render(<BirthdaysWidget />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders staff supplied by the dashboard API', () => {
    render(<BirthdaysWidget birthdays={[
      { id: 101, name: 'Nguyễn Văn Minh', birthdate: '24/09', position: 'Chuyên viên', department: 'Văn phòng' },
    ]} />);
    expect(screen.getAllByText('Nguyễn Văn Minh')).toHaveLength(2);
  });

  it('sắp xếp theo thứ bậc chức vụ (Trưởng bộ phận trước Văn thư)', () => {
    const birthdays = [
      { id: 1, name: 'Nguyễn Văn Thư', birthdate: '31/10 (Hôm nay)', isToday: true, position: 'Văn thư', department: 'Ban kiểm toán nội bộ' },
      { id: 2, name: 'Huỳnh Thị Yến', birthdate: '31/10 (Hôm nay)', isToday: true, position: 'Trưởng Bộ phận', department: 'Bảo Long Bình Dương' },
    ];
    render(<BirthdaysWidget birthdays={birthdays} />);
    const names = screen.getAllByText(/(Huỳnh Thị Yến|Nguyễn Văn Thư)/).map(n => n.textContent);
    // Huỳnh Thị Yến (Trưởng bộ phận) phải xuất hiện trước Nguyễn Văn Thư (Văn thư)
    expect(names[0]).toBe('Huỳnh Thị Yến');
    expect(names[1]).toBe('Nguyễn Văn Thư');
  });
});
