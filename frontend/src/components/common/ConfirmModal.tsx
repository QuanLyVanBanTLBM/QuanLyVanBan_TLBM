import React from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

interface Props {
  open: boolean;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open,
  title = 'Xác nhận hành động',
  message = '',
  confirmText = 'Xác nhận',
  cancelText = 'Hủy bỏ',
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null;

  const content = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-150">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onCancel}
      />

      {/* Modal Dialog */}
      <div className="relative bg-surface border border-border-subtle rounded-2xl shadow-2xl w-[440px] max-w-full p-6 z-10 animate-in zoom-in-95 duration-150">
        <div className="flex items-center gap-3.5 mb-3.5">
          <div className="w-11 h-11 rounded-xl bg-danger-subtle text-danger flex items-center justify-center text-lg shrink-0 shadow-2xs">
            <i className="fa-solid fa-triangle-exclamation" />
          </div>
          <div>
            <h3 className="text-base font-bold text-main m-0">{title}</h3>
            <span className="text-[11px] text-muted">Hành động này cần được xác thực kỹ lưỡng</span>
          </div>
        </div>

        <div className="text-xs text-secondary leading-relaxed mb-5 bg-surface-subtle border border-border-subtle rounded-xl p-3.5">
          {message}
        </div>

        <div className="flex justify-end gap-2.5 pt-3 border-t border-border-subtle">
          <Button variant="secondary" size="sm" onClick={onCancel}>
            {cancelText}
          </Button>
          <Button variant="danger" size="sm" icon="fa-trash-can" onClick={onConfirm}>
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(content, window.document.body) : content;
}
