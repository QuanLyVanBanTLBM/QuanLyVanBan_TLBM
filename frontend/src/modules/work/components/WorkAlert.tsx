import React from 'react';
import { useTranslation } from '@i18n/translate';

/** Khung thông báo dùng chung: báo lỗi, cảnh báo, thành công hoặc thông tin hướng dẫn. */

export type WorkAlertVariant = 'success' | 'warning' | 'danger' | 'info';

const VARIANT_STYLES: Record<WorkAlertVariant, { icon: string; color: string; background: string; border: string }> = {
  success: {
    icon: 'fa-solid fa-circle-check',
    color: 'var(--color-success)',
    background: 'var(--color-success-subtle)',
    border: 'var(--color-success-border)',
  },
  warning: {
    icon: 'fa-solid fa-triangle-exclamation',
    color: 'var(--color-warning-text)',
    background: 'var(--color-warning-subtle)',
    border: 'var(--color-warning-border)',
  },
  danger: {
    icon: 'fa-solid fa-circle-exclamation',
    color: 'var(--color-danger)',
    background: 'var(--color-danger-subtle)',
    border: 'var(--color-danger-border)',
  },
  info: {
    icon: 'fa-solid fa-circle-info',
    color: 'var(--color-info)',
    background: 'var(--color-info-subtle)',
    border: 'var(--color-info-border)',
  },
};

interface WorkAlertProps {
  variant?: WorkAlertVariant;
  title?: string;
  /** Nội dung thông báo; nên nêu cả lý do và cách khắc phục. */
  message?: React.ReactNode;
  children?: React.ReactNode;
  onClose?: () => void;
}

export default function WorkAlert({ variant = 'info', title, message, children, onClose }: WorkAlertProps) {
  const { t } = useTranslation();
  const style = VARIANT_STYLES[variant];

  return (
    <div
      role={variant === 'danger' ? 'alert' : 'status'}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '12px 14px',
        borderRadius: 'var(--radius-md)',
        background: style.background,
        border: `1px solid ${style.border}`,
        color: 'var(--text-main)',
      }}
    >
      <i className={style.icon} style={{ color: style.color, marginTop: '2px', fontSize: '1rem' }} />
      <div style={{ flex: 1, minWidth: 0, fontSize: '0.88rem', lineHeight: 1.6 }}>
        {title && <div style={{ fontWeight: 700, marginBottom: '2px', color: style.color }}>{title}</div>}
        {message}
        {children}
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label={t('work.common.closeNotification')}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '2px 4px',
            fontSize: '0.9rem',
            lineHeight: 1,
          }}
        >
          <i className="fa-solid fa-xmark" />
        </button>
      )}
    </div>
  );
}
