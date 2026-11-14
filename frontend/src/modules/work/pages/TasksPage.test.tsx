import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import authService from '@lib/authService';
import TasksPage from './TasksPage';

// Hai trang con gọi API thật; ở đây chỉ cần biết trang nào đang hiển thị.
vi.mock('./TaskDetailPage', () => ({
  default: ({ taskId, onBack }: { taskId: number; onBack: () => void }) => (
    <div>
      <span data-testid="detail">Chi tiết việc {taskId}</span>
      <button type="button" onClick={onBack}>Quay lại</button>
    </div>
  ),
}));

vi.mock('./TaskListPage', () => ({
  default: ({ onOpenTask }: { onOpenTask: (taskId: number) => void }) => (
    <div>
      <span data-testid="list">Danh sách công việc</span>
      <button type="button" onClick={() => onOpenTask(32)}>Mở việc 32</button>
    </div>
  ),
}));

vi.mock('@lib/authService', () => ({
  default: { getSession: vi.fn() },
}));

const VIEW_STORAGE_KEY = 'work.view';

function dangNhap(id: number | undefined, username: string) {
  vi.mocked(authService.getSession).mockReturnValue({
    id,
    username,
    fullName: username,
    role: 'staff',
    roleTitle: 'Chuyên viên',
  });
}

describe('TasksPage — vị trí đã lưu gắn với từng tài khoản', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('cùng tài khoản: mở chi tiết rồi vào lại vẫn ở chi tiết', () => {
    dangNhap(5, 'vanthu');

    const { unmount } = render(<TasksPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Mở việc 32' }));
    expect(screen.getByTestId('detail').textContent).toBe('Chi tiết việc 32');
    unmount();

    render(<TasksPage />);
    expect(screen.getByTestId('detail').textContent).toBe('Chi tiết việc 32');
  });

  it('đổi tài khoản trên cùng tab: KHÔNG mở chi tiết việc của người trước', () => {
    // Văn thư (id 5) đang xem chi tiết việc 32.
    dangNhap(5, 'vanthu');
    const { unmount } = render(<TasksPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Mở việc 32' }));
    unmount();

    // Đăng xuất chỉ dọn localStorage, sessionStorage vẫn còn nguyên vị trí của Văn thư.
    expect(sessionStorage.getItem(VIEW_STORAGE_KEY)).toContain('"taskId":32');

    // Chuyên viên (id 6) đăng nhập trên cùng tab.
    dangNhap(6, 'chuyenvien');
    render(<TasksPage />);

    expect(screen.getByTestId('list')).toBeDefined();
    expect(screen.queryByTestId('detail')).toBeNull();
  });

  it('dữ liệu cũ không có owner thì không khôi phục', () => {
    sessionStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify({ mode: 'detail', taskId: 32 }));
    dangNhap(5, 'vanthu');

    render(<TasksPage />);

    expect(screen.getByTestId('list')).toBeDefined();
    expect(screen.queryByTestId('detail')).toBeNull();
  });

  it('chưa đăng nhập thì mở danh sách và không ghi đè vị trí đã lưu', () => {
    const daLuu = JSON.stringify({ mode: 'detail', taskId: 32, owner: '5' });
    sessionStorage.setItem(VIEW_STORAGE_KEY, daLuu);
    vi.mocked(authService.getSession).mockReturnValue(null);

    render(<TasksPage />);

    expect(screen.getByTestId('list')).toBeDefined();
    expect(sessionStorage.getItem(VIEW_STORAGE_KEY)).toBe(daLuu);
  });

  it('tài khoản không có id thì gắn theo username', () => {
    dangNhap(undefined, 'vanthu');
    const { unmount } = render(<TasksPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Mở việc 32' }));
    expect(sessionStorage.getItem(VIEW_STORAGE_KEY)).toContain('"owner":"vanthu"');
    unmount();

    dangNhap(undefined, 'chuyenvien');
    render(<TasksPage />);
    expect(screen.getByTestId('list')).toBeDefined();
  });
});
