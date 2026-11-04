import React from 'react';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '../hooks/useIsMobile';
import { TaskListItem } from '../types/task';
import { isoToDisplay } from './DateInput';
import { employeeMeta } from './EmployeeSelect';
import TaskActionCell from './TaskActionCell';
import TaskAssigneeCell from './TaskAssigneeCell';
import TaskStatusBadge from './TaskStatusBadge';

/**
 * Danh sách công việc.
 * - Desktop (≥ 768px): bảng 9 cột, có thể cuộn ngang nếu màn quá hẹp.
 * - Mobile (< 768px): mỗi công việc là một card xếp dọc, không cuộn ngang.
 */

interface TaskTableProps {
  tasks: TaskListItem[];
  /** Số thứ tự của dòng đầu tiên, để cột TT đánh số liên tục qua các trang. */
  startIndex: number;
  busy?: boolean;
  onOpenTask: (task: TaskListItem) => void;
  onEdit: (task: TaskListItem) => void;
  onDelete: (task: TaskListItem) => void;
  onApprove: (task: TaskListItem) => void;
  onUnapprove: (task: TaskListItem) => void;
}

const COLUMN_KEYS = [
  { key: 'work.table.colIndex', width: '40px' },
  { key: 'work.table.colTitle', width: '188px' },
  { key: 'work.table.colCreator', width: '124px' },
  { key: 'work.table.colRequirement', width: '178px' },
  { key: 'work.table.colAssignees', width: '150px' },
  { key: 'work.table.colCreatedDate', width: '86px' },
  { key: 'work.table.colDueDate', width: '86px' },
  { key: 'work.table.colStatus', width: '116px' },
  { key: 'work.table.colActions', width: '120px' },
] as const;

const cellStyle: React.CSSProperties = {
  padding: '10px 8px',
  borderBottom: '1px solid var(--border-subtle)',
  verticalAlign: 'top',
  fontSize: '0.85rem',
  color: 'var(--text-main)',
};

const clampStyle: React.CSSProperties = {
  display: '-webkit-box',
  WebkitLineClamp: 3,
  WebkitBoxOrient: 'vertical',
  overflow: 'hidden',
  whiteSpace: 'pre-line',
};

const metaRow: React.CSSProperties = {
  display: 'flex',
  gap: '4px',
  fontSize: '0.78rem',
  color: 'var(--text-secondary)',
  lineHeight: 1.45,
};

export default function TaskTable(props: TaskTableProps) {
  const isMobile = useIsMobile();
  if (isMobile) {
    return <TaskCardList {...props} />;
  }
  return <TaskGridTable {...props} />;
}

