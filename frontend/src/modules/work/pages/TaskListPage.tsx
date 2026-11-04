import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { toMessage } from '../api/client';
import { unapproveTask } from '../api/taskActions';
import { deleteTask, listTasks } from '../api/tasks';
import ConfirmDialog from '../components/ConfirmDialog';
import TaskFilterBar, { FilterDraft } from '../components/TaskFilterBar';
import TaskFormModal from '../components/TaskFormModal';
import TaskPagination from '../components/TaskPagination';
import TaskTable from '../components/TaskTable';
import WorkAlert from '../components/WorkAlert';
import { useIsMobile } from '../hooks/useIsMobile';
import { Paginated, TaskListItem } from '../types/task';

/**
 * Danh sách nội dung công việc.
 *
 * Bộ lọc và trang hiện tại được lưu vào sessionStorage: khi rê chuột qua menu bên trái,
 * layout tạm thay trang khác làm trang này bị gỡ khỏi màn hình, quay lại vẫn giữ nguyên chỗ đang xem.
 */

interface ListState {
  filters: FilterDraft;
  page: number;
  pageSize: number;
}

const STORAGE_KEY = 'work.listState';
const EMPTY_FILTERS: FilterDraft = { search: '', status: '', createdFrom: '', createdTo: '' };
const DEFAULT_STATE: ListState = { filters: EMPTY_FILTERS, page: 1, pageSize: 10 };

function readState(): ListState {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw) as Partial<ListState>;
    return {
      filters: { ...EMPTY_FILTERS, ...(parsed.filters || {}) },
      page: Number(parsed.page) > 0 ? Number(parsed.page) : 1,
      pageSize: [10, 20, 50].includes(Number(parsed.pageSize)) ? Number(parsed.pageSize) : 10,
    };
  } catch {
    return DEFAULT_STATE;
  }
}

type PendingAction = { type: 'delete' | 'unapprove'; task: TaskListItem } | null;

interface TaskListPageProps {
  onOpenTask: (taskId: number) => void;
}

