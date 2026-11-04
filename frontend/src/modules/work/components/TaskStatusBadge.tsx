import React from 'react';
import { useTranslation } from '@i18n/translate';
import { TASK_STATUS_LABELS, TaskStatus } from '../types/task';
import './TaskStatusBadge.css';

interface StatusStyle {
  icon: string;
  color: string;
  background: string;
}

const STATUS_STYLES: Record<TaskStatus, StatusStyle> = {
  // "Chờ xử lý" dùng màu vàng amber (theo yêu cầu GVHD). Không có token badge vàng dùng chung
  // nên đặt hex trực tiếp tại đây, không đụng global.css. Nền vàng nhạt amber-100 + chữ nâu đậm
  // amber-900 cho tương phản ~8:1 (đạt WCAG AAA) để chữ không bị chìm trên nền vàng. Giữ icon đồng hồ cát.
  CHO_XU_LY: {
    icon: 'fa-regular fa-hourglass-half',
    color: '#78350F',
    background: '#FEF3C7',
  },
  // Các trạng thái còn lại giữ nguyên: Đang xử lý / Chờ duyệt / Chưa hoàn thành = xám,
  // Hoàn thành = xanh, Quá hạn = đỏ. Giữ nguyên icon từng trạng thái.
  DANG_XU_LY: {
    icon: 'fa-solid fa-pen-ruler',
    color: 'var(--color-task-badge-gray-text)',
    background: 'var(--color-task-badge-gray-bg)',
  },
  CHO_DUYET: {
    icon: 'fa-regular fa-clock',
    color: 'var(--color-task-badge-gray-text)',
    background: 'var(--color-task-badge-gray-bg)',
  },
  HOAN_THANH: {
    icon: 'fa-solid fa-circle-check',
    color: 'var(--color-task-badge-green-text)',
    background: 'var(--color-task-badge-green-bg)',
  },
  CHUA_HOAN_THANH: {
    icon: 'fa-solid fa-triangle-exclamation',
    color: 'var(--color-task-badge-gray-text)',
    background: 'var(--color-task-badge-gray-bg)',
  },
  QUA_HAN: {
    icon: 'fa-solid fa-circle-exclamation',
    color: 'var(--color-task-badge-red-text)',
    background: 'var(--color-task-badge-red-bg)',
  },
};

interface TaskStatusBadgeProps {
  status: TaskStatus;
  /** Nhãn do API trả về; bỏ trống thì dùng nhãn mặc định trong types/task.ts. */
  label?: string;
  size?: 'sm' | 'md';
}

export default function TaskStatusBadge({ status, label, size = 'md' }: TaskStatusBadgeProps) {
  const { t } = useTranslation();
  const style = STATUS_STYLES[status] || STATUS_STYLES.CHO_XU_LY;
  const text = label || t(`work.status.${status}`) || TASK_STATUS_LABELS[status] || status;

  return (
    <span
      // class để TaskStatusBadge.css đảo tông amber ở dark mode (chỉ áp cho CHO_XU_LY).
      className={`work-task-badge work-task-badge--${status}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: size === 'sm' ? '2px 8px' : '4px 12px',
        borderRadius: '9999px',
        background: style.background,
        color: style.color,
        fontSize: size === 'sm' ? '12px' : '13px',
        fontWeight: 500,
        whiteSpace: 'nowrap',
        lineHeight: 1.6,
      }}
      title={text}
    >
      <i className={style.icon} style={{ fontSize: '0.72em' }} />
      <span>{text}</span>
    </span>
  );
}
