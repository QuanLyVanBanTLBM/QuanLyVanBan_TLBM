import React from 'react';
import { useTranslation } from '@i18n/translate';
import { TaskListItem } from '../types/task';

/**
 * Ô "Tác vụ" trong bảng. Nút hiện theo cờ permissions do API tính, frontend không tự suy quyền.
 * - Duyệt: chuyển sang trang chi tiết để người duyệt xem bằng chứng trước.
 * - Hủy duyệt: làm ngay tại danh sách, trang cha hiện hộp xác nhận.
 */

interface TaskActionCellProps {
  task: TaskListItem;
  disabled?: boolean;
  onEdit: (task: TaskListItem) => void;
  onDelete: (task: TaskListItem) => void;
  onApprove: (task: TaskListItem) => void;
  onUnapprove: (task: TaskListItem) => void;
}

function IconButton({
  icon,
  label,
  color,
  disabled,
  onClick,
}: {
  icon: string;
  label: string;
  color: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      style={{
        width: '32px',
        height: '32px',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        color,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        fontSize: '0.85rem',
      }}
    >
      <i className={icon} />
    </button>
  );
}

function TextButton({
  label,
  icon,
  variant,
  disabled,
  onClick,
}: {
  label: string;
  icon: string;
  variant: 'primary' | 'warning';
  disabled: boolean;
  onClick: () => void;
}) {
  const isPrimary = variant === 'primary';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 10px',
        borderRadius: 'var(--radius-sm)',
        border: `1px solid ${isPrimary ? 'var(--color-success-border)' : 'var(--color-warning-border)'}`,
        background: isPrimary ? 'var(--color-success-subtle)' : 'var(--color-warning-subtle)',
        color: isPrimary ? 'var(--color-success)' : 'var(--color-warning-text)',
        fontSize: '0.78rem',
        fontWeight: 700,
        whiteSpace: 'nowrap',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <i className={icon} />
      {label}
    </button>
  );
}

export default function TaskActionCell({
  task,
  disabled = false,
  onEdit,
  onDelete,
  onApprove,
  onUnapprove,
}: TaskActionCellProps) {
  const { t } = useTranslation();
  const { canEdit, canDelete, canApprove, canUnapprove } = task.permissions;

  if (!canEdit && !canDelete && !canApprove && !canUnapprove) {
    return (
      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }} title={t('work.actions.viewOnly')}>
        —
      </span>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
      {canEdit && (
        <IconButton
          icon="fa-solid fa-pen"
          label={t('work.actions.edit')}
          color="var(--color-primary)"
          disabled={disabled}
          onClick={() => onEdit(task)}
        />
      )}
      {canDelete && (
        <IconButton
          icon="fa-solid fa-trash"
          label={t('work.actions.delete')}
          color="var(--color-danger)"
          disabled={disabled}
          onClick={() => onDelete(task)}
        />
      )}
      {canApprove && (
        <TextButton
          label={t('work.actions.approve')}
          icon="fa-solid fa-check"
          variant="primary"
          disabled={disabled}
          onClick={() => onApprove(task)}
        />
      )}
      {canUnapprove && (
        <TextButton
          label={t('work.actions.unapprove')}
          icon="fa-solid fa-rotate-left"
          variant="warning"
          disabled={disabled}
          onClick={() => onUnapprove(task)}
        />
      )}
    </div>
  );
}
