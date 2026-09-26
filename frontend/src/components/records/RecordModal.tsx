import React from 'react';
import { Button } from '@components/common';
import type { Dossier, DossierPayload, DocumentType, DocumentTypePayload } from '@app-types/records';

const fieldClass =
  'w-full rounded-lg border border-border-subtle bg-surface-elevated px-3 py-2.5 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle disabled:opacity-60';

interface BaseProps {
  open: boolean;
  isLoading?: boolean;
  error?: string | null;
  onClose: () => void;
}

interface DossierModalProps extends BaseProps {
  mode: 'dossier';
  value?: Dossier | null;
  onSubmit: (payload: DossierPayload) => void;
}

interface DocumentTypeModalProps extends BaseProps {
  mode: 'documentType';
  value?: DocumentType | null;
  onSubmit: (payload: DocumentTypePayload) => void;
}

type RecordModalProps = DossierModalProps | DocumentTypeModalProps;

function dateInputValue(value?: string | null): string {
  return value ? value.slice(0, 10) : '';
}

export default function RecordModal(props: RecordModalProps) {
  if (!props.open) return null;

  const entityKey = props.value ? String(props.value.id) : 'new';
  return <RecordModalForm key={`${props.mode}-${entityKey}`} {...props} />;
}

function RecordModalForm(props: RecordModalProps) {
  const { open, isLoading = false, error, onClose, mode, value } = props;
  const dossier = mode === 'dossier' ? (value as Dossier | null | undefined) : null;
  const documentType = mode === 'documentType' ? (value as DocumentType | null | undefined) : null;
  const [priority, setPriority] = React.useState(dossier?.stt_uu_tien == null ? '' : String(dossier.stt_uu_tien));
  const [code, setCode] = React.useState(dossier?.so_ky_hieu ?? '');
  const [name, setName] = React.useState(dossier?.ten_ho_so ?? documentType?.ten_loai ?? '');
  const [date, setDate] = React.useState(dateInputValue(dossier?.ngay_lap ?? documentType?.ngay_lap));
  const [note, setNote] = React.useState(dossier?.ghi_chu ?? documentType?.ghi_chu ?? '');
  const [validation, setValidation] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoading) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, isLoading, onClose]);

  const isEditing = Boolean(value);
  const title = `${isEditing ? 'Chỉnh sửa' : 'Thêm'} ${mode === 'dossier' ? 'hồ sơ' : 'loại văn bản'}`;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setValidation(mode === 'dossier' ? 'Vui lòng nhập tên hồ sơ.' : 'Vui lòng nhập tên loại văn bản.');
      return;
    }
    if (mode === 'dossier' && !code.trim()) {
      setValidation('Vui lòng nhập số/ký hiệu hồ sơ.');
      return;
    }
    if (mode === 'dossier' && priority && (!Number.isInteger(Number(priority)) || Number(priority) < 0)) {
      setValidation('Số thứ tự ưu tiên phải là số nguyên không âm.');
      return;
    }

    setValidation(null);
    if (mode === 'dossier') {
      (props as DossierModalProps).onSubmit({
        stt_uu_tien: priority === '' ? null : Number(priority),
        so_ky_hieu: code.trim(),
        ten_ho_so: name.trim(),
        ngay_lap: date || null,
        ghi_chu: note.trim(),
      });
    } else {
      (props as DocumentTypeModalProps).onSubmit({
        ten_loai: name.trim(),
        ngay_lap: date || null,
        ghi_chu: note.trim(),
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4" role="presentation">
      <form
        className="max-h-[90vh] w-full max-w-xl animate-slide-in-bottom overflow-y-auto rounded-xl border border-border-subtle bg-surface shadow-lg"
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="record-modal-title"
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <div>
            <h2 id="record-modal-title" className="m-0 text-lg font-bold text-main">{title}</h2>
            <p className="m-0 mt-1 text-xs text-muted">Các trường có dấu * là bắt buộc.</p>
          </div>
          <button
            type="button"
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted transition hover:bg-surface-hover hover:text-main"
            onClick={onClose}
            disabled={isLoading}
            aria-label="Đóng"
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {mode === 'dossier' && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block text-sm font-semibold text-secondary">
                Số/ký hiệu *
                <input className={`${fieldClass} mt-1.5`} value={code} onChange={(e) => setCode(e.target.value)} maxLength={100} autoFocus />
              </label>
              <label className="block text-sm font-semibold text-secondary">
                Thứ tự ưu tiên
                <input className={`${fieldClass} mt-1.5`} type="number" min="0" value={priority} onChange={(e) => setPriority(e.target.value)} />
              </label>
            </div>
          )}

          <label className="block text-sm font-semibold text-secondary">
            {mode === 'dossier' ? 'Tên hồ sơ' : 'Tên loại văn bản'} *
            <input
              className={`${fieldClass} mt-1.5`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
              autoFocus={mode !== 'dossier'}
            />
          </label>

          <label className="block text-sm font-semibold text-secondary">
            Ngày lập
            <input className={`${fieldClass} mt-1.5`} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>

          <label className="block text-sm font-semibold text-secondary">
            Ghi chú
            <textarea className={`${fieldClass} mt-1.5 min-h-24 resize-y`} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
          </label>

          {(validation || error) && (
            <div className="rounded-lg border border-danger-border bg-danger-subtle px-3 py-2 text-sm text-danger" role="alert">
              {validation || error}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border-subtle px-5 py-4">
          <Button type="button" variant="secondary" disabled={isLoading} onClick={onClose}>Hủy</Button>
          <Button type="submit" isLoading={isLoading} icon="fa-floppy-disk">
            {isEditing ? 'Lưu thay đổi' : 'Thêm mới'}
          </Button>
        </div>
      </form>
    </div>
  );
}
