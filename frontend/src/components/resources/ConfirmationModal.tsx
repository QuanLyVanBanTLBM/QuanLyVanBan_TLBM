import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@components/common/Button';

export interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  subMessage?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'primary';
  confirmIcon?: string;
  headerIcon?: string;
  isLoading?: boolean;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  subMessage,
  confirmText = 'Xác nhận',
  cancelText = 'Hủy bỏ',
  variant = 'warning',
  confirmIcon,
  headerIcon,
  isLoading = false,
}) => {
  // Đóng khi nhấn phím Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isLoading, onClose]);

  if (!isOpen || typeof document === 'undefined') return null;

  const isDanger = variant === 'danger';
  const isWarning = variant === 'warning';

  const iconBg = isDanger
    ? 'bg-danger-subtle text-danger border-danger/20'
    : isWarning
    ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    : 'bg-primary-subtle text-primary border-primary/20';

  const modalHeaderIcon =
    headerIcon ||
    (isDanger
      ? 'fa-trash-can'
      : isWarning
      ? 'fa-triangle-exclamation'
      : 'fa-circle-info');

  const modalButtonIcon =
    confirmIcon !== undefined
      ? confirmIcon
      : isDanger
      ? 'fa-trash'
      : isWarning
      ? 'fa-triangle-exclamation'
      : undefined;

  return createPortal(
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <div
        className="w-full max-w-md bg-surface rounded-2xl border border-border-subtle shadow-2xl p-6 space-y-4 animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3.5">
          <div
            className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0 border ${iconBg}`}
          >
            <i className={`fa-solid ${modalHeaderIcon}`} />
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <h3
              id="confirm-modal-title"
              className="text-base font-bold text-main tracking-tight leading-snug"
            >
              {title}
            </h3>
            <p className="text-xs text-secondary mt-1.5 leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        {subMessage && (
          <div className="p-3 bg-surface-elevated rounded-xl border border-border-subtle text-xs text-secondary leading-relaxed">
            {subMessage}
          </div>
        )}

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border-subtle">
          <Button
            variant="secondary"
            size="md"
            disabled={isLoading}
            onClick={onClose}
            className="rounded-xl px-4 text-xs font-semibold"
          >
            {cancelText}
          </Button>
          <Button
            variant={isDanger ? 'danger' : 'primary'}
            size="md"
            icon={modalButtonIcon}
            isLoading={isLoading}
            onClick={onConfirm}
            className={`rounded-xl px-4 text-xs font-bold shadow-xs ${
              isWarning && !isDanger
                ? '!bg-amber-600 hover:!bg-amber-700 text-white !border-amber-600'
                : ''
            }`}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
};
