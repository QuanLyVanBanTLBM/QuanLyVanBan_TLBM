import React, { useEffect, useMemo, useState } from 'react';
import { t, useTranslation } from '@i18n/translate';
import { API_BASE_URL, ApiError, authHeaders, toMessage } from '../api/client';
import { createTask, getTask, updateTask } from '../api/tasks';
import { Attachment, TaskDetail, TaskFormValues } from '../types/task';
import DateInput, { todayIso } from './DateInput';
import EmployeeMultiSelect from './EmployeeMultiSelect';
import EmployeeSelect from './EmployeeSelect';
import FilePicker, { fileIconClass, formatFileSize } from './FilePicker';
import WorkAlert from './WorkAlert';
import WorkModal from './WorkModal';

/**
 * Form "Cập nhật thông tin công việc", dùng chung cho Thêm (taskId = null) và Sửa.
 * Kiểm tra dữ liệu ngay tại trình duyệt theo đúng quy tắc của backend; lỗi backend trả về
 * (nếu có) vẫn được hiện dưới đúng trường.
 */

type FieldName =
  | 'title'
  | 'createdDate'
  | 'dueDate'
  | 'requirement'
  | 'hostId'
  | 'directorIds'
  | 'participantIds'
  | 'attachments';

type FieldErrors = Partial<Record<FieldName, string>>;

const FIELD_NAMES: FieldName[] = [
  'title',
  'createdDate',
  'dueDate',
  'requirement',
  'hostId',
  'directorIds',
  'participantIds',
  'attachments',
];

interface TaskFormModalProps {
  open: boolean;
  /** null khi thêm mới. */
  taskId: number | null;
  onClose: () => void;
  onSaved: (task: TaskDetail, mode: 'create' | 'edit') => void;
}

interface DonViOption {
  id: number;
  ten: string;
}

async function fetchAllDonVi(): Promise<DonViOption[]> {
  const res = await fetch(`${API_BASE_URL}/organizations/units/?all=true`, {
    headers: authHeaders(),
  });
  if (!res.ok) return [];
  const data = await res.json();
  const items: Array<{ id: number; ten?: string; name?: string }> = Array.isArray(data)
    ? data
    : data?.results || [];
  return items
    .map((item) => ({ id: item.id, ten: (item.ten || item.name || '').trim() }))
    .filter((item) => item.ten)
    .sort((a, b) => a.ten.localeCompare(b.ten, 'vi'));
}

function emptyValues(): TaskFormValues {
  return {
    title: '',
    createdDate: todayIso(),
    dueDate: '',
    requirement: '',
    hostId: null,
    directorIds: [],
    participantIds: [],
    isPublic: true,
    donViIds: [],
    attachments: [],
    removeAttachmentIds: [],
  };
}

function validate(values: TaskFormValues, isEdit: boolean): FieldErrors {
  const errors: FieldErrors = {};
  const today = todayIso();

  if (!values.title.trim()) errors.title = t('work.taskForm.errTitle');
  if (!values.requirement.trim()) errors.requirement = t('work.taskForm.errRequirement');

  if (!values.createdDate) {
    errors.createdDate = t('work.taskForm.errCreatedDate');
  } else if (!isEdit && values.createdDate < today) {
    errors.createdDate = t('work.taskForm.errCreatedDatePast');
  }

  if (!values.dueDate) {
    errors.dueDate = t('work.taskForm.errDueDate');
  } else if (values.createdDate && values.dueDate < values.createdDate) {
    errors.dueDate = t('work.taskForm.errDueDateBeforeCreated');
  } else if (isEdit && values.dueDate < today) {
    errors.dueDate = t('work.taskForm.errDueDatePast');
  }

  if (values.hostId === null) errors.hostId = t('work.taskForm.errHost');
  if (!values.directorIds.length) errors.directorIds = t('work.taskForm.errDirectors');
  if (!values.participantIds.length) {
    errors.participantIds = t('work.taskForm.errParticipants');
  }

  const overlap = values.participantIds.some(
    (id) => id === values.hostId || values.directorIds.includes(id),
  ) || values.directorIds.includes(values.hostId ?? -1);
  if (overlap) {
    errors.participantIds = t('work.taskForm.errRoleOverlap');
  }

  return errors;
}

