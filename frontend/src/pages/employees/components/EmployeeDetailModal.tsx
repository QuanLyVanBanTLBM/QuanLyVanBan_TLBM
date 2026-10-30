import React, { useEffect, useRef } from 'react';
import { useTranslation } from '@i18n/translate';
import { Employee } from '@app-types/employee';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';

interface EmployeeDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  employee: Employee | null;
  onEdit?: (employee: Employee) => void;
  returnFocusRef?: React.RefObject<HTMLButtonElement | null>;
}

export const EmployeeDetailModal: React.FC<EmployeeDetailModalProps> = ({
  isOpen,
  onClose,
  employee,
  onEdit,
  returnFocusRef,
}) => {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const onEditRef = useRef(onEdit);
  const skipFocusRestoreRef = useRef(false);
  const employeeKey = employee?.id ?? null;

  useEffect(() => {
    onCloseRef.current = onClose;
    onEditRef.current = onEdit;
  }, [onClose, onEdit]);

  useEffect(() => {
    if (!isOpen || employeeKey === null) return;

    skipFocusRestoreRef.current = false;
    const opener = returnFocusRef?.current;
    closeButtonRef.current?.focus();

    const dialog = dialogRef.current;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== 'Tab' || !dialog) return;

      const focusableElements = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter((element) => {
        const style = window.getComputedStyle(element);
        return element.getAttribute('aria-hidden') !== 'true' && style.display !== 'none' && style.visibility !== 'hidden';
      });

      if (focusableElements.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = focusableElements[0];
      const last = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && (activeElement === first || !dialog.contains(activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (activeElement === last || !dialog.contains(activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (skipFocusRestoreRef.current) {
        skipFocusRestoreRef.current = false;
        return;
      }
      window.requestAnimationFrame(() => {
        if (opener?.isConnected) opener.focus();
      });
    };
  }, [isOpen, employeeKey, returnFocusRef]);

  if (!isOpen || !employee) return null;

  const initials = (employee.ho_ten || 'NV')
    .split(' ')
    .filter(Boolean)
    .slice(-2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  const isWorking = employee.trang_thai === 'LAM_VIEC';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="employee-detail-title"
        tabIndex={-1}
        className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-up focus:outline-none"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-id-card text-primary text-lg" />
            <h2 id="employee-detail-title" className="text-lg font-bold text-main">
              {t('employees.detail.title')}
            </h2>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label={t('employees.actions.close')}
            className="text-secondary hover:text-main p-2 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Header Card with Avatar */}
          <div className="flex items-center gap-4 p-4 bg-surface-elevated border border-border rounded-xl">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-primary to-primary-hover text-white flex items-center justify-center text-xl font-bold shrink-0 shadow-md">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-xl font-bold text-main truncate">
                  {employee.ho_ten}
                </h3>
                <Badge variant={isWorking ? 'success' : 'danger'}>
                  {isWorking ? t('employees.status.working') : t('employees.status.resigned')}
                </Badge>
                {employee.is_public ? (
                  <Badge variant="info">{t('employees.fields.public')}</Badge>
                ) : (
                  <Badge variant="secondary">{t('employees.fields.internalOnly')}</Badge>
                )}
              </div>
              <p className="text-sm text-secondary truncate mt-0.5">
                @{employee.username} • {employee.email}
              </p>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Đơn vị */}
            <div className="p-3.5 bg-surface-elevated border border-border rounded-lg space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                {t('employees.fields.unit')}
              </span>
              <span className="text-sm font-medium text-main block">
                {employee.don_vi_ten || '—'}
              </span>
              {employee.khoi_ten && (
                <span className="text-xs text-secondary block">
                  {t('employees.fields.region')}: {employee.khoi_ten}
                </span>
              )}
            </div>

            {/* Chức vụ & Chức danh */}
            <div className="p-3.5 bg-surface-elevated border border-border rounded-lg space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                {t('employees.fields.position')}
              </span>
              <span className="text-sm font-medium text-main block">
                {employee.chuc_vu_ten || '—'}
              </span>
              {employee.chuc_danh && (
                <span className="text-xs text-secondary block">
                  {t('employees.fields.title')}: {employee.chuc_danh}
                </span>
              )}
            </div>

            {/* Ngày sinh (với bảo mật quyền riêng tư) */}
            <div className="p-3.5 bg-surface-elevated border border-border rounded-lg space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                  {t('employees.fields.birthday')}
                </span>
                {employee.is_birthday_masked && (
                  <span
                    className="inline-flex items-center gap-1 text-[11px] text-warning bg-warning-subtle px-2 py-0.5 rounded-full"
                    title={t('employees.hints.birthdayMaskedTooltip')}
                  >
                    <i className="fa-solid fa-lock text-[10px]" />
                    {t('employees.hints.masked')}
                  </span>
                )}
              </div>
              <span className="text-sm font-medium text-main block font-mono">
                {employee.ngay_sinh || '—'}
              </span>
            </div>

            {/* Số điện thoại */}
            <div className="p-3.5 bg-surface-elevated border border-border rounded-lg space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                {t('employees.fields.phone')}
              </span>
              <span className="text-sm font-medium text-main block">
                {employee.sdt ? (
                  <a
                    href={`tel:${employee.sdt}`}
                    className="text-primary hover:underline"
                  >
                    {employee.sdt}
                  </a>
                ) : (
                  '—'
                )}
              </span>
            </div>
          </div>

          {/* Phân công kiêm nhiệm (Đa phòng ban & Chức vụ) */}
          {employee.assignments && employee.assignments.length > 0 && (
            <div className="p-4 bg-surface-elevated border border-border rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                  {t('employees.fields.concurrentAssignments')}
                </span>
                <span className="text-xs font-medium text-primary bg-primary-subtle px-2 py-0.5 rounded-full border border-primary-border">
                  {employee.assignments.length}
                </span>
              </div>
              <div className="space-y-2">
                {employee.assignments.map((assignment, index) => (
                  <div
                    key={assignment.id || index}
                    className="p-3 bg-surface border border-border rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <i className="fa-solid fa-building text-xs text-primary" />
                        <span className="text-sm font-semibold text-main">
                          {assignment.don_vi_ten || '—'}
                        </span>
                      </div>
                      {assignment.khoi_ten && (
                        <span className="text-xs text-secondary block pl-4">
                          {t('employees.fields.region')}: {assignment.khoi_ten}
                        </span>
                      )}
                    </div>
                    <div className="sm:text-right space-y-0.5">
                      <div className="flex items-center sm:justify-end gap-1.5">
                        <i className="fa-solid fa-briefcase text-xs text-secondary" />
                        <span className="text-sm font-medium text-main">
                          {assignment.chuc_vu_ten || '—'}
                        </span>
                      </div>
                      {assignment.chuc_danh && (
                        <span className="text-xs text-secondary block">
                          {assignment.chuc_danh}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nhóm quyền (RBAC) */}
          <div className="p-4 bg-surface-elevated border border-border rounded-lg space-y-2">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
              {t('employees.fields.groups')}
            </span>
            {employee.nhom_quyen && employee.nhom_quyen.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {employee.nhom_quyen.map((group) => (
                  <span
                    key={group.id}
                    className="px-2.5 py-1 text-xs font-medium rounded-md bg-primary-subtle text-primary border border-primary-border"
                  >
                    <i className="fa-solid fa-shield-halved mr-1.5" />
                    {group.name}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-xs text-muted">
                {employee.has_sensitive_permission
                  ? t('employees.detail.noGroups')
                  : t('employees.hints.groupsHidden')}
              </span>
            )}
          </div>

          {/* Ghi chú */}
          {employee.ghi_chu && (
            <div className="p-4 bg-surface-elevated border border-border rounded-lg space-y-1">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider block">
                {t('employees.fields.notes')}
              </span>
              <p className="text-sm text-secondary whitespace-pre-line leading-relaxed">
                {employee.ghi_chu}
              </p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface-elevated">
          <span className="text-xs text-muted">
            ID: #{employee.id} • {t('employees.fields.joined')}: {new Date(employee.created_at).toLocaleDateString()}
          </span>
          <div className="flex items-center gap-3">
            <Button type="button" variant="secondary" onClick={onClose}>
              {t('employees.actions.close')}
            </Button>
            {onEdit && (
              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  skipFocusRestoreRef.current = true;
                  onEditRef.current?.(employee);
                }}
                icon="fa-pen-to-square"
              >
                {t('employees.actions.edit')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
