import React from 'react';
import { Button } from '@components/common';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  isLoading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  isLoading = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  React.useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoading) onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, isLoading, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4" role="presentation">
      <div
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
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" disabled={isLoading} onClick={onCancel}>Hủy</Button>
          <Button type="button" variant="danger" isLoading={isLoading} onClick={onConfirm}>Xóa</Button>
        </div>
      </div>
    </div>
  );
}
