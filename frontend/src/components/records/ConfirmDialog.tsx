import React from 'react';
import { Button } from '@components/common';
import { useTranslation } from '@i18n/translate';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  isLoading?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  isLoading = false,
  error,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  const dialogRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement;
    dialogRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
    return () => {
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, [open]);

  React.useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoading) onCancel();
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (!first) {
        event.preventDefault();
        dialogRef.current?.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, isLoading, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4" role="presentation">
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="w-full max-w-md animate-slide-in-bottom rounded-xl border border-border-subtle bg-surface p-5 shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
      >
        <div className="mb-4 flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-danger-subtle text-danger">
            <i className="fa-solid fa-triangle-exclamation" />
          </span>
          <div>
            <h2 id="confirm-dialog-title" className="m-0 text-base font-bold text-main">{title}</h2>
            <p className="mt-1 text-sm text-secondary">{message}</p>
          </div>
        </div>
        {error && <p className="mb-4 rounded-lg border border-danger-border bg-danger-subtle px-3 py-2 text-sm text-danger" role="alert">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={isLoading} onClick={onCancel}>
            {t('records.actions.cancel')}
          </Button>
          <Button type="button" variant="danger" isLoading={isLoading} onClick={onConfirm}>
            {t('records.actions.delete')}
          </Button>
        </div>
      </div>
    </div>
  );
}