function TaskGridTable({
  tasks,
  startIndex,
  busy = false,
  onOpenTask,
  onEdit,
  onDelete,
  onApprove,
  onUnapprove,
}: TaskTableProps) {
  const { t } = useTranslation();
  return (
    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
      <table style={{ width: '100%', minWidth: '960px', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <colgroup>
          {COLUMN_KEYS.map((column) => (
            <col key={column.key} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead>
          <tr style={{ background: 'var(--bg-surface-hover)' }}>
            {COLUMN_KEYS.map((column) => {
              const label = t(column.key);
              return (
                <th
                  key={column.key}
                  scope="col"
                  style={{
                    padding: '10px 8px',
                    textAlign: column.key === 'work.table.colIndex' ? 'center' : 'left',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody style={{ opacity: busy ? 0.55 : 1, transition: 'opacity var(--transition-fast)' }}>
          {tasks.map((task, index) => {
            const hidden = !task.isPublic;
            return (
              <tr
                key={task.id}
                style={{ background: hidden ? 'var(--color-purple-subtle)' : 'var(--bg-surface)' }}
              >
                <td style={{ ...cellStyle, textAlign: 'center', color: 'var(--text-secondary)' }}>
                  {startIndex + index}
                </td>

                <td style={cellStyle}>
                  <button
                    type="button"
                    onClick={() => onOpenTask(task)}
                    title={t('work.table.viewDetail')}
                    style={{
                      ...clampStyle,
                      padding: 0,
                      border: 'none',
                      background: 'transparent',
                      color: 'var(--color-primary)',
                      fontWeight: 600,
                      fontSize: '0.86rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      lineHeight: 1.5,
                    }}
                  >
                    {task.title}
                  </button>
                  {hidden && (
                    <span
                      title={t('work.common.hiddenTooltip')}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        marginTop: '6px',
                        padding: '1px 8px',
                        borderRadius: 'var(--radius-full)',
                        border: '1px solid var(--color-purple-border)',
                        color: 'var(--color-purple)',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                      }}
                    >
                      <i className="fa-solid fa-eye-slash" />
                      {t('work.common.hidden')}
                    </span>
                  )}
                </td>

                <td style={cellStyle}>
                  <div style={{ fontWeight: 600 }}>{task.creator.fullName}</div>
                  {employeeMeta(task.creator) && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {employeeMeta(task.creator)}
                    </div>
                  )}
                </td>

                <td style={cellStyle}>
                  <div style={{ ...clampStyle, color: 'var(--text-secondary)' }} title={task.requirement}>
                    {task.requirement}
                  </div>
                </td>

                <td style={cellStyle}>
                  <TaskAssigneeCell host={task.host} participants={task.participants} />
                </td>

                <td style={{ ...cellStyle, whiteSpace: 'nowrap' }}>{isoToDisplay(task.createdDate)}</td>
                <td style={{ ...cellStyle, whiteSpace: 'nowrap' }}>{isoToDisplay(task.dueDate)}</td>

                <td style={cellStyle}>
                  <TaskStatusBadge status={task.status} label={task.statusLabel} size="sm" />
                </td>

                <td style={cellStyle}>
                  <TaskActionCell
                    task={task}
                    disabled={busy}
                    onEdit={onEdit}
                    onDelete={onDelete}
                    onApprove={onApprove}
                    onUnapprove={onUnapprove}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TaskCardList({
  tasks,
  startIndex,
  busy = false,
  onOpenTask,
  onEdit,
  onDelete,
  onApprove,
  onUnapprove,
}: TaskTableProps) {
  const { t } = useTranslation();
  return (
    <ul
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        margin: 0,
        padding: 0,
        listStyle: 'none',
        opacity: busy ? 0.55 : 1,
        transition: 'opacity var(--transition-fast)',
      }}
    >
      {tasks.map((task, index) => {
        const hidden = !task.isPublic;
        return (
          <li
            key={task.id}
            style={{
              background: hidden ? 'var(--color-purple-subtle)' : 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--bg-surface-hover)',
                  flexShrink: 0,
                }}
              >
                #{startIndex + index}
              </span>
              <TaskStatusBadge status={task.status} label={task.statusLabel} size="sm" />
            </div>

            <button
              type="button"
              onClick={() => onOpenTask(task)}
              title={t('work.table.viewDetail')}
              style={{
                padding: 0,
                border: 'none',
                background: 'transparent',
                color: 'var(--color-primary)',
                fontWeight: 700,
                fontSize: '0.95rem',
                textAlign: 'left',
                cursor: 'pointer',
                fontFamily: 'inherit',
                lineHeight: 1.4,
                whiteSpace: 'pre-line',
              }}
            >
              {task.title}
            </button>

            {hidden && (
              <span
                title={t('work.common.hiddenTooltip')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '1px 8px',
                  borderRadius: 'var(--radius-full)',
                  border: '1px solid var(--color-purple-border)',
                  color: 'var(--color-purple)',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  alignSelf: 'flex-start',
                }}
              >
                <i className="fa-solid fa-eye-slash" />
                {t('work.common.hidden')}
              </span>
            )}

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto 1fr',
                columnGap: '8px',
                rowGap: '6px',
                fontSize: '0.82rem',
                color: 'var(--text-main)',
              }}
            >
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{t('work.table.cardCreator')}</span>
              <span>
                <span style={{ fontWeight: 600 }}>{task.creator.fullName}</span>
                {employeeMeta(task.creator) && (
                  <span style={{ color: 'var(--text-secondary)' }}> · {employeeMeta(task.creator)}</span>
                )}
              </span>

              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{t('work.table.cardAssignees')}</span>
              <span>
                <TaskAssigneeCell host={task.host} participants={task.participants} />
              </span>

              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{t('work.table.cardCreatedDate')}</span>
              <span>{isoToDisplay(task.createdDate)}</span>

              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{t('work.table.cardDueDate')}</span>
              <span>{isoToDisplay(task.dueDate)}</span>
            </div>

            {task.requirement && (
              <div style={metaRow}>
                <span style={{ fontWeight: 600 }}>{t('work.table.cardRequirement')}</span>
                <span style={{ ...clampStyle, color: 'var(--text-secondary)' }}>{task.requirement}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
              <TaskActionCell
                task={task}
                disabled={busy}
                onEdit={onEdit}
                onDelete={onDelete}
                onApprove={onApprove}
                onUnapprove={onUnapprove}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
