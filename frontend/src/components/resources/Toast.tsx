import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

export interface ToastNotification {
  id: number;
  message: string;
  type?: 'success' | 'danger' | 'warning' | 'info';
  title?: string;
  duration?: number;
}

export interface ToastProps {
  toast: ToastNotification | null;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!toast) return;
    const duration = toast.duration || 3200;
    const interval = 40;
    const startTime = Date.now();

    const timer = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remainingPercent = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remainingPercent);
      if (remainingPercent <= 0) {
        clearInterval(timer);
        onClose();
      }
    }, interval);

    return () => clearInterval(timer);
  }, [toast, onClose]);

  if (!toast) return null;
  if (typeof document === 'undefined') return null;

  const type = toast.type || 'success';
  const isDeleteAction =
    type === 'danger' &&
    ((toast.title && /xóa|delete/i.test(toast.title)) ||
      (toast.message && /đã xóa|xóa thành công|deleted/i.test(toast.message)));

  const config = {
    success: {
      icon: 'fa-circle-check',
      iconBox: 'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/25',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/30',
      progressBar: 'bg-emerald-500 dark:bg-emerald-400',
      defaultTitle: 'Thành công',
    },
    danger: {
      icon: isDeleteAction ? 'fa-trash-can' : 'fa-circle-exclamation',
      iconBox: 'bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-500/15 dark:text-rose-400 dark:border-rose-500/25',
      badge: 'bg-rose-50 text-rose-700 border-rose-200/80 dark:bg-rose-500/20 dark:text-rose-300 dark:border-rose-500/30',
      progressBar: 'bg-rose-500 dark:bg-rose-400',
      defaultTitle: isDeleteAction ? 'Đã xóa' : 'Lỗi thao tác',
    },
    warning: {
      icon: 'fa-triangle-exclamation',
      iconBox: 'bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/25',
      badge: 'bg-amber-50 text-amber-700 border-amber-200/80 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/30',
      progressBar: 'bg-amber-500 dark:bg-amber-400',
      defaultTitle: 'Cảnh báo',
    },
    info: {
      icon: 'fa-circle-info',
      iconBox: 'bg-sky-50 text-sky-600 border-sky-100 dark:bg-sky-500/15 dark:text-sky-400 dark:border-sky-500/25',
      badge: 'bg-sky-50 text-sky-700 border-sky-200/80 dark:bg-sky-500/20 dark:text-sky-300 dark:border-sky-500/30',
      progressBar: 'bg-sky-500 dark:bg-sky-400',
      defaultTitle: 'Thông báo',
    },
  }[type];

  return createPortal(
    <div
      className="fixed top-5 right-5 sm:top-6 sm:right-6 z-[999999] max-w-sm sm:max-w-md w-[calc(100%-2.5rem)] sm:w-full pointer-events-auto animate-fade-in"
      role="status"
      aria-live="polite"
    >
      {/* Toast Card */}
      <div
        className="relative overflow-hidden rounded-2xl bg-white/98 dark:bg-[#121824]/98 backdrop-blur-md border border-slate-200/90 dark:border-slate-800/90 shadow-[0_12px_36px_-6px_rgba(15,23,42,0.16),0_4px_16px_-2px_rgba(15,23,42,0.08)] dark:shadow-[0_16px_40px_-6px_rgba(0,0,0,0.6),0_4px_16px_-2px_rgba(0,0,0,0.4)] p-4"
      >
        <div className="flex items-start gap-3.5">
          {/* Status Icon */}
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${config.iconBox}`}
          >
            <i className={`fa-solid ${config.icon} text-base`} />
          </div>

          {/* Toast Body */}
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`inline-flex items-center text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${config.badge}`}
              >
                {toast.title || config.defaultTitle}
              </span>
            </div>
            <p className="text-xs sm:text-[13.5px] text-slate-700 dark:text-slate-200 font-medium leading-relaxed break-words">
              {toast.message}
            </p>
          </div>

          {/* Close Button */}
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/70 flex items-center justify-center transition-colors cursor-pointer shrink-0 -mr-1 -mt-1"
            aria-label="Đóng thông báo"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Countdown Progress Bar */}
        <div className="absolute bottom-0 left-0 right-0 h-[3px] bg-slate-100 dark:bg-slate-800/60 overflow-hidden">
          <div
            className={`h-full transition-all duration-75 ease-linear ${config.progressBar}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>,
    document.body
  );
};
