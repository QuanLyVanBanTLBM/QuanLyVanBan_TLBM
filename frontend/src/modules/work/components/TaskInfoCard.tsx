import React from 'react';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '../hooks/useIsMobile';
import { Employee } from '../types/employee';
import { TaskDetail } from '../types/task';
import { daysUntil, isoToDisplay } from './DateInput';
import { employeeMeta } from './EmployeeSelect';
import TaskAttachmentList from './TaskAttachmentList';

/**
 * Khối "Nội dung công việc" theo ảnh mẫu, chia 2 cột nhỏ:
 * trái — nội dung, ngày tạo, người tạo và giao, tệp đính kèm;
 * phải — cán bộ chủ trì, thời hạn xử lý, yêu cầu xử lý.
 */

interface TaskInfoCardProps {
  task: TaskDetail;
  onError: (message: string) => void;
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6, whiteSpace: 'pre-line' }}>
        {children}
      </div>
    </div>
  );
}

/** "(Chức vụ - Phòng ban)" sau tên; bỏ qua khi thiếu dữ liệu để không hiện ngoặc rỗng. */
function PersonMeta({ person }: { person: Employee }) {
  const meta = employeeMeta(person);
  if (!meta) return null;
  return <span style={{ color: 'var(--text-secondary)' }}> ({meta})</span>;
}

function DeadlineHint({ task }: { task: TaskDetail }) {
  const { t } = useTranslation();
  if (task.status === 'HOAN_THANH') return null;
  const days = daysUntil(task.dueDate);
  const text = days > 0
    ? t('work.infoCard.deadlineDaysLeft', { days: String(days) })
    : days === 0
      ? t('work.infoCard.deadlineToday')
      : t('work.infoCard.deadlineOverdue', { days: String(-days) });
  const color =
    days < 0 ? 'var(--color-danger)' : days <= 2 ? 'var(--color-warning-text)' : 'var(--text-secondary)';
  return <span style={{ marginLeft: '8px', fontSize: '0.8rem', fontWeight: 700, color }}>({text})</span>;
}

export default function TaskInfoCard({ task, onError }: TaskInfoCardProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  return (
    <section
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: isMobile ? '14px 14px' : '18px 20px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <h2 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '16px' }}>
        <i className="fa-solid fa-file-lines" style={{ color: 'var(--color-primary)', marginRight: '8px' }} />
        {t('work.infoCard.heading')}
      </h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(min(260px, 100%), 1fr))',
          gap: '16px 28px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <Item label={t('work.infoCard.labelTitle')}>{task.title}</Item>
          <Item label={t('work.infoCard.labelCreatedDate')}>{isoToDisplay(task.createdDate)}</Item>
          <Item label={t('work.infoCard.labelCreator')}>
            {task.creator.fullName}
            <PersonMeta person={task.creator} />
          </Item>
          <Item label={t('work.infoCard.labelAttachments')}>
            <TaskAttachmentList files={task.attachments} onError={onError} compact />
          </Item>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <Item label={t('work.infoCard.labelHost')}>
            {task.host ? (
              <>
                {task.host.fullName}
                <PersonMeta person={task.host} />
              </>
            ) : (
              '—'
            )}
          </Item>
          <Item label={t('work.infoCard.labelDueDate')}>
            {isoToDisplay(task.dueDate)}
            <DeadlineHint task={task} />
          </Item>
          <Item label={t('work.infoCard.labelRequirement')}>{task.requirement}</Item>
        </div>
      </div>
    </section>
  );
}
