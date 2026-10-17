import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Employee, Position, GroupSimple, EmployeeCreatePayload, EmployeeUpdatePayload, EmployeeStatus } from '@app-types/employee';
import { Unit } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Select } from '@components/common/Select';
import { usePermissions } from '@lib/permissions';
import { ApiError } from '@lib/apiClient';

interface EmployeeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: EmployeeCreatePayload | EmployeeUpdatePayload) => Promise<{ temporary_password?: string | null } | void>;
  initialData?: Employee | null;
  units: Unit[];
  positions: Position[];
  groups: GroupSimple[];
  isLoading?: boolean;
}

export const EmployeeModal: React.FC<EmployeeModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  units,
  positions,
  groups,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const { can } = usePermissions();
  const isSelfEditOnly = Boolean(initialData && !can('change_full_cbnv'));

  const toIsoDateString = (dateStr?: string | null): string => {
    if (!dateStr) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) {
      const [d, m, y] = dateStr.split('/');
      return `${y}-${m}-${d}`;
    }
    return '';
  };

  const [formData, setFormData] = useState(() => {
    if (initialData) {
      return {
        ho_ten: initialData.ho_ten || '',
        email: initialData.email || '',
        username: initialData.username || '',
        password: '',
        ngay_sinh: initialData.is_birthday_masked
          ? ''
          : initialData.ngay_sinh_iso || toIsoDateString(initialData.ngay_sinh),
        don_vi_id: initialData.don_vi_id ? String(initialData.don_vi_id) : '',
        chuc_vu_id: initialData.chuc_vu_id ? String(initialData.chuc_vu_id) : '',
        chuc_danh: initialData.chuc_danh || '',
        sdt: initialData.sdt || '',
        nhom_quyen_ids: initialData.nhom_quyen ? initialData.nhom_quyen.map((g) => g.id) : [],
        trang_thai: initialData.trang_thai || 'LAM_VIEC',
        is_public: initialData.is_public ?? true,
        ghi_chu: initialData.ghi_chu || '',
        assignments: initialData.assignments
          ? initialData.assignments.map((a) => ({
              don_vi_id: String(a.don_vi_id),
              chuc_vu_id: String(a.chuc_vu_id),
              chuc_danh: a.chuc_danh || '',
            }))
          : [],
      };
    }
    return {
      ho_ten: '',
      email: '',
      username: '',
      password: '',
      ngay_sinh: '',
      don_vi_id: units.length > 0 ? String(units[0].id) : '',
      chuc_vu_id: positions.length > 0 ? String(positions[0].id) : '',
      chuc_danh: '',
      sdt: '',
      nhom_quyen_ids: [] as number[],
      trang_thai: 'LAM_VIEC' as const,
      is_public: true,
      ghi_chu: '',
      assignments: [] as Array<{ don_vi_id: string; chuc_vu_id: string; chuc_danh: string }>,
    };
  });

  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const handleAddAssignment = () => {
    const usedUnitIds = new Set([
      formData.don_vi_id,
      ...formData.assignments.map((a) => a.don_vi_id),
    ]);
    const availableUnit = units.find((u) => !usedUnitIds.has(String(u.id)));
    const defaultUnitId = availableUnit
      ? String(availableUnit.id)
      : (units[0] ? String(units[0].id) : '');
    const defaultPosId = positions[0] ? String(positions[0].id) : '';

    setFormData((prev) => ({
      ...prev,
      assignments: [
        ...prev.assignments,
        { don_vi_id: defaultUnitId, chuc_vu_id: defaultPosId, chuc_danh: '' },
      ],
    }));
  };

  const handleRemoveAssignment = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      assignments: prev.assignments.filter((_, i) => i !== index),
    }));
  };

  const handleAssignmentChange = (
    index: number,
    field: 'don_vi_id' | 'chuc_vu_id' | 'chuc_danh',
    value: string
  ) => {
    setFormData((prev) => {
      const next = [...prev.assignments];
      next[index] = { ...next[index], [field]: value };
      return { ...prev, assignments: next };
    });
    if (errorKey) setErrorKey(null);
  };

  if (!isOpen) return null;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    if (errorKey) setErrorKey(null);
  };

  const handleGroupToggle = (groupId: number) => {
    setFormData((prev) => {
      const exists = prev.nhom_quyen_ids.includes(groupId);
      return {
        ...prev,
        nhom_quyen_ids: exists
          ? prev.nhom_quyen_ids.filter((id) => id !== groupId)
          : [...prev.nhom_quyen_ids, groupId],
      };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ho_ten.trim()) {
      setErrorKey(t('employees.validation.nameRequired'));
      return;
    }
    if (!formData.email.trim()) {
      setErrorKey(t('employees.validation.emailRequired'));
      return;
    }
    if (!initialData && !formData.ngay_sinh) {
      setErrorKey(t('employees.validation.birthdayRequired'));
      return;
    }
    if (formData.sdt && !/^(0|\+84)[1-9][0-9]{7,9}$/.test(formData.sdt.replace(/\s+/g, ''))) {
      setErrorKey(t('employees.validation.phoneInvalid'));
      return;
    }

    try {
      let payload: EmployeeCreatePayload | EmployeeUpdatePayload;

      if (isSelfEditOnly) {
        // Chỉ gửi các trường thông tin cá nhân được phép đối với chủ tài khoản
        payload = {
          email: formData.email.trim(),
          sdt: formData.sdt.trim(),
          ngay_sinh: formData.ngay_sinh,
        };
      } else {
        // Validate assignments kiêm nhiệm
        if (formData.assignments.length > 0) {
          const pUnit = formData.don_vi_id;
          for (const a of formData.assignments) {
            if (!a.don_vi_id || !a.chuc_vu_id) {
              setErrorKey(t('employees.fields.duplicateAssignmentUnit'));
              return;
            }
            if (a.don_vi_id === pUnit) {
              setErrorKey(t('employees.fields.duplicateAssignmentUnit'));
              return;
            }
          }
          const seenUnits = new Set(formData.assignments.map((a) => a.don_vi_id));
          if (seenUnits.size !== formData.assignments.length) {
            setErrorKey(t('employees.fields.duplicateAssignmentUnit'));
            return;
          }
        }

        payload = {
          ho_ten: formData.ho_ten.trim(),
          email: formData.email.trim(),
          ngay_sinh: formData.ngay_sinh,
          don_vi_id: formData.don_vi_id ? Number(formData.don_vi_id) : null,
          chuc_vu_id: formData.chuc_vu_id ? Number(formData.chuc_vu_id) : null,
          chuc_danh: formData.chuc_danh.trim(),
          sdt: formData.sdt.trim(),
          nhom_quyen_ids: formData.nhom_quyen_ids,
          trang_thai: formData.trang_thai,
          is_public: formData.is_public,
          ghi_chu: formData.ghi_chu.trim(),
          assignments: formData.assignments.map((a) => ({
            don_vi_id: Number(a.don_vi_id),
            chuc_vu_id: Number(a.chuc_vu_id),
            chuc_danh: a.chuc_danh.trim(),
          })),
        };

        if (!initialData) {
          if (formData.username.trim()) {
            (payload as EmployeeCreatePayload).username = formData.username.trim();
          }
          if (formData.password.trim()) {
            (payload as EmployeeCreatePayload).password = formData.password.trim();
          }
        }
      }

      const res = await onSubmit(payload);
      if (res && res.temporary_password) {
        setCreatedPassword(res.temporary_password);
      } else {
        onClose();
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const detail = err.data?.detail || err.data?.error || err.data?.message;
        if (typeof detail === 'string') {
          setErrorKey(t(detail));
        } else if (err.data && typeof err.data === 'object') {
          const firstKey = Object.keys(err.data)[0];
          const val = (err.data as Record<string, unknown>)[firstKey];
          if (Array.isArray(val) && val.length > 0) {
            setErrorKey(t(String(val[0])));
          } else if (typeof val === 'string') {
            setErrorKey(t(val));
          } else {
            setErrorKey(t(err.message));
          }
        } else {
          setErrorKey(t(err.message));
        }
      } else if (err instanceof Error) {
        setErrorKey(t(err.message));
      } else {
        setErrorKey(t('employees.messages.saveError'));
      }
    }
  };

  const handleCopyPassword = () => {
    if (createdPassword) {
      navigator.clipboard.writeText(createdPassword);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-up">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-lg">
              <i className={initialData ? 'fa-solid fa-user-pen' : 'fa-solid fa-user-plus'} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-main">
                {initialData ? t('employees.modal.editTitle') : t('employees.modal.createTitle')}
              </h2>
              <p className="text-xs text-muted">
                {initialData ? t('employees.modal.editDesc') : t('employees.modal.createDesc')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-secondary hover:text-main p-2 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Modal Content */}
        {createdPassword ? (
          <div className="p-6 space-y-6">
            <div className="p-5 bg-success-subtle border border-success-border rounded-xl text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-success text-white flex items-center justify-center mx-auto text-xl">
                <i className="fa-solid fa-check" />
              </div>
              <h3 className="font-bold text-lg text-main">
                {t('employees.created.successTitle')}
              </h3>
              <p className="text-sm text-secondary">
                {t('employees.created.passwordNotice')}
              </p>
              <div className="flex items-center justify-center gap-3 pt-2">
                <span className="font-mono text-xl font-bold px-4 py-2 bg-surface border border-border rounded-lg text-main select-all tracking-wider">
                  {createdPassword}
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCopyPassword}
                  icon={isCopied ? 'fa-check' : 'fa-copy'}
                >
                  {isCopied ? t('employees.created.copied') : t('employees.created.copyPassword')}
                </Button>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="button" variant="primary" onClick={onClose}>
                {t('employees.actions.close')}
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
            {isSelfEditOnly && (
              <div className="p-3 text-xs bg-primary-subtle text-primary border border-primary-border rounded-lg flex items-center gap-2">
                <i className="fa-solid fa-circle-info text-sm shrink-0" />
                <span>{t('employees.hints.selfEditNotice')}</span>
              </div>
            )}

            {errorKey && (
              <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg flex items-center gap-2">
                <i className="fa-solid fa-circle-exclamation shrink-0" />
                <span>{errorKey}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Họ và tên */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.fullName')} <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  name="ho_ten"
                  value={formData.ho_ten}
                  onChange={handleChange}
                  disabled={isSelfEditOnly}
                  placeholder={t('employees.placeholders.fullName')}
                  className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                  required
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.email')} <span className="text-danger">*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder={t('employees.placeholders.email')}
                  className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  required
                />
              </div>

              {/* Username (chỉ khi tạo mới hoặc hiển thị readonly) */}
              {!initialData ? (
                <div>
                  <label className="block text-sm font-semibold text-secondary mb-1.5">
                    {t('employees.fields.username')}
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder={t('employees.placeholders.username')}
                    className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  />
                  <span className="text-xs text-muted block mt-1">
                    {t('employees.hints.usernameAuto')}
                  </span>
                </div>
              ) : null}

              {/* Password (khi tạo mới) */}
              {!initialData ? (
                <div>
                  <label className="block text-sm font-semibold text-secondary mb-1.5">
                    {t('employees.fields.initialPassword')}
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder={t('employees.placeholders.initialPassword')}
                    className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  />
                  <span className="text-xs text-muted block mt-1">
                    {t('employees.hints.passwordAuto')}
                  </span>
                </div>
              ) : null}

              {/* Ngày sinh */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.birthday')} {!initialData && <span className="text-danger">*</span>}
                </label>
                <input
                  type="date"
                  name="ngay_sinh"
                  value={formData.ngay_sinh}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  required={!initialData}
                />
              </div>

              {/* Số điện thoại */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.phone')}
                </label>
                <input
                  type="tel"
                  name="sdt"
                  value={formData.sdt}
                  onChange={handleChange}
                  placeholder={t('employees.placeholders.phone')}
                  className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>

              {/* Đơn vị / Phòng ban */}
              <div>
                <Select
                  label={t('employees.fields.unit')}
                  name="don_vi_id"
                  value={formData.don_vi_id}
                  disabled={isSelfEditOnly}
                  onChange={(val) => {
                    setFormData((prev) => ({ ...prev, don_vi_id: val }));
                    if (errorKey) setErrorKey(null);
                  }}
                  placeholder={t('employees.placeholders.selectUnit')}
                  leftIcon="fa-building"
                  clearable={!isSelfEditOnly}
                  searchable={!isSelfEditOnly}
                  options={units.map((u) => ({
                    value: String(u.id),
                    label: u.ten,
                    group: u.khoi_ten || undefined,
                  }))}
                />
              </div>

              {/* Chức vụ */}
              <div>
                <Select
                  label={t('employees.fields.position')}
                  name="chuc_vu_id"
                  value={formData.chuc_vu_id}
                  disabled={isSelfEditOnly}
                  onChange={(val) => {
                    setFormData((prev) => ({ ...prev, chuc_vu_id: val }));
                    if (errorKey) setErrorKey(null);
                  }}
                  placeholder={t('employees.placeholders.selectPosition')}
                  leftIcon="fa-id-badge"
                  clearable={!isSelfEditOnly}
                  options={positions.map((pos) => ({
                    value: String(pos.id),
                    label: pos.name,
                  }))}
                />
              </div>

              {/* Chức danh tự do */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.title')}
                </label>
                <input
                  type="text"
                  name="chuc_danh"
                  value={formData.chuc_danh}
                  onChange={handleChange}
                  disabled={isSelfEditOnly}
                  placeholder={t('employees.placeholders.title')}
                  className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              {/* Trạng thái làm việc */}
              <div>
                <Select
                  label={t('employees.fields.status')}
                  name="trang_thai"
                  value={formData.trang_thai}
                  disabled={isSelfEditOnly}
                  onChange={(val) => {
                    setFormData((prev) => ({ ...prev, trang_thai: val as EmployeeStatus }));
                    if (errorKey) setErrorKey(null);
                  }}
                  leftIcon="fa-circle-dot"
                  options={[
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
                <span className="text-xs text-muted block mt-1">
                  {t('employees.hints.statusNotice')}
                </span>
              </div>
            </div>

            {/* Phân công kiêm nhiệm (Đa phòng ban & chức vụ - Yêu cầu 3) */}
            {!isSelfEditOnly && (
              <div className="border border-border rounded-xl p-4 bg-surface-elevated space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <i className="fa-solid fa-network-wired text-primary" />
                    <span className="text-sm font-semibold text-main">
                      {t('employees.fields.concurrentAssignments')}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleAddAssignment}
                    icon="fa-plus"
                  >
                    {t('employees.fields.addAssignment')}
                  </Button>
                </div>

                {formData.assignments.length === 0 ? (
                  <p className="text-xs text-muted italic">
                    {t('employees.fields.noAssignments')}
                  </p>
                ) : (
                  <div className="space-y-3">
                    {formData.assignments.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 p-3 bg-surface border border-border rounded-lg"
                      >
                        <div className="flex-1">
                          <Select
                            name={`assign_unit_${idx}`}
                            value={item.don_vi_id}
                            onChange={(val) =>
                              handleAssignmentChange(idx, 'don_vi_id', val)
                            }
                            placeholder={t('employees.placeholders.selectUnit')}
                            options={units.map((u) => ({
                              value: String(u.id),
                              label: u.ten,
                              group: u.khoi_ten || undefined,
                            }))}
                          />
                        </div>
                        <div className="flex-1">
                          <Select
                            name={`assign_pos_${idx}`}
                            value={item.chuc_vu_id}
                            onChange={(val) =>
                              handleAssignmentChange(idx, 'chuc_vu_id', val)
                            }
                            placeholder={t('employees.placeholders.selectPosition')}
                            options={positions.map((pos) => ({
                              value: String(pos.id),
                              label: pos.name,
                            }))}
                          />
                        </div>
                        <div className="flex-1">
                          <input
                            type="text"
                            value={item.chuc_danh}
                            onChange={(e) =>
                              handleAssignmentChange(idx, 'chuc_danh', e.target.value)
                            }
                            placeholder={t('employees.fields.assignmentTitle')}
                            className="w-full px-3 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveAssignment(idx)}
                          className="p-2 text-danger hover:bg-danger-subtle rounded-lg transition-colors shrink-0 self-end sm:self-center"
                          title={t('employees.fields.removeAssignment')}
                        >
                          <i className="fa-solid fa-trash-can" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Nhóm quyền (RBAC) */}
            {groups.length > 0 && (
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.groups')}
                </label>
                <div className={`grid grid-cols-2 sm:grid-cols-3 gap-2 p-3 bg-surface-elevated border border-border rounded-lg max-h-36 overflow-y-auto ${isSelfEditOnly ? 'opacity-60 cursor-not-allowed' : ''}`}>
                  {groups.map((group) => {
                    const isChecked = formData.nhom_quyen_ids.includes(group.id);
                    return (
                      <label
                        key={group.id}
                        className={`flex items-center gap-2 text-xs text-main select-none transition-colors ${isSelfEditOnly ? 'cursor-not-allowed' : 'cursor-pointer hover:text-primary'}`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={isSelfEditOnly}
                          onChange={() => handleGroupToggle(group.id)}
                          className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
                        />
                        <span>{group.name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Ghi chú */}
            <div>
              <label className="block text-sm font-semibold text-secondary mb-1.5">
                {t('employees.fields.notes')}
              </label>
              <textarea
                name="ghi_chu"
                rows={2}
                value={formData.ghi_chu}
                onChange={handleChange}
                disabled={isSelfEditOnly}
                placeholder={t('employees.placeholders.notes')}
                className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none disabled:opacity-60 disabled:cursor-not-allowed"
              />
            </div>

            {/* Công khai */}
            <div className={`flex items-start gap-3 p-3 bg-surface-elevated border border-border rounded-lg ${isSelfEditOnly ? 'opacity-60 cursor-not-allowed' : ''}`}>
              <input
                type="checkbox"
                id="is_public_emp"
                name="is_public"
                checked={formData.is_public}
                disabled={isSelfEditOnly}
                onChange={handleChange}
                className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed"
              />
              <label htmlFor="is_public_emp" className={`text-sm select-none ${isSelfEditOnly ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                <span className="font-semibold text-main block">{t('employees.fields.isPublicLabel')}</span>
                <span className="text-muted text-xs block">{t('employees.fields.isPublicHelp')}</span>
              </label>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
                {t('employees.actions.cancel')}
              </Button>
              <Button type="submit" variant="primary" isLoading={isLoading}>
                {initialData ? t('employees.actions.save') : t('employees.actions.create')}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
