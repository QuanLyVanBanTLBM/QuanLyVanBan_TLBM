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
    const duration = toast.duration || 2600;
    const interval = 50;
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

  const config = {
    success: {
      icon: 'fa-circle-check',
      iconBg: 'bg-emerald-50 text-emerald-600 border border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-400 dark:border-emerald-800',
      badgeBg: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/90 dark:text-emerald-300 dark:border-emerald-800',
      defaultTitle: 'Thành công',
      accentBorder: 'border-l-4 border-l-emerald-500 border-border-subtle',
      progressBar: 'bg-emerald-500',
    },
    danger: {
      icon: 'fa-circle-xmark',
      iconBg: 'bg-rose-50 text-rose-600 border border-rose-200 dark:bg-rose-950/80 dark:text-rose-400 dark:border-rose-800',
      badgeBg: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/90 dark:text-rose-300 dark:border-rose-800',
      defaultTitle: 'Đã xóa',
      accentBorder: 'border-l-4 border-l-rose-500 border-border-subtle',
      progressBar: 'bg-rose-500',
    },
    warning: {
      icon: 'fa-triangle-exclamation',
      iconBg: 'bg-amber-50 text-amber-600 border border-amber-200 dark:bg-amber-950/80 dark:text-amber-400 dark:border-amber-800',
      badgeBg: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/90 dark:text-amber-300 dark:border-amber-800',
      defaultTitle: 'Cảnh báo',
      accentBorder: 'border-l-4 border-l-amber-500 border-border-subtle',
      progressBar: 'bg-amber-500',
    },
    info: {
      icon: 'fa-circle-info',
      iconBg: 'bg-sky-50 text-sky-600 border border-sky-200 dark:bg-sky-950/80 dark:text-sky-400 dark:border-sky-800',
      badgeBg: 'bg-sky-50 text-sky-700 border border-sky-200 dark:bg-sky-950/90 dark:text-sky-300 dark:border-sky-800',
      defaultTitle: 'Thông báo',
      accentBorder: 'border-l-4 border-l-sky-500 border-border-subtle',
      progressBar: 'bg-sky-500',
    },
  }[type];

  return createPortal(
    <div
      className="fixed top-6 right-6 z-[999999] max-w-sm sm:max-w-md w-full px-3 sm:px-0 animate-fade-in pointer-events-auto"
      role="status"
      aria-live="polite"
    >
      {/* Khung Toast: Nền đặc 100% OPAQUE (bg-white trên nền sáng, bg-[#121824] trên nền tối), tuyệt đối không trong suốt */}
      <div
        className={`relative overflow-hidden rounded-2xl bg-white dark:bg-[#121824] border border-border-subtle shadow-2xl p-4 transition-all ${config.accentBorder}`}
        style={{
          boxShadow: '0 20px 45px -10px rgba(0, 0, 0, 0.25), 0 10px 20px -5px rgba(0, 0, 0, 0.15)',
        }}
      >
        <div className="flex items-start gap-3">
          {/* Icon badge */}
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${config.iconBg}`}
          >
            <i className={`fa-solid ${config.icon} text-base`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 pr-1">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${config.badgeBg}`}
              >
                {toast.title || config.defaultTitle}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-neutral-900 dark:text-neutral-100 font-semibold leading-snug break-words">
              {toast.message}
            </p>
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg text-muted hover:text-main hover:bg-neutral-100 dark:hover:bg-neutral-800 flex items-center justify-center transition-colors cursor-pointer shrink-0 -mr-1 -mt-1"
            aria-label="Đóng thông báo"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Progress bar countdown */}
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-neutral-100 dark:bg-neutral-800">
          <div
            className={`h-full transition-all duration-75 ${config.progressBar}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>,
    document.body
  );
};
