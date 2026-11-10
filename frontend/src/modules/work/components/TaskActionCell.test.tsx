import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TaskActionCell from './TaskActionCell';
import { TaskListItem } from '../types/task';

function makeTask(permissions: Partial<TaskListItem['permissions']>): TaskListItem {
  return {
    id: 7,
    title: 'Việc thử',
    permissions: {
      canEdit: false,
      canDelete: false,
      canApprove: false,
      canUnapprove: false,
      ...permissions,
    },
  } as unknown as TaskListItem;
}

const noop = () => undefined;

describe('TaskActionCell — gia hạn việc quá hạn', () => {
  it('hiện nút Gia hạn khi có cờ canExtend và gọi onExtend', () => {
    const onExtend = vi.fn();
    const task = makeTask({ canExtend: true });
    render(
      <TaskActionCell task={task} onEdit={noop} onDelete={noop} onApprove={noop} onUnapprove={noop} onExtend={onExtend} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /gia hạn|extend/i }));
    expect(onExtend).toHaveBeenCalledWith(task);
  });

  it('không hiện nút Gia hạn khi thiếu cờ canExtend', () => {
    render(
      <TaskActionCell
        task={makeTask({ canEdit: true })}
        onEdit={noop}
        onDelete={noop}
        onApprove={noop}
        onUnapprove={noop}
        onExtend={noop}
      />,
    );
    expect(screen.queryByRole('button', { name: /gia hạn|extend/i })).toBeNull();
  });
});
