import React, { useCallback, useEffect, useState } from 'react';
import { t as tModule, useTranslation } from '@i18n/translate';
import { toMessage } from '../api/client';
import { getMe } from '../api/employees';
import { approveTask, createComment, deleteEvidence, listComments, openTask, unapproveTask } from '../api/taskActions';
import { getTask } from '../api/tasks';
import ConfirmDialog from '../components/ConfirmDialog';
import TaskApprovalBar from '../components/TaskApprovalBar';
import TaskCommentPanel from '../components/TaskCommentPanel';
import TaskInfoCard from '../components/TaskInfoCard';
import TaskPeopleCard from '../components/TaskPeopleCard';
import TaskStatusBadge from '../components/TaskStatusBadge';
import WorkAlert, { WorkAlertVariant } from '../components/WorkAlert';
import { useIsMobile } from '../hooks/useIsMobile';
import { Attachment, TaskComment, TaskDetail } from '../types/task';

/**
 * Trang chi tiết xử lý công việc, bố cục theo ảnh mẫu của thầy:
 * cột trái "Luồng xử lý"; cột phải "Nội dung công việc" và khu vực ý kiến; nút Duyệt cuối trang.
 *
 * Vừa vào trang thì gọi openTask: chủ trì / chỉ đạo / tham gia mở lần đầu (khi chưa quá hạn)
 * được tính là "đã mở"; người tạo mở không tính.
 */

interface TaskDetailPageProps {
  taskId: number;
  onBack: () => void;
}

type PendingAction = { type: 'approve' } | { type: 'unapprove' } | { type: 'deleteFile'; file: Attachment } | null;

function statusNotice(task: TaskDetail): { variant: WorkAlertVariant; message: string } {
  switch (task.status) {
    case 'CHO_XU_LY':
      return { variant: 'info', message: tModule('work.taskDetail.statusNotice.CHO_XU_LY') };
    case 'DANG_XU_LY':
      return { variant: 'info', message: tModule('work.taskDetail.statusNotice.DANG_XU_LY') };
    case 'CHO_DUYET':
      return { variant: 'warning', message: tModule('work.taskDetail.statusNotice.CHO_DUYET') };
    case 'HOAN_THANH':
      return { variant: 'success', message: tModule('work.taskDetail.statusNotice.HOAN_THANH') };
    default:
      return { variant: 'danger', message: tModule('work.taskDetail.statusNotice.frozen') };
  }
}

