import React from 'react';
import { t, useTranslation } from '@i18n/translate';
import { FROZEN_STATUSES, ParticipantRole, TaskDetail } from '../types/task';
import { isoDateTimeToDisplay } from './DateInput';

/**
 * Thanh duyệt cuối trang chi tiết, chỉ dành cho người tạo, chủ trì và chỉ đạo.
 * Chờ duyệt → nút "Duyệt hoàn thành"; Hoàn thành → nút "Hủy duyệt".
 * Trạng thái khác thì chỉ hiện một dòng giải thích khi nào duyệt được.
 */

const APPROVER_ROLES: ParticipantRole[] = ['NGUOI_TAO', 'CHU_TRI', 'CHI_DAO'];

interface TaskApprovalBarProps {
  task: TaskDetail;
  busy: boolean;
  onApprove: () => void;
  onUnapprove: () => void;
}

function waitingReason(task: TaskDetail): string {
  if (FROZEN_STATUSES.includes(task.status)) {
    return t('work.approval.waitingFrozen');
  }
  return t('work.approval.waitingEvidence');
}

export default function TaskApprovalBar({ task, busy, onApprove, onUnapprove }: TaskApprovalBarProps) {
  const { t } = useTranslation();
  const { canApprove, canUnapprove } = task.permissions;
  const isApprover = task.myRoles.some((role) => APPROVER_ROLES.includes(role));

  if (!canApprove && !canUnapprove && !isApprover) return null;

  const buttonStyle = (color: string, subtle: string, border: string): React.CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    border: `1px solid ${border}`,
    background: subtle,
    color,
    fontWeight: 800,
    fontSize: '0.9rem',
    cursor: busy ? 'not-allowed' : 'pointer',
    opacity: busy ? 0.6 : 1,
  });

  let description = waitingReason(task);
  if (canApprove) {
    description = t('work.approval.readyToApprove');
  } else if (canUnapprove) {
    const who = task.approvedBy ? t('work.approval.approvedBy', { name: task.approvedBy.fullName }) : '';
    description = t('work.approval.alreadyApproved', { time: isoDateTimeToDisplay(task.approvedAt), by: who });
  }

  return (
    <section
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '14px',
        flexWrap: 'wrap',
        padding: '16px 20px',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', flex: '1 1 280px' }}>
        <i className="fa-solid fa-stamp" style={{ color: 'var(--color-primary)', marginRight: '8px' }} />
        {description}
      </div>
      {canApprove && (
        <button
          type="button"
          disabled={busy}
          onClick={onApprove}
          style={buttonStyle('var(--color-success)', 'var(--color-success-subtle)', 'var(--color-success-border)')}
        >
          <i className="fa-solid fa-check-double" />
          {t('work.approval.approveButton')}
        </button>
      )}
      {canUnapprove && (
        <button
          type="button"
          disabled={busy}
          onClick={onUnapprove}
          style={buttonStyle('var(--color-warning-text)', 'var(--color-warning-subtle)', 'var(--color-warning-border)')}
        >
          <i className="fa-solid fa-rotate-left" />
          {t('work.approval.unapproveButton')}
        </button>
      )}
    </section>
  );
}