function toFormValues(task: TaskDetail): TaskFormValues {
  return {
    title: task.title,
    createdDate: task.createdDate,
    dueDate: task.dueDate,
    requirement: task.requirement,
    hostId: task.host ? task.host.id : null,
    directorIds: task.directors.map((person) => person.id),
    participantIds: task.participants.map((person) => person.id),
    isPublic: task.isPublic,
    donViIds: task.donViIds,
    attachments: [],
    removeAttachmentIds: [],
  };
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '6px',
  fontSize: '0.82rem',
  fontWeight: 700,
  color: 'var(--text-main)',
};

function textAreaStyle(invalid: boolean): React.CSSProperties {
  return {
    width: '100%',
    minHeight: '96px',
    padding: '10px 12px',
    borderRadius: 'var(--radius-md)',
    border: `1px solid ${invalid ? 'var(--color-danger)' : 'var(--border-subtle)'}`,
    background: 'var(--bg-surface)',
    color: 'var(--text-main)',
    fontSize: '0.88rem',
    fontFamily: 'inherit',
    lineHeight: 1.6,
    resize: 'vertical',
    outline: 'none',
  };
}

function Field({
  label,
  required,
  hint,
  error,
  htmlFor,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} style={labelStyle}>
        {label}
        {required && <span style={{ color: 'var(--color-danger)' }}> *</span>}
      </label>
      {hint && (
        <div style={{ marginTop: '-2px', marginBottom: '6px', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
          {hint}
        </div>
      )}
      {children}
      {error && (
        <div style={{ marginTop: '4px', fontSize: '0.76rem', color: 'var(--color-danger)', lineHeight: 1.5 }}>
          {error}
        </div>
      )}
    </div>
  );
}

export default function TaskFormModal({ open, taskId, onClose, onSaved }: TaskFormModalProps) {
  const { t: tr } = useTranslation();
  const isEdit = taskId !== null;
  const [values, setValues] = useState<TaskFormValues>(emptyValues);
  const [existingFiles, setExistingFiles] = useState<Attachment[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState('');
  const [lockedReason, setLockedReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [donViList, setDonViList] = useState<DonViOption[]>([]);
  const [donViSearch, setDonViSearch] = useState('');

  useEffect(() => {
    fetchAllDonVi().then(setDonViList).catch(() => {});
  }, []);

  const filteredDonVi = useMemo(() => {
    if (!donViSearch.trim()) return donViList;
    const q = donViSearch.toLowerCase();
    return donViList.filter((d) => d.ten.toLowerCase().includes(q));
  }, [donViList, donViSearch]);

  useEffect(() => {
    if (!open) return undefined;

    setErrors({});
    setFormError('');
    setLockedReason('');
    setExistingFiles([]);

    if (taskId === null) {
      setValues(emptyValues());
      return undefined;
    }

    const controller = new AbortController();
    setLoading(true);
    getTask(taskId, controller.signal)
      .then((task) => {
        setValues(toFormValues(task));
        setExistingFiles(task.attachments);
        if (!task.permissions.canEdit) {
          setLockedReason(
            t('work.taskForm.lockedReason', { status: task.statusLabel }),
          );
        }
      })
      .catch((cause) => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return;
        setFormError(toMessage(cause));
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [open, taskId]);

  const update = <K extends keyof TaskFormValues>(key: K, next: TaskFormValues[K]) => {
    setValues((previous) => ({ ...previous, [key]: next }));
    setErrors((previous) => ({ ...previous, [key]: undefined }));
  };

  const toggleRemoveFile = (attachmentId: number) => {
    setValues((previous) => ({
      ...previous,
      removeAttachmentIds: previous.removeAttachmentIds.includes(attachmentId)
        ? previous.removeAttachmentIds.filter((id) => id !== attachmentId)
        : [...previous.removeAttachmentIds, attachmentId],
    }));
  };

  const handleSubmit = async () => {
    const found = validate(values, isEdit);
    const count = Object.values(found).filter(Boolean).length;
    if (count) {
      setErrors(found);
      setFormError(tr('work.taskForm.validationCount', { count: String(count) }));
      return;
    }

    setSaving(true);
    setFormError('');
    try {
      const saved = isEdit ? await updateTask(taskId as number, values) : await createTask(values);
      onSaved(saved, isEdit ? 'edit' : 'create');
    } catch (cause) {
      if (cause instanceof ApiError) {
        const mapped: FieldErrors = {};
        FIELD_NAMES.forEach((name) => {
          const message = cause.errorFor(name);
          if (message) mapped[name] = message;
        });
        setErrors(mapped);
        const otherMessage = cause.errorFor('non_field_errors') || cause.errorFor('detail') || cause.errorFor('removeAttachmentIds');
        setFormError(
          otherMessage ||
            (Object.keys(mapped).length
              ? tr('work.taskForm.serverValidation')
              : cause.message),
        );
      } else {
        setFormError(toMessage(cause));
      }
    } finally {
      setSaving(false);
    }
  };

  const today = todayIso();
  const dueMin = isEdit
    ? [values.createdDate, today].filter(Boolean).sort().pop()
    : values.createdDate || today;
  const disabled = loading || saving || Boolean(lockedReason);

  return (
    <WorkModal
      open={open}
      title={tr('work.taskForm.modalTitle')}
      subtitle={isEdit ? tr('work.taskForm.subtitleEdit') : tr('work.taskForm.subtitleCreate')}
      onClose={onClose}
      width="lg"
      busy={saving}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '9px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontWeight: 600,
              fontSize: '0.86rem',
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >
            {tr('work.taskForm.cancelButton')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 18px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: '0.86rem',
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.6 : 1,
            }}
          >
            <i className={saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'} />
            {saving ? tr('work.common.saving') : tr('work.taskForm.saveButton')}
          </button>
        </>
      }
    >
      {loading ? (
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <i className="fa-solid fa-circle-notch fa-spin" /> {tr('work.taskForm.loadingTask')}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {lockedReason && <WorkAlert variant="warning" message={lockedReason} />}
          {formError && <WorkAlert variant="danger" message={formError} onClose={() => setFormError('')} />}

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(300px, 100%), 1fr))',
              gap: '18px 24px',
              alignItems: 'start',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <Field label={tr('work.taskForm.labelTitle')} required htmlFor="work-form-title" error={errors.title}>
                <textarea
                  id="work-form-title"
                  value={values.title}
                  disabled={disabled}
                  onChange={(event) => update('title', event.target.value)}
                  placeholder={tr('work.taskForm.placeholderTitle')}
                  style={textAreaStyle(Boolean(errors.title))}
                />
              </Field>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
                <Field label={tr('work.taskForm.labelCreatedDate')} required error={errors.createdDate}>
                  <DateInput
                    value={values.createdDate}
                    onChange={(next) => update('createdDate', next)}
                    min={isEdit ? undefined : today}
                    disabled={disabled}
                    invalid={Boolean(errors.createdDate)}
                    ariaLabel={tr('work.taskForm.labelCreatedDate')}
                  />
                </Field>
                <Field label={tr('work.taskForm.labelDueDate')} required error={errors.dueDate}>
                  <DateInput
                    value={values.dueDate}
                    onChange={(next) => update('dueDate', next)}
                    min={dueMin}
                    disabled={disabled}
                    invalid={Boolean(errors.dueDate)}
                    ariaLabel={tr('work.taskForm.labelDueDate')}
                  />
                </Field>
              </div>

              <Field label={tr('work.taskForm.labelRequirement')} required htmlFor="work-form-requirement" error={errors.requirement}>
                <textarea
                  id="work-form-requirement"
                  value={values.requirement}
                  disabled={disabled}
                  onChange={(event) => update('requirement', event.target.value)}
                  placeholder={tr('work.taskForm.placeholderRequirement')}
                  style={textAreaStyle(Boolean(errors.requirement))}
                />
              </Field>

              <Field label={tr('work.taskForm.labelAttachments')} error={errors.attachments}>
                {existingFiles.length > 0 && (
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
                    {existingFiles.map((file) => {
                      const removing = values.removeAttachmentIds.includes(file.id);
                      return (
                        <li
                          key={file.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '8px 10px',
                            borderRadius: 'var(--radius-sm)',
                            border: `1px solid ${removing ? 'var(--color-danger-border)' : 'var(--border-subtle)'}`,
                            background: removing ? 'var(--color-danger-subtle)' : 'var(--bg-surface-hover)',
                          }}
                        >
                          <i className={fileIconClass(file.fileName)} style={{ color: 'var(--color-primary)' }} />
                          <span
                            title={file.fileName}
                            style={{
                              flex: 1,
                              minWidth: 0,
                              fontSize: '0.84rem',
                              color: 'var(--text-main)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              textDecoration: removing ? 'line-through' : 'none',
                            }}
                          >
                            {file.fileName}
                          </span>
                          <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                            {removing ? tr('work.taskForm.willDeleteOnSave') : formatFileSize(file.size)}
                          </span>
                          <button
                            type="button"
                            disabled={disabled}
                            onClick={() => toggleRemoveFile(file.id)}
                            style={{
                              border: 'none',
                              background: 'transparent',
                              color: removing ? 'var(--color-primary)' : 'var(--color-danger)',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              cursor: disabled ? 'not-allowed' : 'pointer',
                              padding: '2px 4px',
                            }}
                          >
                            {removing ? tr('work.taskForm.keepFile') : tr('work.taskForm.removeFile')}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
                <FilePicker
                  files={values.attachments}
                  onChange={(files) => update('attachments', files)}
                  disabled={disabled}
                  buttonLabel={isEdit ? tr('work.taskForm.addFile') : tr('work.taskForm.selectFile')}
                />
              </Field>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-surface-hover)',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={values.isPublic}
                  disabled={disabled}
                  onChange={(event) => update('isPublic', event.target.checked)}
                  style={{ marginTop: '3px' }}
                />
                <span>
                  <span style={{ display: 'block', fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-main)' }}>
                    {tr('work.taskForm.labelVisibility')}
                  </span>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                    {tr('work.taskForm.visibilityHint')}
                  </span>
                </span>
              </label>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <Field
                label={tr('work.taskForm.labelHost')}
                required
                hint={tr('work.taskForm.hostHint')}
                error={errors.hostId}
              >
                <EmployeeSelect
                  value={values.hostId}
                  onChange={(next) => update('hostId', next)}
                  excludeIds={[...values.directorIds, ...values.participantIds]}
                  disabled={disabled}
                  invalid={Boolean(errors.hostId)}
                  placeholder={tr('work.taskForm.placeholderHost')}
                />
              </Field>

              <Field label={tr('work.taskForm.labelDirectors')} required error={errors.directorIds}>
                <EmployeeMultiSelect
                  value={values.directorIds}
                  onChange={(next) => update('directorIds', next)}
                  excludeIds={[...(values.hostId !== null ? [values.hostId] : []), ...values.participantIds]}
                  disabled={disabled}
                  invalid={Boolean(errors.directorIds)}
                  placeholder={tr('work.taskForm.placeholderDirectors')}
                />
              </Field>

              <Field
                label={tr('work.taskForm.labelDonVi')}
                hint={tr('work.taskForm.donViHint')}
              >
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                  }}
                >
                  <input
                    type="text"
                    placeholder={tr('work.taskForm.donViSearchPlaceholder')}
                    value={donViSearch}
                    onChange={(e) => setDonViSearch(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      border: 'none',
                      borderBottom: '1px solid var(--border-subtle)',
                      background: 'transparent',
                      fontSize: '0.85rem',
                      outline: 'none',
                      color: 'var(--text-main)',
                    }}
                  />
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      padding: '10px 12px',
                      maxHeight: '200px',
                      overflowY: 'auto',
                    }}
                  >
                    {donViList.length === 0 && (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        {tr('work.taskForm.donViLoading')}
                      </span>
                    )}
                    {filteredDonVi.map((donVi) => {
                      const checked = values.donViIds.includes(donVi.id);
                      return (
                        <label
                          key={donVi.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            fontSize: '0.85rem',
                            color: 'var(--text-main)',
                            cursor: disabled ? 'not-allowed' : 'pointer',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={disabled}
                            onChange={(event) =>
                              update(
                                'donViIds',
                                event.target.checked
                                  ? [...values.donViIds, donVi.id]
                                  : values.donViIds.filter((id) => id !== donVi.id),
                              )
                            }
                          />
                          {donVi.ten}
                        </label>
                      );
                    })}
                    {donViList.length > 0 && filteredDonVi.length === 0 && (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        {tr('work.taskForm.donViNoResults')}
                      </span>
                    )}
                  </div>
                </div>
              </Field>

              <Field label={tr('work.taskForm.labelParticipants')} required error={errors.participantIds}>
                <EmployeeMultiSelect
                  value={values.participantIds}
                  onChange={(next) => update('participantIds', next)}
                  excludeIds={[...(values.hostId !== null ? [values.hostId] : []), ...values.directorIds]}
                  disabled={disabled}
                  invalid={Boolean(errors.participantIds)}
                  placeholder={tr('work.taskForm.placeholderParticipants')}
                />
              </Field>

              <WorkAlert
                variant="info"
                message={tr('work.taskForm.roleExclusiveHint')}
              />
            </div>
          </div>
        </div>
      )}
    </WorkModal>
  );
}
