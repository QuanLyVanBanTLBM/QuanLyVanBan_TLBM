import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PagePermissionGuard from './PagePermissionGuard';

const state = { loaded: true, perms: new Set<string>() };

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({ loaded: state.loaded, can: (code: string) => state.perms.has(code) }),
}));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dashboard" element={<div>trang tong quan</div>} />
        <Route
          path="*"
          element={
            <PagePermissionGuard>
              <div>noi dung trang</div>
            </PagePermissionGuard>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PagePermissionGuard', () => {
  beforeEach(() => {
    state.loaded = true;
    state.perms = new Set();
  });

  it('chuyển về tổng quan khi gõ URL trang cần quyền xem mà thiếu quyền', () => {
    renderAt('/roles');
    expect(screen.getByText('trang tong quan')).toBeInTheDocument();
    expect(screen.queryByText('noi dung trang')).not.toBeInTheDocument();
  });

  it('cho vào khi có quyền xem tương ứng', () => {
    state.perms = new Set(['view_nhomquyen']);
    renderAt('/roles');
    expect(screen.getByText('noi dung trang')).toBeInTheDocument();
  });

  it('không hiện nội dung trong lúc quyền chưa tải', () => {
    state.loaded = false;
    renderAt('/roles');
    expect(screen.queryByText('noi dung trang')).not.toBeInTheDocument();
    expect(screen.queryByText('trang tong quan')).not.toBeInTheDocument();
  });

  it('trang không cần quyền xem riêng vẫn mở bình thường', () => {
    renderAt('/dashboard');
    expect(screen.getByText('trang tong quan')).toBeInTheDocument();
  });
});
