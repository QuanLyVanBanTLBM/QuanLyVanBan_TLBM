import { render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const state = { perms: new Set<string>() };

vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({ loaded: true, can: (code: string) => state.perms.has(code) }),
}));
vi.mock('@layouts/MainLayout', () => ({ default: () => <Outlet /> }));
vi.mock('./moduleRouteTable', () => ({
  MODULE_ROUTES: [
    { path: '/dashboard', Component: () => <div>trang tong quan</div> },
    { path: '/roles', Component: () => <div>trang phan quyen</div> },
    { path: '/login', Component: () => <div>trang dang nhap</div>, public: true },
  ],
}));

import AppRouter from './router';

function renderAt(path: string) {
  localStorage.setItem('tlbm_access_token', 't');
  localStorage.setItem('tlbm_session', 's');
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRouter currentTheme="light" onSelectTheme={() => {}} />
    </MemoryRouter>,
  );
}

describe('AppRouter chặn URL theo quyền xem', () => {
  beforeEach(() => {
    state.perms = new Set();
    localStorage.clear();
  });

  it('gõ /roles khi thiếu view_nhomquyen thì về tổng quan', async () => {
    renderAt('/roles');
    expect(await screen.findByText('trang tong quan')).toBeInTheDocument();
    expect(screen.queryByText('trang phan quyen')).not.toBeInTheDocument();
  });

  it('có view_nhomquyen thì vào được /roles', async () => {
    state.perms = new Set(['view_nhomquyen']);
    renderAt('/roles');
    expect(await screen.findByText('trang phan quyen')).toBeInTheDocument();
  });

  it('trang đăng nhập công khai không bị guard', async () => {
    renderAt('/login');
    expect(await screen.findByText('trang dang nhap')).toBeInTheDocument();
  });
});
