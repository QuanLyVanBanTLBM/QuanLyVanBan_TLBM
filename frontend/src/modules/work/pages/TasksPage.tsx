import React, { useEffect, useState } from 'react';
import TaskDetailPage from './TaskDetailPage';
import TaskListPage from './TaskListPage';

/**
 * Điểm vào của module Công việc (page id 'tasks').
 * Dự án không dùng router theo URL nên việc chuyển giữa danh sách và chi tiết nằm trong state của trang,
 * lưu vào sessionStorage để không mất khi layout tạm gỡ trang lúc rê chuột qua menu.
 */

type View = { mode: 'list' } | { mode: 'detail'; taskId: number };

const VIEW_STORAGE_KEY = 'work.view';

function readView(): View {
  try {
    const raw = window.sessionStorage.getItem(VIEW_STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as View) : null;
    if (parsed && parsed.mode === 'detail' && Number(parsed.taskId) > 0) {
      return { mode: 'detail', taskId: Number(parsed.taskId) };
    }
  } catch {
    // Dữ liệu lưu bị hỏng thì mở danh sách.
  }
  return { mode: 'list' };
}

export default function TasksPage() {
  const [view, setView] = useState<View>(readView);
  useEffect(() => {
    try {
      window.sessionStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(view));
    } catch {
      // Không lưu được thì chỉ mất vị trí khi quay lại.
    }
  }, [view]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {view.mode === 'detail' ? (
        <TaskDetailPage
          key={`detail-${view.taskId}`}
          taskId={view.taskId}
          onBack={() => setView({ mode: 'list' })}
        />
      ) : (
        <TaskListPage
          onOpenTask={(taskId) => setView({ mode: 'detail', taskId })}
        />
      )}
    </div>
  );
}
