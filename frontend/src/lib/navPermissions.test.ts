import { describe, expect, it } from 'vitest';
import { MAIN_MODULES } from '@lib/constants';
import { filterModulesByPermission } from './navPermissions';

const pagesOf = (codes: string[], loaded = true) =>
  filterModulesByPermission(MAIN_MODULES, loaded, (c) => codes.includes(c)).flatMap((m) => m.subItems.map((s) => s.id));

describe('filterModulesByPermission', () => {
  it('ẩn mục cần quyền xem khi tài khoản không có quyền, giữ mục backend cho mọi người đăng nhập', () => {
    const pages = pagesOf([]);
    expect(pages).toEqual(expect.arrayContaining(['dashboard', 'tasks', 'documents_incoming', 'documents_outgoing']));
    for (const hidden of ['records', 'record_types', 'resources', 'birthdays', 'meetings', 'organizations', 'positions', 'employees', 'roles', 'ai_assistant']) {
      expect(pages).not.toContain(hidden);
    }
  });

  it('chỉ hiện Phân Quyền & Vai Trò khi có view_nhomquyen', () => {
    expect(pagesOf(['view_nhomquyen'])).toContain('roles');
    expect(pagesOf(['view_hoso'])).not.toContain('roles');
  });

  it('hiện mục tương ứng khi có đúng mã quyền xem', () => {
    const pages = pagesOf(['view_hoso', 'view_tailieu', 'view_chucvu']);
    expect(pages).toEqual(expect.arrayContaining(['records', 'resources', 'positions']));
    expect(pages).not.toContain('employees');
  });

  it('ẩn mục cần quyền khi quyền chưa tải xong', () => {
    expect(pagesOf(['view_hoso'], false)).not.toContain('records');
  });

  it('bỏ phân hệ không còn mục con và đặt lại trang mặc định về mục còn hiện', () => {
    const modules = filterModulesByPermission(MAIN_MODULES, true, (c) => c === 'view_nhomquyen');
    expect(modules.find((m) => m.id === 'ai')).toBeUndefined();
    expect(modules.find((m) => m.id === 'records_resources')).toBeUndefined();
    const system = modules.find((m) => m.id === 'system');
    expect(system?.subItems.map((s) => s.id)).toEqual(['roles']);
    expect(system?.defaultPage).toBe('roles');
  });
});