export default function TaskDetailPage({ taskId, onBack }: TaskDetailPageProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [pending, setPending] = useState<PendingAction>(null);
  const [pendingBusy, setPendingBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([openTask(taskId), listComments(taskId), getMe().catch(() => null)])
      .then(([detail, items, me]) => {
        if (cancelled) return;
        setTask(detail);
        setComments(items);
        setCurrentUserId(me ? me.id : null);
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(toMessage(cause));
      })
      .finally(() => {
        if (cancelled) return;
        setLoaded(true);
        setCommentsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(''), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  /** Tải lại cả công việc lẫn ý kiến sau mỗi thao tác để trạng thái và nút luôn khớp máy chủ. */
  const refresh = useCallback(async () => {
    setCommentsLoading(true);
    try {
      const [detail, items] = await Promise.all([getTask(taskId), listComments(taskId)]);
      setTask(detail);
      setComments(items);
      return detail;
    } finally {
      setCommentsLoading(false);
    }
  }, [taskId]);

  const handleSubmitComment = async (content: string, files: File[]): Promise<string | null> => {
    try {
      await createComment(taskId, content, files);
      const before = task?.status;
      const detail = await refresh();
      setActionError('');
      if (files.length && before !== 'CHO_DUYET' && detail.status === 'CHO_DUYET') {
        setNotice(t('work.comments.sentWithFilesChangedNotice', { count: String(files.length) }));
      } else if (files.length) {
        setNotice(t('work.comments.sentWithFilesNotice', { count: String(files.length) }));
      } else {
        setNotice(t('work.comments.sentNotice'));
      }
      return null;
    } catch (cause) {
      // Trạng thái có thể đã đổi (ví dụ vừa quá hạn): tải lại để khóa đúng ô nhập.
      refresh().catch(() => undefined);
      return toMessage(cause);
    }
  };

  const handleConfirm = async () => {
    if (!pending) return;
    setPendingBusy(true);
    try {
      if (pending.type === 'approve') {
        await approveTask(taskId);
        setNotice(t('work.taskDetail.approvedNotice'));
      } else if (pending.type === 'unapprove') {
        await unapproveTask(taskId);
        setNotice(t('work.taskDetail.unapprovedNotice'));
      } else {
        await deleteEvidence(taskId, pending.file.id);
        setNotice(t('work.taskDetail.deletedFileNotice', { fileName: pending.file.fileName }));
      }
      setActionError('');
    } catch (cause) {
      setActionError(toMessage(cause));
    } finally {
      await refresh().catch(() => undefined);
      setPendingBusy(false);
      setPending(null);
    }
  };

  if (!loaded) {
    return (
      <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <i className="fa-solid fa-circle-notch fa-spin" /> {t('work.taskDetail.loadingDetail')}
      </div>
    );
  }

  if (!task) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <WorkAlert variant="danger" title={t('work.taskDetail.loadError')} message={loadError} />
        <div>
          <button
            type="button"
            onClick={onBack}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <i className="fa-solid fa-arrow-left" />
            {t('work.common.backToList')}
          </button>
        </div>
      </div>
    );
  }

  const statusInfo = statusNotice(task);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <button
          type="button"
          onClick={onBack}
          aria-label={t('work.common.backToList')}
          title={t('work.common.backToList')}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            color: 'var(--text-main)',
            cursor: 'pointer',
          }}
        >
          <i className="fa-solid fa-arrow-left" />
        </button>
        <h1 style={{ fontSize: isMobile ? '1.05rem' : '1.25rem', fontWeight: 800, color: 'var(--text-main)' }}>{t('work.taskDetail.pageTitle')}</h1>
        <TaskStatusBadge status={task.status} label={task.statusLabel} />
        {!task.isPublic && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 10px',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--color-purple-border)',
              color: 'var(--color-purple)',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}
          >
            <i className="fa-solid fa-eye-slash" />
            {t('work.common.hidden')}
          </span>
        )}
      </div>

      <WorkAlert variant={statusInfo.variant} message={statusInfo.message} />
      {notice && <WorkAlert variant="success" message={notice} onClose={() => setNotice('')} />}
      {actionError && <WorkAlert variant="danger" message={actionError} onClose={() => setActionError('')} />}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'flex-start' }}>
        <div style={{ flex: '1 1 260px', minWidth: 0 }}>
          <TaskPeopleCard task={task} currentUserId={currentUserId} />
        </div>

        <div style={{ flex: '1000 1 560px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <TaskInfoCard task={task} onError={setActionError} />
          <TaskCommentPanel
            task={task}
            comments={comments}
            loading={commentsLoading}
            onBack={onBack}
            onSubmit={handleSubmitComment}
            onDeleteFile={(file) => setPending({ type: 'deleteFile', file })}
            onError={setActionError}
          />
        </div>
      </div>

      <TaskApprovalBar
        task={task}
        busy={pendingBusy}
        onApprove={() => setPending({ type: 'approve' })}
        onUnapprove={() => setPending({ type: 'unapprove' })}
      />

      <ConfirmDialog
        open={pending !== null}
        loading={pendingBusy}
        danger={pending?.type === 'deleteFile'}
        title={
          pending?.type === 'approve'
            ? t('work.taskDetail.confirmApproveTitle')
            : pending?.type === 'unapprove'
              ? t('work.taskDetail.confirmUnapproveTitle')
              : t('work.taskDetail.confirmDeleteFileTitle')
        }
        confirmLabel={
          pending?.type === 'approve'
            ? t('work.taskDetail.confirmApproveLabel')
            : pending?.type === 'unapprove'
              ? t('work.taskDetail.confirmUnapproveLabel')
              : t('work.taskDetail.confirmDeleteFileLabel')
        }
        message={
          pending?.type === 'approve'
            ? t('work.taskDetail.confirmApproveMessage')
            : pending?.type === 'unapprove'
              ? t('work.taskDetail.confirmUnapproveMessage')
              : pending?.type === 'deleteFile'
                ? t('work.taskDetail.confirmDeleteFileMessage', { fileName: pending.file.fileName })
                : ''
        }
        onCancel={() => setPending(null)}
        onConfirm={handleConfirm}
      />
    </div>
  );
}
