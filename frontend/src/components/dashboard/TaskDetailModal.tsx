import React, { useEffect } from 'react';
import { useTranslation } from '@i18n/translate';
import { Badge } from '@components/common';
import { TaskItem } from './ModernDashboardView';
import { formatUserName } from '@lib/roleUtils';

export interface TaskDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: TaskItem | null;
  onNavigateTasks?: () => void;
}

export default function TaskDetailModal({
  isOpen,
  onClose,
  task,
  onNavigateTasks,
}: TaskDetailModalProps) {
  const { t, currentLang } = useTranslation();

  // Đóng bằng phím Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !task) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-5 overflow-y-auto animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="task-detail-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-2xl flex flex-col bg-surface rounded-2xl sm:rounded-3xl shadow-2xl border border-border-subtle overflow-hidden my-auto animate-in zoom-in-95 duration-200">
        {/* Header Modal */}
        <div className="p-5 sm:p-6 pb-4 border-b border-border-subtle bg-surface flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl bg-purple-subtle text-purple flex items-center justify-center shrink-0">
              <i className="fa-solid fa-list-check text-xl" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2
                  id="task-detail-modal-title"
                  className="text-base sm:text-lg font-bold text-main leading-tight truncate"
                >
                  Chi Tiết Nhiệm Vụ Được Giao
                </h2>
                <Badge variant={task.variant} size="sm">
                  {t(`dashboardDetails.taskStatuses.${task.workStatus ?? task.status}`)}
                </Badge>
              </div>
              <p className="text-xs text-secondary mt-0.5 truncate">
                Mã công việc: #CV-{task.id.padStart(2, '0')} · Phân hệ Quản lý công việc (Nhóm 6)
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-muted hover:text-main hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all cursor-pointer shrink-0"
            title="Đóng (ESC)"
            aria-label="Đóng"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Body Modal */}
        <div className="p-5 sm:p-6 space-y-4 max-h-[calc(85vh-140px)] overflow-y-auto">
          {/* Tên nhiệm vụ */}
          <div>
            <div className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
              NỘI DUNG NHIỆM VỤ
            </div>
            <div className="bg-surface-subtle border border-border-subtle rounded-2xl p-4 text-main font-semibold text-base sm:text-lg leading-relaxed shadow-xs">
              {task.title}
            </div>
          </div>

          {/* 2 Cột thông số: Thời gian & Cán bộ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Cột 1: Tiến độ thời gian */}
            <div className="border border-border-subtle rounded-2xl p-4 bg-surface shadow-xs space-y-3">
              <div className="text-xs font-bold text-purple tracking-wider uppercase flex items-center gap-2 pb-2 border-b border-border-subtle">
                <i className="fa-regular fa-clock text-xs" />
                <span>MỐC THỜI GIAN</span>
              </div>
              <div className="text-sm space-y-2">
                <div className="flex justify-between items-center text-secondary">
                  <span>Ngày giao việc:</span>
                  <span className="font-semibold text-main">{task.createdDate || '01/10/2026'}</span>
                </div>
                <div className="flex justify-between items-center text-secondary">
                  <span>Hạn xử lý (Deadline):</span>
                  <span className="font-bold text-danger">{task.due}</span>
                </div>
                <div className="flex justify-between items-center text-secondary">
                  <span>Trạng thái:</span>
                  <Badge variant={task.variant} size="sm">
                    {t(`dashboardDetails.taskStatuses.${task.workStatus ?? task.status}`)}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Cột 2: Cán bộ phụ trách */}
            <div className="border border-border-subtle rounded-2xl p-4 bg-surface shadow-xs space-y-3">
              <div className="text-xs font-bold text-purple tracking-wider uppercase flex items-center gap-2 pb-2 border-b border-border-subtle">
                <i className="fa-solid fa-user-check text-xs" />
                <span>PHÂN CÔNG NHÂN SỰ</span>
              </div>
              <div className="text-sm space-y-2">
                <div className="flex justify-between items-center text-secondary">
                  <span>Người giao việc:</span>
                  <span className="font-semibold text-main">{formatUserName(task.creator || 'Quản trị hệ thống', currentLang)}</span>
                </div>
                <div className="flex justify-between items-center text-secondary">
                  <span>Cán bộ chủ trì:</span>
                  <span className="font-semibold text-main">{task.assignee || 'Trưởng Phòng CNTT'}</span>
                </div>
                <div className="flex justify-between items-center text-secondary">
                  <span>Đơn vị phối hợp:</span>
                  <span className="font-medium text-main">Ban CNTT & Hành chính</span>
                </div>
              </div>
            </div>
          </div>

          {/* Chi tiết yêu cầu xử lý */}
          <div>
            <div className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <i className="fa-regular fa-file-lines text-xs" />
              <span>YÊU CẦU XỬ LÝ & CHỈ ĐẠO</span>
            </div>
            <div className="bg-surface-subtle border border-border-subtle rounded-2xl p-4 text-sm text-secondary leading-relaxed">
              {task.description ||
                'Chủ trì phối hợp cùng các bộ phận liên quan rà soát, lập báo cáo chi tiết và đính kèm biên bản nghiệm thu trước hạn chót. Định kỳ báo cáo tiến độ về Ban Giám đốc.'}
            </div>
          </div>
        </div>

        {/* Footer Modal */}
        <div className="p-4 sm:px-6 bg-surface-subtle border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <span className="text-muted">
            Thuộc phân hệ <strong>Quản Lý Công Việc & Giao Việc (Module 6)</strong>
          </span>

          <div className="flex items-center gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border-subtle bg-surface hover:bg-surface-hover text-secondary font-semibold transition-colors cursor-pointer"
            >
              Đóng
            </button>
            {onNavigateTasks && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onNavigateTasks();
                }}
                className="px-4 py-2 rounded-xl bg-purple hover:bg-purple-hover text-white font-semibold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <span>Xem trang quản lý công việc</span>
                <i className="fa-solid fa-arrow-right text-xs" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
