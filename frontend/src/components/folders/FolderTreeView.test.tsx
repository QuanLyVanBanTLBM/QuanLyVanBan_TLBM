import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FolderTreeView } from './FolderTreeView';
import { FolderItem } from '@app-types/resource';

const tree = [{ id: 1, name: 'Thư mục gốc', depth: 0, children: [] }] as unknown as FolderItem[];

function renderTree(flags: { canAdd?: boolean; canChange?: boolean; canDelete?: boolean }) {
  render(
    <FolderTreeView
      tree={tree}
      selectedFolderId={null}
      onSelectFolder={vi.fn()}
      onCreateChild={vi.fn()}
      onEditFolder={vi.fn()}
      onMoveFolder={vi.fn()}
      onDeleteFolder={vi.fn()}
      {...flags}
    />,
  );
}

describe('FolderTreeView — nút thao tác theo quyền', () => {
  it('ẩn toàn bộ nút thao tác khi không có quyền thêm, sửa, xóa', () => {
    renderTree({ canAdd: false, canChange: false, canDelete: false });
    expect(screen.queryByTitle(/thêm thư mục con|add subfolder/i)).toBeNull();
    expect(screen.queryByTitle(/tùy chọn khác|more options/i)).toBeNull();
  });

  it('chỉ có quyền thêm thì menu không có Đổi tên, Di chuyển, Xóa', () => {
    renderTree({ canAdd: true, canChange: false, canDelete: false });
    fireEvent.click(screen.getByTitle(/tùy chọn khác|more options/i));
    expect(screen.getAllByText(/thêm thư mục con|add subfolder/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/đổi tên|rename/i)).toBeNull();
    expect(screen.queryByText(/di chuyển|move/i)).toBeNull();
    expect(screen.queryByText(/^xóa|^delete/i)).toBeNull();
  });

  it('đủ quyền thì thấy cả bốn thao tác', () => {
    renderTree({ canAdd: true, canChange: true, canDelete: true });
    fireEvent.click(screen.getByTitle(/tùy chọn khác|more options/i));
    expect(screen.getByText(/đổi tên|rename/i)).toBeInTheDocument();
    expect(screen.getByText(/di chuyển|move/i)).toBeInTheDocument();
    expect(screen.getByText(/xóa|delete/i)).toBeInTheDocument();
  });
});
