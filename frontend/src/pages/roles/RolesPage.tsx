import React, { useState, useEffect } from 'react';
import { useTranslation } from '@i18n/translate';
import { apiClient } from '@lib/apiClient';
import { usePermissions } from '@lib/permissions';
import { Role, Permission, PaginatedResponse } from '@app-types/authorization';
import { Button } from '@components/common/Button';
import { RoleModal } from './components/RoleModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';
import { PermissionMatrix } from './components/PermissionMatrix';
import { filterPermissions } from './components/permissionFilter';

export default function RolesPage() {
  const { t } = useTranslation();
  // Chỉ ẩn/hiện thao tác cho gọn giao diện; backend vẫn kiểm quyền thật (view/add/change/delete_nhomquyen).
  const { can } = usePermissions();
  const canAdd = can('add_nhomquyen');
  const canChange = can('change_nhomquyen');
  const canDelete = can('delete_nhomquyen');

  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoadingRoles, setIsLoadingRoles] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState<number>(0);

  const [permissions, setPermissions] = useState<Permission[]>([]);

  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<number>>(new Set());
  const [isSavingPermissions, setIsSavingPermissions] = useState<boolean>(false);
  const [permissionQuery, setPermissionQuery] = useState<string>('');

  const [isRoleModalOpen, setIsRoleModalOpen] = useState<boolean>(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [isSubmittingRole, setIsSubmittingRole] = useState<boolean>(false);

  const [deletingRole, setDeletingRole] = useState<Role | null>(null);
  const [deleteErrorKey, setDeleteErrorKey] = useState<string | null>(null);
  const [isDeletingRole, setIsDeletingRole] = useState<boolean>(false);

  const [toastMessage, setToastMessage] = useState<{ textKey: string; isError?: boolean } | null>(null);

  const showToast = (textKey: string, isError = false) => {
    setToastMessage({ textKey, isError });
    setTimeout(() => setToastMessage(null), 3500);
  };

  const selectedRole = roles.find((r) => r.id === selectedRoleId) || null;
  // Năm nhóm chuẩn của DDL (có mã nhóm quyền) không đổi tên, không xóa được; quyền vẫn chỉnh được.
  const isProtectedRole = !!selectedRole?.ma_nhom_quyen;

  // Có tick/bỏ tick mà chưa bấm Lưu (so với quyền đã lưu của nhóm đang chọn)
  const savedPermissionIds = new Set(selectedRole?.permission_ids || []);
  const hasUnsavedChanges =
    !!selectedRole &&
    (savedPermissionIds.size !== selectedPermissionIds.size ||
      Array.from(selectedPermissionIds).some((id) => !savedPermissionIds.has(id)));
  const confirmDiscardChanges = () => !hasUnsavedChanges || window.confirm(t('roles.messages.unsavedConfirm'));

  // "Chọn tất cả" / "Bỏ chọn" chỉ tác động lên các quyền đang hiện theo ô tìm, giữ nguyên quyền đang ẩn
  const setVisiblePermissions = (checked: boolean) => {
    const visibleIds = filterPermissions(permissions, permissionQuery).map((p) => p.id);
    setSelectedPermissionIds((prev) => {
      const next = new Set(prev);
      visibleIds.forEach((id) => (checked ? next.add(id) : next.delete(id)));
      return next;
    });
  };

  // Tải toàn bộ danh sách quyền hệ thống (1 lần, dùng chung cho mọi nhóm quyền)
  useEffect(() => {
    let ignore = false;
    apiClient<Permission[]>('/api/permissions/?all=true')
      .then((data) => {
        if (!ignore) setPermissions(data || []);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, []);

  const requestRoles = () =>
    apiClient<PaginatedResponse<Role> | Role[]>('/api/roles/?all=true').then((res) =>
      Array.isArray(res) ? res : res.results || []
    );

  const roleErrorKey = (err: unknown): string => {
    const detail =
      err && typeof err === 'object' && 'data' in err
        ? (err as { data?: { detail?: string } }).data?.detail
        : undefined;
    return detail || 'roles.messages.fetchError';
  };

  // Lấy key i18n lỗi từ phản hồi lưu quyền (vd nhóm ADMIN bắt buộc giữ quyền quản lý nhóm quyền)
  const saveErrorKey = (err: unknown): string => {
    const data =
      err && typeof err === 'object' && 'data' in err
        ? (err as { data?: { detail?: unknown; permission_ids?: unknown } }).data
        : undefined;
    const candidates = [data?.detail, ...(Array.isArray(data?.permission_ids) ? data.permission_ids : [])];
    const key = candidates.find((c) => typeof c === 'string' && c.startsWith('roles.'));
    return (key as string | undefined) || 'roles.messages.fetchError';
  };

  // Tải lần đầu / khi bấm "Thử lại" (trạng thái đang tải ban đầu đã là true, nút Thử lại tự đặt lại trước khi đổi retryToken)
  useEffect(() => {
    let ignore = false;
    requestRoles()
      .then((list) => {
        if (ignore) return;
        setRoles(list);
        setFetchError(null);
        setIsLoadingRoles(false);
      })
      .catch((err: unknown) => {
        if (ignore) return;
        const errorKey = roleErrorKey(err);
        setFetchError(errorKey);
        setRoles([]);
        showToast(errorKey, true);
        setIsLoadingRoles(false);
      });
    return () => {
      ignore = true;
    };
  }, [retryToken]);

  // Tải lại sau khi thêm/sửa/xóa (gọi từ sự kiện)
  const reloadRoles = async () => {
    setIsLoadingRoles(true);
    setFetchError(null);
    try {
      setRoles(await requestRoles());
    } catch (err: unknown) {
      const errorKey = roleErrorKey(err);
      setFetchError(errorKey);
      setRoles([]);
      showToast(errorKey, true);
    } finally {
      setIsLoadingRoles(false);
    }
  };

  // Khi chọn 1 nhóm quyền bên trái, dùng permission_ids đã có sẵn trong danh sách (list trả đủ field)
  const selectRole = (roleId: number) => {
    if (roleId === selectedRoleId || !confirmDiscardChanges()) return;
    setSelectedRoleId(roleId);
    const role = roles.find((r) => r.id === roleId);
    setSelectedPermissionIds(new Set(role?.permission_ids || []));
  };

  const togglePermission = (permId: number) => {
    setSelectedPermissionIds((prev) => {
      const next = new Set(prev);
      if (next.has(permId)) next.delete(permId);
      else next.add(permId);
      return next;
    });
  };

  const handleSavePermissions = async () => {
    if (!selectedRole) return;
    setIsSavingPermissions(true);
    try {
      await apiClient.put(`/api/roles/${selectedRole.id}/`, {
        name: selectedRole.name,
        permission_ids: Array.from(selectedPermissionIds),
      });
      showToast('roles.messages.updateSuccess');
      await reloadRoles();
    } catch (err: unknown) {
      showToast(saveErrorKey(err), true);
    } finally {
      setIsSavingPermissions(false);
    }
  };

  // Thêm mới hoặc đổi tên nhóm quyền (modal nhỏ, không đụng tới ma trận quyền)
  const handleSaveRoleName = async (formData: { name: string }) => {
    setIsSubmittingRole(true);
    try {
      if (editingRole) {
        // Chỉ đổi tên - không gửi permission_ids để giữ nguyên quyền hiện có
        await apiClient.put(`/api/roles/${editingRole.id}/`, { name: formData.name });
        showToast('roles.messages.updateSuccess');
        await reloadRoles();
      } else {
        const created = await apiClient.post<Role>('/api/roles/', { name: formData.name });
        showToast('roles.messages.createSuccess');
        await reloadRoles();
        if (created?.id) {
          setSelectedRoleId(created.id);
          setSelectedPermissionIds(new Set(created.permission_ids || []));
        }
      }
    } finally {
      setIsSubmittingRole(false);
    }
  };

  const handleConfirmDeleteRole = async () => {
    if (!deletingRole) return;
    setIsDeletingRole(true);
    try {
      await apiClient.delete(`/api/roles/${deletingRole.id}/`);
      showToast('roles.messages.deleteSuccess');
      if (selectedRoleId === deletingRole.id) {
        setSelectedRoleId(null);
        setSelectedPermissionIds(new Set());
      }
      setDeletingRole(null);
      setDeleteErrorKey(null);
      await reloadRoles();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const apiErr = (err as { data?: { detail?: string } }).data;
        setDeleteErrorKey(apiErr?.detail || 'roles.messages.groupHasUsers');
      } else {
        setDeleteErrorKey('roles.messages.groupHasUsers');
      }
    } finally {
      setIsDeletingRole(false);
    }
  };

  return (
    <div className="overflow-x-hidden">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2.5 text-sm font-semibold animate-fade-in ${
            toastMessage.isError
              ? 'bg-danger text-white border border-danger-border'
              : 'bg-success text-white border border-success-border'
          }`}
        >
          <i className={`fa-solid ${toastMessage.isError ? 'fa-circle-xmark' : 'fa-circle-check'}`} />
          {t(toastMessage.textKey)}
        </div>
      )}

      <div className="grid h-[71vh] min-h-0 grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <div className="flex min-h-0 flex-col gap-4">
          <section className="shrink-0 bg-surface border border-border rounded-xl px-4 py-3 shadow-md">
            <h1 className="text-lg font-bold text-main flex items-center gap-2">
              <i className="fa-solid fa-user-shield text-primary" />
              {t('roles.title')}
            </h1>
            <p className="text-secondary text-xs leading-5 mt-1">{t('roles.desc')}</p>
          </section>

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
            <div className="flex shrink-0 items-center gap-1 border-b border-border bg-surface-elevated px-2 py-2">
            {canAdd && (
              <Button
                size="sm"
                variant="ghost"
                icon="fa-plus"
                onClick={() => {
                  // Tạo nhóm mới sẽ chuyển sang nhóm vừa tạo, nên hỏi trước nếu còn thay đổi chưa lưu
                  if (!confirmDiscardChanges()) return;
                  setEditingRole(null);
                  setIsRoleModalOpen(true);
                }}
              >
                {t('roles.actions.addGroup')}
              </Button>
            )}
            {canChange && (
              <Button
                size="sm"
                variant="ghost"
                icon="fa-pen"
                disabled={!selectedRole || isProtectedRole}
                onClick={() => {
                  if (selectedRole) {
                    setEditingRole(selectedRole);
                    setIsRoleModalOpen(true);
                  }
                }}
              >
                {t('roles.actions.edit')}
              </Button>
            )}
            {canDelete && (
              <Button
                size="sm"
                variant="ghost"
                icon="fa-xmark"
                disabled={!selectedRole || isProtectedRole}
                onClick={() => {
                  if (selectedRole) {
                    setDeletingRole(selectedRole);
                    setDeleteErrorKey(null);
                  }
                }}
              >
                {t('roles.actions.delete')}
              </Button>
            )}
          </div>

            <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">
              {isLoadingRoles ? (
                <div className="text-center py-10 text-secondary">
                  <i className="fa-solid fa-spinner fa-spin text-xl text-primary mb-2 block" />
                  {t('roles.table.loading')}
                </div>
              ) : fetchError ? (
                <div className="text-center py-10 px-3">
                  <i className="fa-solid fa-triangle-exclamation text-2xl text-danger mb-2 block" />
                  <p className="text-danger text-sm font-semibold mb-2">{t(fetchError)}</p>
                  {/* Không có quyền (403) thì thử lại cũng không được, nên chỉ hiện nút với lỗi tải/mạng */}
                  {fetchError !== 'roles.messages.permissionDenied' && (
                    <Button variant="outline" size="sm" icon="fa-rotate-right" onClick={() => {
                        setIsLoadingRoles(true);
                        setFetchError(null);
                        setRetryToken((n) => n + 1);
                      }}>
                      {t('roles.actions.retry')}
                    </Button>
                  )}
                </div>
              ) : roles.length === 0 ? (
                <div className="text-center py-10 text-secondary text-sm">
                  <i className="fa-solid fa-folder-open text-2xl text-muted mb-2 block" />
                  {t('roles.table.empty')}
                </div>
              ) : (
                roles.map((role) => (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => selectRole(role.id)}
                    className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left text-sm border-b border-border-subtle transition-colors cursor-pointer ${
                      selectedRoleId === role.id
                        ? 'bg-primary text-white font-semibold hover:bg-primary active:bg-primary'
                        : 'text-main hover:bg-surface-hover'
                    }`}
                  >
                    <i className={`fa-solid fa-users-gear ${selectedRoleId === role.id ? 'text-white' : 'text-primary'}`} />
                    {role.name}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Cột phải: Ma trận phân quyền của nhóm đang chọn */}
        <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
          {canChange && (
            <div className="flex shrink-0 items-center gap-2 border-b border-border bg-surface-elevated px-4 py-2">
              <Button
                size="sm"
                variant="primary"
                icon="fa-floppy-disk"
                disabled={!selectedRole}
                isLoading={isSavingPermissions}
                onClick={handleSavePermissions}
              >
                {t('roles.actions.save')}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                icon="fa-check-double"
                disabled={!selectedRole}
                onClick={() => setVisiblePermissions(true)}
              >
                {t('roles.actions.selectAll')}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                icon="fa-square"
                disabled={!selectedRole}
                onClick={() => setVisiblePermissions(false)}
              >
                {t('roles.actions.deselectAll')}
              </Button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-5">
            {!selectedRole ? (
              <div className="p-5 rounded-lg bg-success-subtle border border-success-border text-sm">
                <p className="font-bold text-main mb-2">{t('roles.matrixPlaceholderTitle')}</p>
                <ul className="list-disc list-inside space-y-1 text-secondary">
                  <li>{t('roles.matrixPlaceholderStep1')}</li>
                  <li>{t('roles.matrixPlaceholderStep2')}</li>
                </ul>
              </div>
            ) : (
              <PermissionMatrix
                permissions={permissions}
                selectedIds={selectedPermissionIds}
                onToggle={togglePermission}
                query={permissionQuery}
                onQueryChange={setPermissionQuery}
                readOnly={!canChange}
              />
            )}
          </div>
        </div>
      </div>

      {/* Modal Thêm/Sửa tên Nhóm quyền */}
      <RoleModal
        key={editingRole?.id ?? (isRoleModalOpen ? 'open-new-role' : 'closed-role')}
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
        onSubmit={handleSaveRoleName}
        initialData={editingRole}
        isLoading={isSubmittingRole}
      />

      {/* Xác nhận xóa Nhóm quyền */}
      <DeleteConfirmModal
        isOpen={!!deletingRole}
        onClose={() => {
          setDeletingRole(null);
          setDeleteErrorKey(null);
        }}
        onConfirm={handleConfirmDeleteRole}
        titleKey="roles.deleteConfirmTitle"
        descKey="roles.deleteConfirmDesc"
        name={deletingRole?.name}
        errorKey={deleteErrorKey}
        isLoading={isDeletingRole}
      />
    </div>
  );
}
