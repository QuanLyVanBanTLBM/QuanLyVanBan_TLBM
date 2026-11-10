import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { toMessage } from '../api/client';
import { downloadAttachment } from '../api/taskActions';
import { Attachment } from '../types/task';
import { fileIconClass, formatFileSize } from './FilePicker';

/**
 * Danh sách file, dùng cho cả file đính kèm lúc giao việc và file kết quả trong ý kiến.
 * Nút xóa chỉ hiện khi truyền onDelete và file có cờ canDelete từ API.
 */

interface TaskAttachmentListProps {
  files: Attachment[];
  emptyText?: string;
  onDelete?: (file: Attachment) => void;
  onError?: (message: string) => void;
  compact?: boolean;
}

export default function TaskAttachmentList({
  files,
  emptyText,
  onDelete,
  onError,
  compact = false,
}: TaskAttachmentListProps) {
  const { t } = useTranslation();
  const resolvedEmptyText = emptyText || t('work.attachments.empty');
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  if (!files.length) {
    return <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>{resolvedEmptyText}</div>;
  }

  const handleDownload = async (file: Attachment) => {
    setDownloadingId(file.id);
    try {
      await downloadAttachment(file);
    } catch (cause) {
      onError?.(toMessage(cause));
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {files.map((file) => (
        <li key={file.id}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: compact ? '6px 10px' : '8px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface-hover)',
            }}
          >
            <i className={fileIconClass(file.fileName)} style={{ color: 'var(--color-primary)' }} />
            <button
              type="button"
              onClick={() => handleDownload(file)}
              title={t('work.attachments.download')}
              style={{
                flex: 1,
                minWidth: 0,
                padding: 0,
                border: 'none',
                background: 'transparent',
                color: 'var(--color-primary)',
                fontSize: '0.84rem',
                fontWeight: 600,
                fontFamily: 'inherit',
                textAlign: 'left',
                cursor: 'pointer',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {file.fileName}
            </button>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              {formatFileSize(file.size)}
            </span>
            <button
              type="button"
              onClick={() => handleDownload(file)}
              disabled={downloadingId === file.id}
              aria-label={t('work.attachments.downloadLabel', { fileName: file.fileName })}
              title={t('work.attachments.download')}
              style={{
                border: 'none',
                background: 'transparent',
                color: 'var(--text-secondary)',
                cursor: downloadingId === file.id ? 'wait' : 'pointer',
                padding: '2px 4px',
              }}
            >
              <i className={downloadingId === file.id ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-download'} />
            </button>
            {onDelete && file.canDelete && (
              <button
                type="button"
                onClick={() => onDelete(file)}
                aria-label={t('work.attachments.downloadLabel', { fileName: file.fileName })}
                title={t('work.attachments.deleteFile')}
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--color-danger)',
                  cursor: 'pointer',
                  padding: '2px 4px',
                }}
              >
                <i className="fa-solid fa-trash" />
              </button>
            )}
          </div>
          {onDelete && !file.canDelete && file.deleteBlockedReason && (
            <div style={{ marginTop: '4px', fontSize: '0.76rem', color: 'var(--color-warning-text)', lineHeight: 1.5 }}>
              <i className="fa-solid fa-circle-info" /> {file.deleteBlockedReason}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
