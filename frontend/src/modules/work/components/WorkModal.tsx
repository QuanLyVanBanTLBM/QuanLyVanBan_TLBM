import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '../hooks/useIsMobile';

/**
 * Khung cửa sổ bật lên dùng chung cho module Công việc.
 *
 * Modal được đưa thẳng ra document.body và có z-index cao hơn thanh menu bên trái (1200)
 * lẫn lớp phủ menu trên điện thoại (10001). Nếu để thấp hơn, khi rê chuột qua mép trái
 * màn hình thì menu trượt ra, trang bị đổi và form đang nhập dở sẽ mất hết.
 */

export const WORK_MODAL_Z_INDEX = 20000;

interface WorkModalProps {
  open: boolean;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  onClose: () => void;
  width?: 'sm' | 'md' | 'lg';
  /** Bấm ra ngoài để đóng. Mặc định tắt để không mất dữ liệu đang nhập trong form. */
  closeOnOverlayClick?: boolean;
  /** Đang lưu thì khóa nút đóng để tránh bấm hai lần. */
  busy?: boolean;
}

const WIDTHS: Record<'sm' | 'md' | 'lg', string> = {
  sm: '440px',
  md: '680px',
  lg: '980px',
};

export default function WorkModal({
  open,
  title,
  subtitle,
  children,
  footer,
  onClose,
  width = 'md',
  closeOnOverlayClick = false,
  busy = false,
}: WorkModalProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) {
        onClose();
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, busy, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      role="presentation"
      onMouseDown={(event) => {
        if (closeOnOverlayClick && !busy && event.target === event.currentTarget) {
          onClose();
        }
      }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: WORK_MODAL_Z_INDEX,
        background: 'rgba(2, 6, 23, 0.6)',
        backdropFilter: 'var(--backdrop-blur)',
        display: 'flex',
        alignItems: isMobile ? 'stretch' : 'center',
        justifyContent: 'center',
        padding: isMobile ? '0' : '16px',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          width: '100%',
          maxWidth: isMobile ? '100%' : WIDTHS[width],
          maxHeight: isMobile ? '100vh' : 'calc(100vh - 32px)',
          height: isMobile ? '100vh' : 'auto',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-surface)',
          border: isMobile ? 'none' : '1px solid var(--border-subtle)',
          borderRadius: isMobile ? 0 : 'var(--radius-lg)',
          boxShadow: isMobile ? 'none' : 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
            padding: isMobile ? '14px 16px' : '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>{title}</h2>
            {subtitle && (
              <p style={{ marginTop: '4px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{subtitle}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            aria-label={t('work.common.close')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: busy ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              opacity: busy ? 0.5 : 1,
            }}
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </div>

        <div style={{ padding: isMobile ? '14px 16px' : '18px 20px', overflowY: 'auto', flex: 1 }}>{children}</div>

        {footer && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '10px',
              padding: isMobile ? '12px 16px' : '14px 20px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface-hover)',
              flexWrap: 'wrap',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
