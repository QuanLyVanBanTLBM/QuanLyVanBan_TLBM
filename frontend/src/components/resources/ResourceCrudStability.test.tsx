import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Toast } from './Toast';
import { CategoryManagementModal } from './CategoryManagementModal';
import { ResourceCategory, ResourceType } from '@app-types/resource';

vi.mock('@lib/authService', () => ({
  authService: {
    getSession: () => ({
      username: 'admin',
      fullName: 'Quản trị viên',
      roles: ['ADMIN'],
    }),
  },
}));

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({
    can: () => true,
    isSuperuser: true,
    isSystemAdmin: true,
  }),
}));

describe('Issue #824: Resource CRUD & Toast Stability', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('Toast không reset tiến trình countdown khi component cha re-render tạo mới hàm onClose', () => {
    vi.useFakeTimers();
    const initialOnClose = vi.fn();
    const updatedOnClose = vi.fn();
    const toast = {
      id: 101,
      message: 'Đã lưu tài liệu',
      type: 'success' as const,
      duration: 1000,
    };

    const { rerender } = render(
      <Toast toast={toast} onClose={initialOnClose} />
    );

    act(() => {
      vi.advanceTimersByTime(520);
    });

    const progressBar = screen.getByRole('status').querySelector('[style*="width"]') as HTMLElement | null;
    expect(progressBar).not.toBeNull();
    const widthAtHalfway = parseFloat(progressBar!.style.width);
    expect(widthAtHalfway).toBeLessThan(60);
    expect(widthAtHalfway).toBeGreaterThan(25);

    // Parent re-renders with a new inline callback function reference (same toast instance)
    rerender(<Toast toast={toast} onClose={updatedOnClose} />);

    act(() => {
      vi.advanceTimersByTime(120);
    });

    const widthAfterRerender = parseFloat(
      (screen.getByRole('status').querySelector('[style*="width"]') as HTMLElement).style.width
    );
    expect(widthAfterRerender).toBeLessThan(widthAtHalfway);

    // Complete remaining duration (~360ms left of 1000ms) -> calls latest onClose
    act(() => {
      vi.advanceTimersByTime(440);
    });

    expect(initialOnClose).not.toHaveBeenCalled();
    expect(updatedOnClose).toHaveBeenCalledTimes(1);
  });

  it('CategoryManagementModal giữ ConfirmationModal mở ở trạng thái loading cho đến khi xóa thư mục hoàn tất', async () => {
    let resolveDelete!: () => void;
    const onDeleteCategory = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveDelete = resolve;
        })
    );

    const categories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ky_hieu: 'TM-01', ten_tai_lieu: 'Thư mục Test' },
    ];

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={vi.fn()}
        categories={categories}
        types={[]}
        onSaveCategory={vi.fn()}
        onDeleteCategory={onDeleteCategory}
        onSaveType={vi.fn()}
        onDeleteType={vi.fn()}
      />
    );

    fireEvent.click(screen.getByLabelText('Thao tác với thư mục Thư mục Test'));
    fireEvent.click(screen.getByRole('button', { name: 'Xóa' }));

    expect(screen.getByText('Xác nhận xóa thư mục')).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /Xóa thư mục/i });
    fireEvent.click(confirmBtn);

    expect(onDeleteCategory).toHaveBeenCalledWith(1);
    expect(screen.getByText('Xác nhận xóa thư mục')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xóa thư mục/i })).toBeDisabled();

    await act(async () => {
      resolveDelete();
    });

    await waitFor(() => {
      expect(screen.queryByText('Xác nhận xóa thư mục')).not.toBeInTheDocument();
    });
  });

  it('CategoryManagementModal giữ ConfirmationModal mở ở trạng thái loading cho đến khi xóa loại tài liệu hoàn tất', async () => {
    let resolveDeleteType!: () => void;
    const onDeleteType = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveDeleteType = resolve;
        })
    );

    const categories: ResourceCategory[] = [
      { id: 1, stt_uu_tien: 1, ky_hieu: 'TM-01', ten_tai_lieu: 'Thư mục Test' },
    ];
    const types: ResourceType[] = [
      { id: 10, dm_tai_lieu: 1, ten_loai: 'Loại Xóa Test', is_public: true },
    ];

    render(
      <CategoryManagementModal
        isOpen={true}
        onClose={vi.fn()}
        categories={categories}
        types={types}
        onSaveCategory={vi.fn()}
        onDeleteCategory={vi.fn()}
        onSaveType={vi.fn()}
        onDeleteType={onDeleteType}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Loại tài liệu/i }));
    fireEvent.click(screen.getByLabelText('Thao tác với loại tài liệu Loại Xóa Test'));
    fireEvent.click(screen.getByRole('button', { name: 'Xóa' }));

    expect(screen.getByText('Xác nhận xóa loại tài liệu')).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /Xóa loại tài liệu/i });
    fireEvent.click(confirmBtn);

    expect(onDeleteType).toHaveBeenCalledWith(10);
    expect(screen.getByText('Xác nhận xóa loại tài liệu')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xóa loại tài liệu/i })).toBeDisabled();

    await act(async () => {
      resolveDeleteType();
    });

    await waitFor(() => {
      expect(screen.queryByText('Xác nhận xóa loại tài liệu')).not.toBeInTheDocument();
    });
  });
});