export default function TaskListPage({ onOpenTask }: TaskListPageProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [state, setState] = useState<ListState>(readState);
  const [data, setData] = useState<Paginated<TaskListItem> | null>(null);
  const [loadedKey, setLoadedKey] = useState('');
  const [loadError, setLoadError] = useState<{ key: string; message: string } | null>(null);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  // Mỗi lần bộ lọc, trang hoặc yêu cầu tải lại thay đổi là một request mới; chưa nhận kết quả thì đang tải.
  const requestKey = `${JSON.stringify(state)}#${reloadToken}`;
  const loading = loadedKey !== requestKey;
  const error = actionError || (loadError && loadError.key === requestKey ? loadError.message : '');
  const [form, setForm] = useState<{ open: boolean; taskId: number | null }>({ open: false, taskId: null });
  const [pending, setPending] = useState<PendingAction>(null);
  const [pendingBusy, setPendingBusy] = useState(false);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Không lưu được thì chỉ mất vị trí khi quay lại, không ảnh hưởng dữ liệu.
    }
  }, [state]);

  useEffect(() => {
    const controller = new AbortController();

    listTasks({ ...state.filters, page: state.page, pageSize: state.pageSize }, controller.signal)
      .then((result) => {
        // Trang đang xem không còn (ví dụ vừa xóa dòng cuối) thì lùi về trang cuối cùng còn dữ liệu.
        if (result.count > 0 && state.page > result.totalPages) {
          setState((previous) => ({ ...previous, page: result.totalPages }));
          return;
        }
        setData(result);
        setLoadedKey(requestKey);
      })
      .catch((cause) => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return;
        const message = toMessage(cause);
        // Trang không tồn tại (lưu từ lần trước) thì quay về trang 1 thay vì báo lỗi.
        if (state.page > 1 && message.includes('không tồn tại')) {
          setState((previous) => ({ ...previous, page: 1 }));
          return;
        }
        setLoadError({ key: requestKey, message });
        setLoadedKey(requestKey);
      });

    return () => controller.abort();
    // requestKey đã gồm state và reloadToken.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(''), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);

  const handleSearch = (filters: FilterDraft) => {
    setActionError('');
    setState((previous) => ({ ...previous, filters, page: 1 }));
    reload();
  };

  const handleConfirm = async () => {
    if (!pending) return;
    setPendingBusy(true);
    try {
      if (pending.type === 'delete') {
        await deleteTask(pending.task.id);
        setNotice(t('work.taskList.deletedNotice', { title: pending.task.title }));
      } else {
        await unapproveTask(pending.task.id);
        setNotice(t('work.taskList.unapprovedNotice', { title: pending.task.title }));
      }
      setActionError('');
      reload();
    } catch (cause) {
      setActionError(toMessage(cause));
      reload();
    } finally {
      setPendingBusy(false);
      setPending(null);
    }
  };

  const hasFilter = Boolean(
    state.filters.search || state.filters.status || state.filters.createdFrom || state.filters.createdTo,
  );
  const tasks = data ? data.results : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
          padding: isMobile ? '14px 16px' : '20px 24px',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div>
          <h1 style={{ fontSize: isMobile ? '1.15rem' : '1.3rem', fontWeight: 800, color: 'var(--text-main)' }}>
            {t('work.taskList.title')}
          </h1>
          <p style={{ marginTop: '4px', fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
            {t('work.taskList.subtitle')}
          </p>
        </div>

        <TaskFilterBar
          value={state.filters}
          busy={loading}
          onSearch={handleSearch}
          onCreate={() => setForm({ open: true, taskId: null })}
        />
      </div>

      {notice && <WorkAlert variant="success" message={notice} onClose={() => setNotice('')} />}
      {error && (
        <WorkAlert
          variant="danger"
          message={error}
          onClose={() => {
            setActionError('');
            setLoadError(null);
          }}
        />
      )}

      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
          padding: isMobile ? '12px' : '16px',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        {loading && !data ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <i className="fa-solid fa-circle-notch fa-spin" /> {t('work.taskList.loadingList')}
          </div>
        ) : !data && error ? (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ fontWeight: 600, color: 'var(--text-main)' }}>{t('work.taskList.loadError')}</p>
            <button
              type="button"
              onClick={reload}
              style={{
                marginTop: '10px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-surface)',
                color: 'var(--text-main)',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <i className="fa-solid fa-rotate-right" /> {t('work.common.retry')}
            </button>
          </div>
        ) : tasks.length === 0 && !loading ? (
          <div style={{ padding: '40px 16px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <i className="fa-regular fa-folder-open" style={{ fontSize: '1.8rem', color: 'var(--text-muted)' }} />
            <p style={{ marginTop: '10px', fontWeight: 600, color: 'var(--text-main)' }}>
              {hasFilter ? t('work.taskList.emptyFiltered') : t('work.taskList.emptyAll')}
            </p>
            <p style={{ marginTop: '4px', fontSize: '0.84rem' }}>
              {hasFilter
                ? t('work.taskList.emptyFilteredHint')
                : t('work.taskList.emptyAllHint')}
            </p>
          </div>
        ) : (
          <>
            <TaskTable
              tasks={tasks}
              startIndex={(state.page - 1) * state.pageSize + 1}
              busy={loading}
              onOpenTask={(task) => onOpenTask(task.id)}
              onEdit={(task) => setForm({ open: true, taskId: task.id })}
              onDelete={(task) => setPending({ type: 'delete', task })}
              onApprove={(task) => onOpenTask(task.id)}
              onUnapprove={(task) => setPending({ type: 'unapprove', task })}
            />
            {data && (
              <TaskPagination
                page={state.page}
                pageSize={state.pageSize}
                totalPages={data.totalPages}
                count={data.count}
                disabled={loading}
                onPageChange={(page) => setState((previous) => ({ ...previous, page }))}
                onPageSizeChange={(pageSize) => setState((previous) => ({ ...previous, pageSize, page: 1 }))}
              />
            )}
          </>
        )}
      </div>

      <TaskFormModal
        open={form.open}
        taskId={form.taskId}
        onClose={() => setForm({ open: false, taskId: null })}
        onSaved={(task, mode) => {
          setForm({ open: false, taskId: null });
          setActionError('');
          if (mode === 'create') {
            setNotice(t('work.taskList.createdNotice', { title: task.title }));
            setState((previous) => ({ ...previous, page: 1 }));
          } else {
            setNotice(t('work.taskList.updatedNotice', { title: task.title }));
          }
          reload();
        }}
      />

      <ConfirmDialog
        open={pending !== null}
        danger={pending?.type === 'delete'}
        loading={pendingBusy}
        title={pending?.type === 'delete' ? t('work.taskList.confirmDeleteTitle') : t('work.taskList.confirmUnapproveTitle')}
        confirmLabel={pending?.type === 'delete' ? t('work.taskList.confirmDeleteLabel') : t('work.taskList.confirmUnapproveLabel')}
        message={
          pending?.type === 'delete'
            ? t('work.taskList.confirmDeleteMessage', { title: pending.task.title })
            : t('work.taskList.confirmUnapproveMessage', { title: pending?.task.title ?? '' })
        }
        onCancel={() => setPending(null)}
        onConfirm={handleConfirm}
      />
    </div>
  );
}
