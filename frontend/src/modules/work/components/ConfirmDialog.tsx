import React from 'react';
import { useTranslation } from '@i18n/translate';
import WorkModal from './WorkModal';

/** Hộp thoại xác nhận trước các thao tác khó hoàn tác: xóa công việc, xóa file, hủy duyệt. */

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** true cho thao tác xóa: nút xác nhận chuyển sang màu đỏ. */
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  danger = false,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  const resolvedConfirmLabel = confirmLabel || t('work.common.confirm');
  const resolvedCancelLabel = cancelLabel || t('work.common.cancel');
  return (
    <WorkModal
      open={open}
      title={title}
      onClose={onCancel}
      width="sm"
      busy={loading}
      closeOnOverlayClick
      footer={
        <>
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: '9px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontWeight: 600,
              fontSize: '0.86rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {resolvedCancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            style={{
              padding: '9px 18px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: danger ? 'var(--color-danger)' : 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: '0.86rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {loading && <i className="fa-solid fa-circle-notch fa-spin" />}
            {loading ? t('work.common.processing') : resolvedConfirmLabel}
          </button>
        </>
      }
    >
      <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{message}</div>
    </WorkModal>
  );
}
