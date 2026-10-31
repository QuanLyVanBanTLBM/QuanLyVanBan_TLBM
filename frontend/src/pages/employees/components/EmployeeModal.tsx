import React, { useState, useRef } from 'react';
import { useTranslation } from '@i18n/translate';
import { formatGroupName } from '@lib/roleUtils';
import { Employee, Position, GroupSimple, EmployeeCreatePayload, EmployeeUpdatePayload, EmployeeStatus } from '@app-types/employee';
import { Unit } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Select } from '@components/common/Select';
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
  isAdmin?: boolean;
  onChangePassword?: (
    employeeId: number,
    newPassword: string,
    confirmPassword: string,
    reasonCode: string,
    reasonDetail?: string
  ) => Promise<void>;
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
  isAdmin = false,
  onChangePassword,
}) => {
  const { t, currentLang } = useTranslation();
  const formRef = useRef<HTMLFormElement>(null);
  const birthdayDateInputRef = useRef<HTMLInputElement>(null);
  const birthdayDateButtonRef = useRef<HTMLButtonElement>(null);
  const isSelfEditOnly = Boolean(initialData && !isAdmin);

  const toDisplayDateString = (dateStr?: string | null): string => {
    if (!dateStr) return '';
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) return dateStr;
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      const [y, m, d] = dateStr.split('-');
      return `${d}/${m}/${y}`;
    }
    return '';
  };

  const parseToIso = (dateStr: string): string | null => {
    const trimmed = dateStr.trim();
    if (!trimmed) return null;
    const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(trimmed);
    if (match) {
      const d = match[1].padStart(2, '0');
      const m = match[2].padStart(2, '0');
      const y = match[3];
      const day = parseInt(d, 10);
      const month = parseInt(m, 10);
      const year = parseInt(y, 10);
      if (month < 1 || month > 12 || day < 1 || day > 31) return null;
      const dt = new Date(year, month - 1, day);
      if (dt.getFullYear() !== year || dt.getMonth() !== month - 1 || dt.getDate() !== day) return null;
      return `${y}-${m}-${d}`;
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      return trimmed;
    }
    return null;
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
          : toDisplayDateString(initialData.ngay_sinh_iso || initialData.ngay_sinh),
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
      don_vi_id: '',
      chuc_vu_id: '',
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
  const [copyFailed, setCopyFailed] = useState<boolean>(false);
  const [isPasswordFormOpen, setIsPasswordFormOpen] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordResetReason, setPasswordResetReason] = useState('');
  const [passwordResetReasonDetail, setPasswordResetReasonDetail] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showInitialPassword, setShowInitialPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false);

  const handleAddAssignment = () => {
    const usedUnitIds = new Set([
      formData.don_vi_id,
      ...formData.assignments.map((a) => a.don_vi_id),
    ]);
    const availableUnit = units.find((u) => !usedUnitIds.has(String(u.id)));
    const defaultUnitId = availableUnit
      ? String(availableUnit.id)
      : (units[0] ? String(units[0].id) : '');
    const defaultPosId = '';

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

  const openBirthdayPicker = () => {
    const input = birthdayDateInputRef.current;
    if (!input) return;
    const pickerInput = input as HTMLInputElement & { showPicker?: () => void };
    if (pickerInput.showPicker) {
      pickerInput.showPicker();
    } else {
      input.click();
    }
  };

  const handleAdminPasswordChange = async () => {
    if (!initialData || !isAdmin || !onChangePassword) return;
    setPasswordError(null);
    if (!newPassword || !confirmNewPassword) {
      setPasswordError(t('employees.validation.passwordRequired'));
      return;
    }
    if (!passwordResetReason) {
      setPasswordError(t('employees.validation.passwordReasonRequired'));
      return;
    }
    if (passwordResetReason === 'OTHER' && !passwordResetReasonDetail.trim()) {
      setPasswordError(t('employees.validation.passwordReasonDetailRequired'));
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordError(t('employees.messages.passwordMismatch'));
      return;
    }

    setIsChangingPassword(true);
    try {
      await onChangePassword(
        initialData.id,
        newPassword,
        confirmNewPassword,
        passwordResetReason,
        passwordResetReason === 'OTHER' ? passwordResetReasonDetail.trim() : undefined
      );
      setNewPassword('');
      setConfirmNewPassword('');
      setPasswordResetReason('');
      setPasswordResetReasonDetail('');
      setIsPasswordFormOpen(false);
    } catch (error: unknown) {
      let rawError: unknown;
      if (error instanceof ApiError) {
        rawError = error.data?.detail || error.data?.error || error.data?.message;
        if (!rawError && error.data && typeof error.data === 'object') {
          const firstValue = Object.values(error.data).find((value) => value !== undefined);
          rawError = Array.isArray(firstValue) ? firstValue[0] : firstValue;
        }
      }
      const message = typeof rawError === 'string'
        ? resolveErrorMessage(rawError)
        : t('employees.messages.passwordChangeError');
      setPasswordError(message);
    } finally {
      setIsChangingPassword(false);
    }
  };

  const resolveErrorMessage = (rawError: string): string => {
    if (rawError.includes('emailExists')) {
      return t('employees.messages.emailExists', { value: formData.email });
    }
    if (rawError.includes('usernameExists')) {
      return t('employees.messages.usernameExists', { value: formData.username || '' });
    }
    if (rawError.includes('duplicateAssignmentUnit')) {
      return t('employees.fields.duplicateAssignmentUnit');
    }
    if (rawError.includes('invalidBirthday')) {
      return t('employees.import.errors.invalidBirthday', { value: formData.ngay_sinh });
    }
    return t(rawError);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ho_ten.trim()) {
      const msg = t('employees.validation.nameRequired');
      setErrorKey(msg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (!formData.email.trim()) {
      const msg = t('employees.validation.emailRequired');
      setErrorKey(msg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }
    if (!initialData && !formData.don_vi_id) {
      const msg = t('employees.import.errors.unitRequired');
      setErrorKey(msg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }

    let isoBirthday: string | null = null;
    if (formData.ngay_sinh) {
      isoBirthday = parseToIso(formData.ngay_sinh);
      if (!isoBirthday) {
        const msg = t('employees.import.errors.invalidBirthday', { value: formData.ngay_sinh });
        setErrorKey(msg);
        formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
        return;
      }
    } else if (!initialData) {
      const msg = t('employees.validation.birthdayRequired');
      setErrorKey(msg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }

    if (formData.sdt && !/^(0|\+84)[1-9][0-9]{7,9}$/.test(formData.sdt.replace(/\s+/g, ''))) {
      const msg = t('employees.validation.phoneInvalid');
      setErrorKey(msg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
      return;
    }


    try {
      let payload: EmployeeCreatePayload | EmployeeUpdatePayload;

      if (isSelfEditOnly) {
        // Chỉ gửi các trường thông tin cá nhân được phép đối với chủ tài khoản
        payload = {
          email: formData.email.trim(),
          sdt: formData.sdt.trim(),
          ngay_sinh: isoBirthday || formData.ngay_sinh,
        };
      } else {
        if (!initialData && !formData.chuc_vu_id) {
          const msg = t('employees.validation.positionRequired');
          setErrorKey(msg);
          formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
          return;
        }

        // Validate assignments kiêm nhiệm
        if (formData.assignments.length > 0) {
          const pUnit = formData.don_vi_id;
          for (const a of formData.assignments) {
            if (!a.don_vi_id) {
              const msg = t('employees.fields.duplicateAssignmentUnit');
              setErrorKey(msg);
              formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
              return;
            }
            if (!a.chuc_vu_id) {
              const msg = t('employees.validation.positionRequired');
              setErrorKey(msg);
              formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
              return;
            }
            if (a.don_vi_id === pUnit) {
              const msg = t('employees.fields.duplicateAssignmentUnit');
              setErrorKey(msg);
              formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
              return;
            }
          }
          const seenUnits = new Set(formData.assignments.map((a) => a.don_vi_id));
          if (seenUnits.size !== formData.assignments.length) {
            const msg = t('employees.fields.duplicateAssignmentUnit');
            setErrorKey(msg);
            formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
            return;
          }
        }

        payload = {
          ho_ten: formData.ho_ten.trim(),
          email: formData.email.trim(),
          ngay_sinh: isoBirthday || formData.ngay_sinh,
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
      let resolvedMsg = t('employees.messages.saveError');
      if (err instanceof ApiError) {
        const detail = err.data?.detail || err.data?.error || err.data?.message;
        if (typeof detail === 'string') {
          resolvedMsg = resolveErrorMessage(detail);
        } else if (err.data && typeof err.data === 'object') {
          const firstKey = Object.keys(err.data)[0];
          const val = (err.data as Record<string, unknown>)[firstKey];
          if (Array.isArray(val) && val.length > 0) {
            resolvedMsg = resolveErrorMessage(String(val[0]));
          } else if (typeof val === 'string') {
            resolvedMsg = resolveErrorMessage(val);
          } else {
            resolvedMsg = resolveErrorMessage(err.message);
          }
        } else {
          resolvedMsg = resolveErrorMessage(err.message);
        }
      } else if (err instanceof Error) {
        resolvedMsg = resolveErrorMessage(err.message);
      }

      setErrorKey(resolvedMsg);
      formRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' });
    }
  };

  const copyWithFallback = (value: string): boolean => {
    const temporaryInput = document.createElement('textarea');
    temporaryInput.value = value;
    temporaryInput.setAttribute('readonly', '');
    temporaryInput.style.position = 'fixed';
    temporaryInput.style.opacity = '0';
    document.body.appendChild(temporaryInput);
    try {
      temporaryInput.select();
      return document.execCommand('copy');
    } finally {
      temporaryInput.remove();
    }
  };

  const handleCopyPassword = async () => {
    if (!createdPassword) return;

    setCopyFailed(false);
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(createdPassword);
      } else if (!copyWithFallback(createdPassword)) {
        throw new Error('clipboardCopyFailed');
      }
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 2500);
    } catch {
      try {
        if (!copyWithFallback(createdPassword)) throw new Error('clipboardCopyFailed');
        setIsCopied(true);
        window.setTimeout(() => setIsCopied(false), 2500);
      } catch {
        setIsCopied(false);
        setCopyFailed(true);
      }
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
            <div className="p-6 bg-success-subtle border border-success-border rounded-xl text-center space-y-5">
              <div className="w-14 h-14 rounded-full bg-success text-white flex items-center justify-center mx-auto text-2xl shadow-sm">
                <i className="fa-solid fa-check" />
              </div>
              <h3 className="font-bold text-xl text-main">
                {t('employees.created.successTitle')}
              </h3>
              <p className="text-sm text-secondary">
                {t('employees.created.passwordNotice')}
              </p>

              {/* Cụm hiển thị mật khẩu: click vào mật khẩu hoặc bấm icon copy đều tự động sao chép */}
              <div className="flex flex-col items-center justify-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleCopyPassword}
                  title={isCopied ? t('employees.created.copied') : t('employees.created.copyPassword')}
                  aria-label={isCopied ? t('employees.created.copied') : t('employees.created.copyPassword')}
                  className="group relative inline-flex items-center gap-3 px-5 py-2.5 bg-surface border-2 border-border hover:border-primary/60 rounded-xl cursor-pointer shadow-sm hover:shadow transition-all duration-200 select-none active:scale-[0.98]"
                >
                  <span className="font-mono text-xl font-bold tracking-widest text-main group-hover:text-primary transition-colors">
                    {createdPassword}
                  </span>
                  <span
                    className={`w-9 h-9 rounded-lg transition-colors flex items-center justify-center shrink-0 ${
                      isCopied
                        ? 'bg-success text-white'
                        : 'bg-surface-elevated text-secondary group-hover:text-primary group-hover:bg-primary-subtle'
                    }`}
                  >
                    <i className={`fa-solid ${isCopied ? 'fa-check' : 'fa-copy'} text-base`} />
                  </span>

                  {isCopied && (
                    <span className="absolute -top-9 left-1/2 -translate-x-1/2 px-2.5 py-1 text-xs font-semibold bg-success text-white rounded-md shadow-md animate-fade-in pointer-events-none whitespace-nowrap">
                      {t('employees.created.copied')}
                    </span>
                  )}
                </button>
                <span className="text-xs text-secondary/80 flex items-center gap-1.5">
                  <i className="fa-regular fa-hand-pointer text-[11px]" />
                  {t('employees.created.clickToCopy')}
                </span>
                {copyFailed && (
                  <span role="alert" className="text-xs text-danger">
                    {t('employees.created.copyFailed')}
                  </span>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="button" variant="primary" onClick={onClose}>
                {t('employees.actions.close')}
              </Button>
            </div>
          </div>
        ) : (
          <form ref={formRef} onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
            {isSelfEditOnly && (
              <div className="p-3 text-xs bg-primary-subtle text-primary border border-primary-border rounded-lg flex items-center gap-2">
                <i className="fa-solid fa-circle-info text-sm shrink-0" />
                <span>{t('employees.hints.selfEditNotice')}</span>
              </div>
            )}

            {initialData && isAdmin && onChangePassword && (
              <section className="p-3 bg-surface-elevated border border-border rounded-lg space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-main">{t('employees.passwordChange.title')}</h3>
                    <p className="text-xs text-muted">{t('employees.passwordChange.help')}</p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      const nextOpen = !isPasswordFormOpen;
                      setIsPasswordFormOpen(nextOpen);
                      setPasswordError(null);
                      if (!nextOpen) {
                        setNewPassword('');
                        setConfirmNewPassword('');
                        setPasswordResetReason('');
                        setPasswordResetReasonDetail('');
                      }
                    }}
                  >
                    {isPasswordFormOpen ? t('employees.actions.cancel') : t('employees.actions.changePassword')}
                  </Button>
                </div>
                {isPasswordFormOpen && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="md:col-span-2">
                      <Select
                        label={t('employees.passwordChange.reason')}
                        name="password-reset-reason"
                        value={passwordResetReason}
                        required
                        onChange={(reason) => {
                          setPasswordResetReason(reason);
                          if (reason !== 'OTHER') setPasswordResetReasonDetail('');
                          setPasswordError(null);
                        }}
                        placeholder={t('employees.passwordChange.reasonPlaceholder')}
                        ariaLabel={t('employees.passwordChange.reason')}
                        searchable={false}
                        options={[
                          { value: 'FORGOT_PASSWORD', label: t('employees.passwordChange.reasonForgotPassword') },
                          { value: 'COMPROMISED', label: t('employees.passwordChange.reasonCompromised') },
                          { value: 'LOST_ACCESS', label: t('employees.passwordChange.reasonLostAccess') },
                          { value: 'OTHER', label: t('employees.passwordChange.reasonOther') },
                        ]}
                      />
                    </div>
                    {passwordResetReason === 'OTHER' && (
                      <label className="block text-sm font-medium text-secondary md:col-span-2">
                        {t('employees.passwordChange.reasonDetail')}
                        <textarea
                          required
                          maxLength={500}
                          value={passwordResetReasonDetail}
                          onChange={(event) => {
                            setPasswordResetReasonDetail(event.target.value);
                            setPasswordError(null);
                          }}
                          placeholder={t('employees.passwordChange.reasonDetailPlaceholder')}
                          rows={2}
                          className="mt-1 w-full px-3 py-2 text-sm bg-surface border border-border rounded-lg text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                        />
                      </label>
                    )}
                    <label className="block text-sm font-medium text-secondary">
                      {t('employees.passwordChange.newPassword')}
                      <span className="relative mt-1 block">
                        <input
                          type={showNewPassword ? 'text' : 'password'}
                          autoComplete="new-password"
                          value={newPassword}
                          onChange={(event) => setNewPassword(event.target.value)}
                          className="employee-password-input w-full px-3 py-2 pr-10 text-sm bg-surface border border-border rounded-lg text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                        />
                        <button
                          type="button"
                          aria-label={t(showNewPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                          title={t(showNewPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                          onClick={() => setShowNewPassword((visible) => !visible)}
                          className="absolute inset-y-0 right-2 inline-flex items-center px-1 text-muted hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                        >
                          <i aria-hidden="true" className={`fa-solid ${showNewPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
                        </button>
                      </span>
                    </label>
                    <label className="block text-sm font-medium text-secondary">
                      {t('employees.passwordChange.confirmPassword')}
                      <span className="relative mt-1 block">
                        <input
                          type={showConfirmNewPassword ? 'text' : 'password'}
                          autoComplete="new-password"
                          value={confirmNewPassword}
                          onChange={(event) => setConfirmNewPassword(event.target.value)}
                          className="employee-password-input w-full px-3 py-2 pr-10 text-sm bg-surface border border-border rounded-lg text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                        />
                        <button
                          type="button"
                          aria-label={t(showConfirmNewPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                          title={t(showConfirmNewPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                          onClick={() => setShowConfirmNewPassword((visible) => !visible)}
                          className="absolute inset-y-0 right-2 inline-flex items-center px-1 text-muted hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                        >
                          <i aria-hidden="true" className={`fa-solid ${showConfirmNewPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
                        </button>
                      </span>
                    </label>
                    {passwordError && (
                      <p role="alert" className="md:col-span-2 text-sm text-danger">{passwordError}</p>
                    )}
                    <div className="md:col-span-2 flex justify-end">
                      <Button
                        type="button"
                        variant="primary"
                        isLoading={isChangingPassword}
                        onClick={handleAdminPasswordChange}
                      >
                        {t('employees.passwordChange.submit')}
                      </Button>
                    </div>
                  </div>
                )}
              </section>
            )}

            {errorKey && (
              <div className="p-4 text-sm text-danger bg-danger-subtle border-2 border-danger rounded-xl flex items-start gap-3 shadow-md animate-shake">
                <div className="w-8 h-8 rounded-full bg-danger text-white flex items-center justify-center shrink-0 mt-0.5 text-base">
                  <i className="fa-solid fa-triangle-exclamation" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-danger text-sm mb-0.5">
                    {t('employees.messages.saveError')}
                  </h4>
                  <p className="text-danger leading-relaxed font-semibold">
                    {errorKey}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorKey(null)}
                  className="text-danger hover:opacity-75 transition-opacity p-1 text-base"
                  title={t('employees.actions.close')}
                >
                  <i className="fa-solid fa-xmark" />
                </button>
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
                  <span className="relative block">
                    <input
                      type={showInitialPassword ? 'text' : 'password'}
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={t('employees.placeholders.initialPassword')}
                      className="employee-password-input w-full px-3.5 py-2 pr-10 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    />
                    <button
                      type="button"
                      aria-label={t(showInitialPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                      title={t(showInitialPassword ? 'employees.passwordChange.hidePassword' : 'employees.passwordChange.showPassword')}
                      onClick={() => setShowInitialPassword((visible) => !visible)}
                      className="absolute inset-y-0 right-2 inline-flex items-center px-1 text-muted hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                    >
                      <i aria-hidden="true" className={`fa-solid ${showInitialPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
                    </button>
                  </span>
                  <span className="text-xs text-muted block mt-1">
                    {t('employees.hints.passwordAuto')}
                  </span>
                </div>
              ) : null}

              {/* Ngày sinh (Định dạng DD/MM/YYYY) */}
              <div>
                <label className="block text-sm font-semibold text-secondary mb-1.5">
                  {t('employees.fields.birthday')} {!initialData && <span className="text-danger">*</span>}
                </label>
                <div className="relative flex items-center">
                  <input
                    type="text"
                    name="ngay_sinh"
                    value={formData.ngay_sinh}
                    onChange={(e) => {
                      let val = e.target.value.replace(/[^\d/]/g, '');
                      if (/^\d{2}$/.test(val) && !formData.ngay_sinh.endsWith('/')) {
                        val = val + '/';
                      } else if (/^\d{2}\/\d{2}$/.test(val) && !formData.ngay_sinh.endsWith('/')) {
                        val = val + '/';
                      }
                      if (val.length <= 10) {
                        setFormData((prev) => ({ ...prev, ngay_sinh: val }));
                      }
                      if (errorKey) setErrorKey(null);
                    }}
                    placeholder="DD/MM/YYYY"
                    maxLength={10}
                    className="w-full pl-3.5 pr-10 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    required={!initialData}
                  />
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex w-full items-center justify-end text-muted">
                    <button
                      ref={birthdayDateButtonRef}
                      type="button"
                      aria-label={t('employees.fields.birthday')}
                      title={t('employees.fields.birthday')}
                      onClick={openBirthdayPicker}
                      className="pointer-events-auto z-10 mr-2.5 inline-flex h-8 w-8 items-center justify-center rounded-md hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      <i aria-hidden="true" className="fa-solid fa-calendar-days text-sm" />
                    </button>
                    <input
                      ref={birthdayDateInputRef}
                      type="date"
                      value={parseToIso(formData.ngay_sinh) || ''}
                      onChange={(e) => {
                        const iso = e.target.value;
                        if (iso) {
                          const [y, m, d] = iso.split('-');
                          setFormData((prev) => ({ ...prev, ngay_sinh: `${d}/${m}/${y}` }));
                          if (errorKey) setErrorKey(null);
                          birthdayDateButtonRef.current?.focus();
                        }
                      }}
                      tabIndex={-1}
                      aria-hidden="true"
                      className="pointer-events-none absolute left-0 top-1/2 h-8 w-8 -translate-y-1/2 opacity-0 md:left-auto md:right-0"
                    />
                  </div>
                </div>
                <span className="text-xs text-muted block mt-1">{t('employees.hints.birthdayFormat')}</span>
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
                  required={!initialData && !isSelfEditOnly}
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
                  required={!isSelfEditOnly}
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

              {/* Chức danh */}
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
                        <span>{formatGroupName(group.name, currentLang)}</span>
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
