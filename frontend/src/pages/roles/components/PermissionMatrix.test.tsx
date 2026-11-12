import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { PermissionMatrix } from './PermissionMatrix';
import { Permission } from '@app-types/authorization';
import { setLanguage } from '@i18n/translate';

const PERMISSIONS: Permission[] = [
  { id: 1, name: 'Xem danh sách chức vụ', codename: 'view_chucvu', module_ten: 'Chức vụ' },
  { id: 2, name: 'Thêm chức vụ', codename: 'add_chucvu', module_ten: 'Chức vụ' },
  { id: 3, name: 'Xuất Excel đơn vị/phòng ban', codename: 'export_donvi', module_ten: 'Đơn vị, phòng ban' },
  { id: 4, name: 'Thêm phòng họp', codename: 'add_phonghop', module_ten: 'Phòng họp (danh mục)' },
];

function renderMatrix(selected: number[] = []) {
  const onToggle = vi.fn();
  render(<PermissionMatrix permissions={PERMISSIONS} selectedIds={new Set(selected)} onToggle={onToggle} />);
  return { onToggle, search: screen.getByRole('textbox') };
}

describe('PermissionMatrix', () => {
  afterEach(() => act(() => setLanguage('vi')));

  it('translates module and permission names when language changes', () => {
    renderMatrix();
    act(() => setLanguage('en'));

    expect(screen.getByText('1. Positions')).toBeInTheDocument();
    expect(screen.getByText('View position list')).toBeInTheDocument();
    expect(screen.getByText('2. Units and departments')).toBeInTheDocument();
    expect(screen.getByText('Export units and departments to Excel')).toBeInTheDocument();
  });

  it('finds a permission by its translated English name', () => {
    act(() => setLanguage('en'));
    const { search } = renderMatrix();
    fireEvent.change(search, { target: { value: 'export units' } });

    expect(screen.getAllByRole('checkbox')).toHaveLength(1);
    expect(screen.getByText('Export units and departments to Excel')).toBeInTheDocument();
  });

  it('falls back to API labels for a permission without a translation', () => {
    act(() => setLanguage('en'));
    render(
      <PermissionMatrix
        permissions={[{ id: 9, codename: 'custom_qa', name: 'Quyền mới', module_ten: 'Module mới' }]}
        selectedIds={new Set()}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByText('1. Module mới')).toBeInTheDocument();
    expect(screen.getByText('Quyền mới')).toBeInTheDocument();
  });

  it('translates the export and validity permissions added after the first label set', () => {
    act(() => setLanguage('en'));
    render(
      <PermissionMatrix
        permissions={[
          { id: 20, codename: 'export_cbnv', name: 'Xuất danh bạ CBNV', module_ten: 'CBNV' },
          { id: 21, codename: 'change_hieu_luc_vanbanden', name: 'Đổi hiệu lực văn bản đến', module_ten: 'Văn bản đến' },
        ]}
        selectedIds={new Set()}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByText('Export employee directory')).toBeInTheDocument();
    expect(screen.getByText('Change validity of incoming documents')).toBeInTheDocument();
    expect(screen.getByText('2. Incoming documents')).toBeInTheDocument();
  });

  it('groups permissions by module and shows every permission', () => {
    renderMatrix([1]);
    expect(screen.getByText('1. Chức vụ')).toBeInTheDocument();
    expect(screen.getByText('2. Đơn vị, phòng ban')).toBeInTheDocument();
    expect(screen.getAllByRole('checkbox')).toHaveLength(4);
    expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
  });

  it('filters by name regardless of case', () => {
    const { search } = renderMatrix();
    fireEvent.change(search, { target: { value: 'XUẤT EXCEL' } });
    expect(screen.getAllByRole('checkbox')).toHaveLength(1);
    expect(screen.getByText('Xuất Excel đơn vị/phòng ban')).toBeInTheDocument();
  });

  it('filters without requiring Vietnamese diacritics', () => {
    const { search } = renderMatrix();
    fireEvent.change(search, { target: { value: 'chuc vu' } });
    expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    expect(screen.queryByText('Thêm phòng họp')).not.toBeInTheDocument();
    fireEvent.change(search, { target: { value: 'phong hop' } });
    expect(screen.getAllByRole('checkbox')).toHaveLength(1);
  });

  it('filters by codename', () => {
    const { search } = renderMatrix();
    fireEvent.change(search, { target: { value: 'export_donvi' } });
    expect(screen.getAllByRole('checkbox')).toHaveLength(1);
  });

  it('shows an empty message when nothing matches and recovers when cleared', () => {
    const { search } = renderMatrix();
    fireEvent.change(search, { target: { value: 'khong-co-quyen-nay' } });
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0);
    expect(screen.getByText('Không tìm thấy quyền phù hợp.')).toBeInTheDocument();
    fireEvent.change(search, { target: { value: '' } });
    expect(screen.getAllByRole('checkbox')).toHaveLength(4);
  });

  it('keeps toggling the right permission while filtered', () => {
    const { search, onToggle } = renderMatrix();
    fireEvent.change(search, { target: { value: 'add_phonghop' } });
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledWith(4);
  });

  it('disables every checkbox in read-only mode and never toggles', () => {
    const onToggle = vi.fn();
    render(<PermissionMatrix permissions={PERMISSIONS} selectedIds={new Set([1])} onToggle={onToggle} readOnly />);
    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((checkbox) => expect(checkbox).toBeDisabled());
    expect(checkboxes[0]).toBeChecked();
    fireEvent.click(checkboxes[1]);
    expect(onToggle).not.toHaveBeenCalled();
  });
});
