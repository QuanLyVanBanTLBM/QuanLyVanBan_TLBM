import React, { useState, useEffect, useCallback, useRef } from 'react';
import './EmployeesPage.mobile.css';
import { useTranslation } from '@i18n/translate';
import { apiClient, downloadBlob } from '@lib/apiClient';
import { usePermissions } from '@lib/permissions';
import { authService } from '@lib/authService';
import {
  Employee,
  Position,
  GroupSimple,
  EmployeeCreatePayload,
  EmployeeUpdatePayload,
} from '@app-types/employee';
import { Unit, PaginatedResponse } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Select } from '@components/common/Select';
import { EmployeeModal } from './components/EmployeeModal';
import { EmployeeDetailModal } from './components/EmployeeDetailModal';
import { EmployeeImportModal } from './components/EmployeeImportModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';

export default function EmployeesPage() {
  const { t } = useTranslation();
  const { can, isSuperuser } = usePermissions();
  const currentSession = authService.getSession();
  const canEditEmployee = (employee: Employee) =>
    isSuperuser ||
    (can('change_self_cbnv') && Boolean(currentSession?.username && currentSession.username === employee.username));

  // Dữ liệu danh sách & phân trang
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Danh mục phục vụ dropdown lọc và tạo/sửa
  const [units, setUnits] = useState<Unit[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [groups, setGroups] = useState<GroupSimple[]>([]);

  // Bộ lọc
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedUnitId, setSelectedUnitId] = useState<string>('');
  const [selectedPositionId, setSelectedPositionId] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  // Trạng thái tải & thông báo
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; isError?: boolean } | null>(null);

  // Quản lý Modal
  const [isEmployeeModalOpen, setIsEmployeeModalOpen] = useState<boolean>(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [detailEmployee, setDetailEmployee] = useState<Employee | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState<boolean>(false);
  const detailTriggerRef = useRef<HTMLButtonElement | null>(null);

  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);

  const [deletingEmployee, setDeletingEmployee] = useState<Employee | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null);

  // Hiển thị Toast tự tắt sau 4s
  const showToast = useCallback((text: string, isError = false) => {
    setToastMessage({ text, isError });
    setTimeout(() => setToastMessage(null), 4000);
  }, []);

  // 1. Tải danh mục Đơn vị, Chức vụ và Nhóm quyền
  useEffect(() => {
    apiClient<Unit[]>('/api/organizations/units/?all=true')
      .then((res) => {
        if (Array.isArray(res)) setUnits(res);
        else if (res && 'results' in res) setUnits((res as PaginatedResponse<Unit>).results);
      })
      .catch(() => {});

    apiClient<Position[]>('/api/positions/?all=true')
      .then((res) => {
        if (Array.isArray(res)) setPositions(res);
        else if (res && 'results' in res) setPositions((res as PaginatedResponse<Position>).results);
      })
      .catch(() => {});

    apiClient<GroupSimple[]>('/api/accounts/groups/')
      .then((res) => {
        if (Array.isArray(res)) setGroups(res);
      })
      .catch(() => {});
  }, []);

  const [reloadKey, setReloadKey] = useState<number>(0);
  const refreshList = useCallback(() => {
    setIsLoading(true);
    setReloadKey((prev) => prev + 1);
  }, []);

  // 2. Tải danh sách CBNV có tìm kiếm & phân trang
  useEffect(() => {
    let ignore = false;
    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    if (searchQuery.trim()) params.append('search', searchQuery.trim());
    if (selectedUnitId) params.append('don_vi_id', selectedUnitId);
    if (selectedPositionId) params.append('chuc_vu_id', selectedPositionId);
    if (selectedStatus) params.append('trang_thai', selectedStatus);

    apiClient<PaginatedResponse<Employee>>(`/api/accounts/employees/?${params.toString()}`)
      .then((res) => {
        if (!ignore) {
          setEmployees(res.results || []);
          setTotalCount(res.count || 0);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!ignore) {
          showToast(t('employees.messages.fetchError'), true);
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, searchQuery, selectedUnitId, selectedPositionId, selectedStatus, reloadKey]);

  // Xuất file Excel toàn bộ danh sách CBNV (Yêu cầu 1 & 4)
  const handleExportExcel = async () => {
    try {
      setIsExporting(true);
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      if (selectedUnitId) params.append('don_vi_id', selectedUnitId);
      if (selectedPositionId) params.append('chuc_vu_id', selectedPositionId);
      if (selectedStatus) params.append('trang_thai', selectedStatus);

      const queryString = params.toString() ? `?${params.toString()}` : '';
      await downloadBlob(`/api/accounts/employees/export/${queryString}`, 'danh_sach_cbnv.xlsx');
      showToast(t('employees.messages.exportSuccess'));
    } catch {
      showToast(t('employees.messages.exportError'), true);
    } finally {
      setIsExporting(false);
    }
  };

  // Thêm mới hoặc Cập nhật CBNV
  const handleSubmitEmployee = async (
    payload: EmployeeCreatePayload | EmployeeUpdatePayload
  ): Promise<{ temporary_password?: string | null } | void> => {
    setIsSubmitting(true);
    try {
      if (editingEmployee) {
        await apiClient.patch(`/api/accounts/employees/${editingEmployee.id}/`, payload);
        showToast(t('employees.messages.updateSuccess'));
        setIsEmployeeModalOpen(false);
        setEditingEmployee(null);
        refreshList();
      } else {
        const res = await apiClient.post<Employee>('/api/accounts/employees/', payload);
        showToast(t('employees.messages.createSuccess'));
        refreshList();
        if (res.temporary_password) {
          return { temporary_password: res.temporary_password };
        }
        setIsEmployeeModalOpen(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Xóa CBNV
  const handleConfirmDelete = async (password: string) => {
    if (!deletingEmployee) return;
    try {
      setIsDeleting(true);
      setDeleteErrorMessage(null);

      await apiClient.delete(`/api/accounts/employees/${deletingEmployee.id}/`, {
        body: JSON.stringify({ password }),
      });
      showToast(t('employees.messages.deleteSuccess'));
      setDeletingEmployee(null);
      refreshList();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const errorData = (err as { data: { detail?: string } }).data;
        if (errorData?.detail) {
          setDeleteErrorMessage(t(errorData.detail));
          return;
        }
      }
      setDeleteErrorMessage(t('employees.messages.deleteError'));
    } finally {
      setIsDeleting(false);
    }
  };

  // Reset bộ lọc
  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedUnitId('');
    setSelectedPositionId('');
    setSelectedStatus('');
    setCurrentPage(1);
  };

  const isFiltered = Boolean(searchQuery || selectedUnitId || selectedPositionId || selectedStatus);
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="employees-page space-y-6">
      {/* Page Header */}
      <div className="employees-page__header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-main flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-base">
              <i className="fa-solid fa-users" />
            </span>
            {t('employees.title')}
          </h1>
          <p className="text-sm text-secondary mt-1">
            {t('employees.subtitle')}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="employees-page__actions flex items-center gap-2.5 flex-wrap">
          {can('export_cbnv') && (
            <Button
              type="button"
              variant="secondary"
              onClick={handleExportExcel}
              isLoading={isExporting}
              icon="fa-file-excel"
              className="employees-page__action employees-page__action--export"
            >
              {t('employees.actions.exportExcel')}
            </Button>
          )}

          {can('import_cbnv') && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsImportModalOpen(true)}
              icon="fa-file-import"
              className="employees-page__action employees-page__action--import"
            >
              {t('employees.actions.importExcel')}
            </Button>
          )}

          {can('add_cbnv') && (
            <Button
              type="button"
              variant="primary"
              onClick={() => {
                setEditingEmployee(null);
                setIsEmployeeModalOpen(true);
              }}
              icon="fa-user-plus"
              className="employees-page__action employees-page__action--add"
            >
              {t('employees.actions.addEmployee')}
            </Button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="employees-page__filters p-4 bg-surface border border-border rounded-xl shadow-sm space-y-3">
        <div className="employees-page__filter-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Ô tìm kiếm đa năng */}
          <div className="relative">
            <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder={t('employees.placeholders.search')}
              className="w-full pl-9 pr-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          {/* Lọc theo Đơn vị */}
          <Select
            value={selectedUnitId}
            onChange={(val) => {
              setSelectedUnitId(val);
              setCurrentPage(1);
            }}
            placeholder={t('employees.filters.allUnits')}
            leftIcon="fa-building"
            clearable
            searchable
            options={[
              { value: '', label: t('employees.filters.allUnits') },
              ...units.map((u) => ({
                value: String(u.id),
                label: u.ten,
                group: u.khoi_ten || undefined,
              })),
            ]}
          />

          {/* Lọc theo Chức vụ */}
          <Select
            value={selectedPositionId}
            onChange={(val) => {
              setSelectedPositionId(val);
              setCurrentPage(1);
            }}
            placeholder={t('employees.filters.allPositions')}
            leftIcon="fa-id-badge"
            clearable
            options={[
              { value: '', label: t('employees.filters.allPositions') },
              ...positions.map((p) => ({
                value: String(p.id),
                label: p.name,
              })),
            ]}
          />

          {/* Lọc theo Trạng thái */}
          <Select
            value={selectedStatus}
            onChange={(val) => {
              setSelectedStatus(val);
              setCurrentPage(1);
            }}
            placeholder={t('employees.filters.allStatuses')}
            leftIcon="fa-circle-dot"
            clearable
            options={[
              { value: '', label: t('employees.filters.allStatuses') },
              {
                value: 'LAM_VIEC',
                label: t('employees.status.working'),
                icon: 'fa-circle-check',
                badge: <Badge variant="success" size="sm">{t('employees.status.working')}</Badge>,
              },
              {
                value: 'NGHI_VIEC',
                label: t('employees.status.resigned'),
                icon: 'fa-circle-xmark',
                badge: <Badge variant="secondary" size="sm">{t('employees.status.resigned')}</Badge>,
              },
            ]}
          />
        </div>

        {/* Nút xóa nhanh bộ lọc */}
        {isFiltered && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-secondary">
              {t('employees.filters.filteringNotice', { count: totalCount })}
            </span>
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
            >
              <i className="fa-solid fa-arrow-rotate-left" />
              {t('employees.filters.reset')}
            </button>
          </div>
        )}
      </div>

      {/* Main Table Card */}
      <div className="employees-page__table-card bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="employees-page__table-scroll overflow-x-auto">
          <table className="employees-page__table w-full text-left text-sm">
            <thead className="employees-page__table-head bg-surface-elevated text-secondary font-semibold border-b border-border text-xs uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4 w-12 text-center">#</th>
                <th className="py-3 px-4">{t('employees.table.employee')}</th>
                <th className="py-3 px-4">{t('employees.table.unit')}</th>
                <th className="py-3 px-4">{t('employees.table.position')}</th>
                <th className="py-3 px-4">{t('employees.table.birthday')}</th>
                <th className="py-3 px-4">{t('employees.table.phone')}</th>
                <th className="py-3 px-4 text-center">{t('employees.table.status')}</th>
                <th className="py-3 px-4 text-right">{t('employees.table.actions')}</th>
              </tr>
            </thead>
            <tbody className="employees-page__table-body divide-y divide-border">
              {isLoading ? (
                <tr className="employees-page__empty-row">
                  <td colSpan={8} className="py-12 text-center text-muted">
                    <div className="inline-flex items-center gap-2">
                      <i className="fa-solid fa-spinner fa-spin text-primary text-lg" />
                      <span>{t('employees.messages.loading')}</span>
                    </div>
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr className="employees-page__empty-row">
                  <td colSpan={8} className="py-12 text-center text-muted">
                    <div className="space-y-2">
                      <div className="w-12 h-12 rounded-full bg-surface-elevated text-muted flex items-center justify-center mx-auto text-xl">
                        <i className="fa-solid fa-user-slash" />
                      </div>
                      <p className="font-semibold text-main">{t('employees.messages.noData')}</p>
                      <p className="text-xs">{t('employees.messages.noDataHelp')}</p>
                    </div>
                  </td>
                </tr>
              ) : (
                employees.map((emp, idx) => {
                  const initials = (emp.ho_ten || 'NV')
                    .split(' ')
                    .filter(Boolean)
                    .slice(-2)
                    .map((w) => w[0])
                    .join('')
                    .toUpperCase();
                  const isWorking = emp.trang_thai === 'LAM_VIEC';
                  const rowNumber = (currentPage - 1) * pageSize + idx + 1;

                  return (
                    <tr key={emp.id} className="employees-page__employee-row hover:bg-surface-hover transition-colors">
                      {/* STT */}
                      <td className="employees-page__cell employees-page__cell--ordinal py-3.5 px-4 text-center text-xs text-muted font-mono">
                        {rowNumber}
                      </td>

                      {/* Họ tên & Avatar */}
                      <td className="employees-page__cell employees-page__cell--identity py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-primary-hover text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm">
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <span
                              onClick={() => {
                                setDetailEmployee(emp);
                                setIsDetailModalOpen(true);
                              }}
                              className="font-semibold text-main hover:text-primary cursor-pointer truncate block"
                            >
                              {emp.ho_ten}
                            </span>
                            <span className="text-xs text-muted truncate block">
                              @{emp.username} • {emp.email}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Đơn vị */}
                      <td className="employees-page__cell employees-page__cell--unit py-3.5 px-4" data-label={t('employees.table.unit')}>
                        <span className="font-medium text-main block">
                          {emp.don_vi_ten || '—'}
                        </span>
                        {emp.khoi_ten && (
                          <span className="text-[11px] text-muted block">
                            {emp.khoi_ten}
                          </span>
                        )}
                        {emp.assignments && emp.assignments.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            <span
                              className="inline-flex items-center gap-1 text-[10px] font-medium text-primary bg-primary-subtle px-1.5 py-0.5 rounded"
                              title={emp.assignments
                                .map(
                                  (a) =>
                                    `${a.don_vi_ten} (${a.chuc_vu_ten}${
                                      a.chuc_danh ? ` - ${a.chuc_danh}` : ''
                                    })`
                                )
                                .join('; ')}
                            >
                              <i className="fa-solid fa-briefcase text-[9px]" />
                              {t('employees.fields.concurrentBadge', { count: emp.assignments.length })}
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Chức vụ & Chức danh */}
                      <td className="employees-page__cell employees-page__cell--position py-3.5 px-4" data-label={t('employees.table.position')}>
                        <span className="font-medium text-main block">
                          {emp.chuc_vu_ten || '—'}
                        </span>
                        {emp.chuc_danh && (
                          <span className="text-[11px] text-muted block">
                            {emp.chuc_danh}
                          </span>
                        )}
                      </td>

                      {/* Ngày sinh */}
                      <td className="employees-page__cell employees-page__cell--birthday py-3.5 px-4" data-label={t('employees.table.birthday')}>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-main">{emp.ngay_sinh || '—'}</span>
                          {emp.is_birthday_masked && (
                            <span
                              className="text-warning text-[10px]"
                              title={t('employees.hints.birthdayMaskedTooltip')}
                            >
                              <i className="fa-solid fa-lock" />
                            </span>
                          )}
                        </div>
                      </td>

                      {/* SĐT */}
                      <td className="employees-page__cell employees-page__cell--phone py-3.5 px-4" data-label={t('employees.table.phone')}>
                        {emp.sdt ? (
                          <a
                            href={`tel:${emp.sdt}`}
                            className="font-medium text-main hover:text-primary transition-colors inline-flex items-center gap-1.5"
                          >
                            <i className="fa-solid fa-phone text-xs text-muted" />
                            <span>{emp.sdt}</span>
                          </a>
                        ) : (
                          <span className="font-medium text-muted">—</span>
                        )}
                      </td>

                      {/* Trạng thái */}
                      <td className="employees-page__cell employees-page__cell--status py-3.5 px-4 text-center">
                        <Badge variant={isWorking ? 'success' : 'danger'}>
                          {isWorking ? t('employees.status.working') : t('employees.status.resigned')}
                        </Badge>
                      </td>

                      {/* Thao tác */}
                      <td className="employees-page__cell employees-page__cell--actions py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* Xem chi tiết */}
                          <button
                            type="button"
                            onClick={(event) => {
                              detailTriggerRef.current = event.currentTarget;
                              setDetailEmployee(emp);
                              setIsDetailModalOpen(true);
                            }}
                            className="p-1.5 rounded-lg text-secondary hover:text-primary hover:bg-surface-elevated transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                            title={t('employees.actions.view')}
                          >
                            <i className="fa-solid fa-eye text-sm" />
                          </button>

                          {/* Chỉnh sửa: Có quyền change_full_cbnv hoặc change_self_cbnv đối với chính mình */}
                          {canEditEmployee(emp) && (
                            <button
                              type="button"
                              onClick={() => {
                                setEditingEmployee(emp);
                                setIsEmployeeModalOpen(true);
                              }}
                              className="p-1.5 rounded-lg text-secondary hover:text-primary hover:bg-surface-elevated transition-colors cursor-pointer"
                              title={t('employees.actions.edit')}
                            >
                              <i className="fa-solid fa-pen-to-square text-sm" />
                            </button>
                          )}

                          {/* Xóa */}
                          {can('delete_cbnv') && (
                            <button
                              type="button"
                              onClick={() => {
                                setDeleteErrorMessage(null);
                                setDeletingEmployee(emp);
                              }}
                              className="p-1.5 rounded-lg text-secondary hover:text-danger hover:bg-danger-subtle transition-colors cursor-pointer"
                              title={t('employees.actions.delete')}
                            >
                              <i className="fa-solid fa-trash-can text-sm" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="employees-page__pagination flex items-center justify-between px-6 py-3.5 border-t border-border bg-surface-elevated text-xs text-secondary">
          <span>
            {t('employees.pagination.showing', {
              from: employees.length > 0 ? (currentPage - 1) * pageSize + 1 : 0,
              to: Math.min(currentPage * pageSize, totalCount),
              total: totalCount,
            })}
          </span>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              className="px-2.5 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <i className="fa-solid fa-chevron-left" />
            </button>

            <span className="px-3 py-1 font-semibold text-main">
              {currentPage} / {totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage >= totalPages || isLoading}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              className="px-2.5 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <i className="fa-solid fa-chevron-right" />
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <EmployeeModal
        key={editingEmployee?.id ?? (isEmployeeModalOpen ? 'open-new-emp' : 'closed-emp')}
        isOpen={isEmployeeModalOpen}
        onClose={() => {
          setIsEmployeeModalOpen(false);
          setEditingEmployee(null);
        }}
        onSubmit={handleSubmitEmployee}
        initialData={editingEmployee}
        units={units}
        positions={positions}
        groups={groups}
        isLoading={isSubmitting}
        isAdmin={isSuperuser}
        onChangePassword={async (employeeId, newPassword, confirmPassword) => {
          await apiClient.post(`/api/accounts/employees/${employeeId}/change-password/`, {
            new_password: newPassword,
            confirm_password: confirmPassword,
          });
          showToast(t('employees.messages.passwordChangeSuccess'));
        }}
      />

      <EmployeeDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setDetailEmployee(null);
        }}
        employee={detailEmployee}
        returnFocusRef={detailTriggerRef}
        onEdit={detailEmployee && canEditEmployee(detailEmployee) ? (emp) => {
          setIsDetailModalOpen(false);
          setDetailEmployee(null);
          setEditingEmployee(emp);
          setIsEmployeeModalOpen(true);
        } : undefined}
      />

      {isImportModalOpen && (
        <EmployeeImportModal
          isOpen={isImportModalOpen}
          onClose={() => setIsImportModalOpen(false)}
          onSuccess={(count) => {
            showToast(t('employees.messages.importSuccess', { count }));
            refreshList();
          }}
        />
      )}

      <DeleteConfirmModal
        key={deletingEmployee?.id ? `del-${deletingEmployee.id}` : 'del-closed'}
        isOpen={Boolean(deletingEmployee)}
        onClose={() => {
          setDeletingEmployee(null);
          setDeleteErrorMessage(null);
        }}
        onConfirm={handleConfirmDelete}
        name={deletingEmployee?.ho_ten || ''}
        isLoading={isDeleting}
        errorMessage={deleteErrorMessage}
      />

      {/* Toast Notification - Luôn nổi lên trên cùng (z-[9999]), không bị backdrop của Modal làm mờ */}
      {toastMessage && (
        <div
          role="alert"
          aria-live="assertive"
          className={`fixed bottom-6 right-6 z-[9999] max-w-md px-5 py-3.5 rounded-xl shadow-2xl flex items-center gap-3 animate-fade-in border ${
            toastMessage.isError
              ? 'bg-danger text-white border-red-300/40 shadow-red-900/30'
              : 'bg-success text-white border-emerald-300/40 shadow-emerald-900/30'
          }`}
        >
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0 text-base">
            <i
              className={`fa-solid ${
                toastMessage.isError ? 'fa-circle-exclamation' : 'fa-circle-check'
              }`}
            />
          </div>
          <span className="text-sm font-semibold tracking-wide flex-1 break-words leading-snug">
            {toastMessage.text}
          </span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-white/80 hover:text-white p-1 rounded transition-colors text-base"
            aria-label="Đóng thông báo"
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </div>
      )}
    </div>
  );
}
