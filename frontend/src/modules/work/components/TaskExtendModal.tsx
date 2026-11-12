import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { toMessage } from '../api/client';
import { extendTask } from '../api/tasks';
import { TaskDetail } from '../types/task';
import DateInput, { isoToDisplay, todayIso } from './DateInput';
import WorkAlert from './WorkAlert';
import WorkModal from './WorkModal';

/**
 * Gia hạn công việc đã quá hạn: chỉ đổi hạn xử lý, trạng thái tự tính lại theo hạn mới.
 * Chỉ người giao việc và quản trị hệ thống thấy nút mở hộp thoại này (cờ permissions.canExtend).
 */

interface TaskExtendModalProps {
  task: { id: number; title: string; dueDate: string } | null;
  onClose: () => void;
  onExtended: (task: TaskDetail) => void;
}

interface ExtendFormProps {
  task: { id: number; title: string; dueDate: string };
  onClose: () => void;
  onExtended: (task: TaskDetail) => void;
}

/** Dựng lại theo key=task.id nên trạng thái ô nhập tự về ban đầu khi mở cho việc khác. */
export default function TaskExtendModal({ task, onClose, onExtended }: TaskExtendModalProps) {
  if (!task) return null;
  return <ExtendForm key={task.id} task={task} onClose={onClose} onExtended={onExtended} />;
}

function ExtendForm({ task, onClose, onExtended }: ExtendFormProps) {
  const { t } = useTranslation();
  const [dueDate, setDueDate] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!dueDate) {
      setError(t('work.extend.required'));
      return;
    }
    setBusy(true);
    try {
      const detail = await extendTask(task.id, dueDate);
      onExtended(detail);
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <WorkModal
      open
      title={t('work.extend.title')}
      subtitle={task.title}
      width="sm"
      busy={busy}
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            style={{
              padding: '9px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontWeight: 600,
              fontSize: '0.86rem',
              cursor: busy ? 'not-allowed' : 'pointer',
              opacity: busy ? 0.6 : 1,
            }}
          >
            {t('work.common.cancel')}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={handleSubmit}
            style={{
              padding: '9px 18px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: '0.86rem',
              cursor: busy ? 'not-allowed' : 'pointer',
              opacity: busy ? 0.6 : 1,
            }}
          >
            {busy ? t('work.common.saving') : t('work.extend.confirm')}
          </button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {error && <WorkAlert variant="danger" title={t('work.extend.errorTitle')} message={error} />}
        <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
          {t('work.extend.hint', { dueDate: isoToDisplay(task.dueDate) })}
        </p>
        <label htmlFor="work-extend-due-date" style={{ fontWeight: 700, fontSize: '0.86rem' }}>
          {t('work.extend.newDueDate')}
        </label>
        <DateInput
          id="work-extend-due-date"
          value={dueDate}
          min={todayIso()}
          invalid={Boolean(error) && !dueDate}
          onChange={(value) => {
            setDueDate(value);
            setError('');
          }}
        />
      </div>
    </WorkModal>
  );
}
