import React, { useId } from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

export type AlertVariant = 'info' | 'error' | 'warning' | 'success';

interface Props {
  open: boolean;
  title?: string;
  message?: string;
  details?: string[];
  variant?: AlertVariant;
  onClose: () => void;
}

const VARIANT_STYLES: Record<
  AlertVariant,
  { icon: string; iconBox: string; badge: string }
> = {
  info: {
    icon: 'fa-solid fa-circle-info',
    iconBox: 'bg-primary-subtle text-primary',
    badge: 'bg-primary-subtle text-primary',
  },
  error: {
    icon: 'fa-solid fa-circle-exclamation',
    iconBox: 'bg-danger-subtle text-danger',
    badge: 'bg-danger-subtle text-danger',
  },
  warning: {
    icon: 'fa-solid fa-triangle-exclamation',
    iconBox: 'bg-warning-subtle text-warning-text',
    badge: 'bg-warning-subtle text-warning-text',
  },
  success: {
    icon: 'fa-solid fa-circle-check',
    iconBox: 'bg-success-subtle text-success',
    badge: 'bg-success-subtle text-success',
  },
};

export default function AlertModal({
  open,
  title = 'Thông báo hệ thống',
  message = '',
  details = [],
  variant = 'info',
  onClose,
}: Props) {
  const titleId = useId();
  if (!open) return null;

  const hasDetails = details.length > 0;
  const styles = VARIANT_STYLES[variant];

  const content = (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div
        className={`relative bg-surface border border-border-subtle rounded-2xl shadow-2xl w-full ${
          hasDetails ? 'max-w-[540px]' : 'max-w-[420px]'
        } max-h-[88vh] supports-[max-height:88dvh]:max-h-[88dvh] flex flex-col p-4 sm:p-6 z-10 animate-in zoom-in-95 duration-150`}
      >
        <div className="flex items-center gap-3 sm:gap-3.5 mb-3 sm:mb-3.5 shrink-0 min-w-0">
          <div
            className={`w-10 h-10 sm:w-11 sm:h-11 rounded-xl ${styles.iconBox} flex items-center justify-center text-base sm:text-lg shrink-0 shadow-2xs`}
          >
            <i className={styles.icon} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 id={titleId} className="text-sm sm:text-base font-bold text-main m-0 break-words">
              {title}
            </h3>
            <span className="text-[11px] text-muted block truncate">Hệ thống Quản lý Văn bản TLBM</span>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto mb-4 sm:mb-5 space-y-2.5 pr-0.5">
          {message && (
            <div className="text-xs sm:text-[13px] text-secondary leading-relaxed bg-surface-subtle border border-border-subtle rounded-xl p-3 sm:p-3.5 whitespace-pre-line break-words">
              {message}
            </div>
          )}

          {hasDetails && (
            <ul className="space-y-2 m-0 p-0 list-none" aria-label="Chi tiết thông báo">
              {details.map((item, idx) => (
                <li
                  key={idx}
                  className="text-xs leading-relaxed text-main bg-surface-subtle border border-border-subtle rounded-xl px-3 py-2.5 flex items-start gap-2.5 min-w-0"
                >
                  <span
                    className={`shrink-0 inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-md ${styles.badge} font-semibold text-[11px] tabular-nums mt-0.5`}
                  >
                    {idx + 1}
                  </span>
                  <span className="min-w-0 flex-1 break-words whitespace-pre-line">{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex justify-end pt-3 border-t border-border-subtle shrink-0">
          <Button variant="primary" size="sm" onClick={onClose} className="w-full sm:w-auto">
            Đã hiểu
          </Button>
        </div>
      </div>
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(content, window.document.body) : content;
}
