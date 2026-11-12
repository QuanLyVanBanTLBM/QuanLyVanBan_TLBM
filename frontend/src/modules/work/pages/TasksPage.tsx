import React, { useEffect, useState } from 'react';
import authService from '@lib/authService';
import TaskDetailPage from './TaskDetailPage';
import TaskListPage from './TaskListPage';

/**
 * Điểm vào của module Công việc (page id 'tasks').
 * Dự án không dùng router theo URL nên việc chuyển giữa danh sách và chi tiết nằm trong state của trang,
 * lưu vào sessionStorage để không mất khi layout tạm gỡ trang lúc rê chuột qua menu.
 *
 * Vị trí đã lưu LUÔN gắn với tài khoản đã mở nó (`owner`). Đăng xuất chỉ dọn localStorage,
 * sessionStorage sống suốt vòng đời của tab, nên nếu không gắn chủ sở hữu thì người đăng nhập
 * sau trên cùng tab sẽ bị mở thẳng vào việc mà người trước đang xem — rò rỉ trạng thái giữa
 * hai tài khoản, và còn văng lỗi nếu tài khoản mới không có quyền xem việc đó.
 */

type View = { mode: 'list' } | { mode: 'detail'; taskId: number };

const VIEW_STORAGE_KEY = 'work.view';

/** Định danh người đang đăng nhập; chuỗi rỗng nghĩa là chưa xác định được. */
function currentOwner(): string {
  const session = authService.getSession();
  if (!session) return '';
  return String(session.id ?? session.username ?? '');
}

function readView(owner: string): View {
  // Chưa xác định được người dùng thì không khôi phục gì cho chắc.
  if (!owner) return { mode: 'list' };
  try {
    const raw = window.sessionStorage.getItem(VIEW_STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Partial<View> & { owner?: string }) : null;
    // Thiếu owner = dữ liệu của bản cũ, cũng không khôi phục vì không biết của ai.
    if (
      parsed
      && parsed.owner === owner
      && parsed.mode === 'detail'
      && Number(parsed.taskId) > 0
    ) {
      return { mode: 'detail', taskId: Number(parsed.taskId) };
    }
  } catch {
    // Dữ liệu lưu bị hỏng thì mở danh sách.
  }
  return { mode: 'list' };
}

export default function TasksPage() {
  const owner = currentOwner();
  const [view, setView] = useState<View>(() => readView(owner));
  useEffect(() => {
    if (!owner) return;
    try {
      window.sessionStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify({ ...view, owner }));
    } catch {
      // Không lưu được thì chỉ mất vị trí khi quay lại.
    }
  }, [view, owner]);

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
