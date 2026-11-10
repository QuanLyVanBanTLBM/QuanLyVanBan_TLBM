/* eslint-disable react-refresh/only-export-components -- file này export kèm vài hàm tiện ích dùng chung; quy ước module chỉ có 4 thư mục api/components/pages/types nên không tách utils riêng. */
import React, { useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { t } from '@i18n/translate';
import WorkAlert from './WorkAlert';

/**
 * Chọn nhiều file, dùng chung cho file đính kèm lúc giao việc và file bằng chứng hoàn thành.
 * Kiểm tra định dạng và dung lượng ngay tại trình duyệt để người dùng biết lỗi trước khi gửi;
 * backend vẫn kiểm tra lại lần nữa.
 */

export const ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'];
export const MAX_FILE_SIZE_MB = 20;

const ACCEPT_ATTRIBUTE = ALLOWED_EXTENSIONS.map((item) => `.${item}`).join(',');

export function formatFileSize(bytes: number): string {
  if (!bytes) return '0 KB';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function fileExtension(fileName: string): string {
  const parts = fileName.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

export function fileIconClass(fileName: string): string {
  const extension = fileExtension(fileName);
  if (extension === 'pdf') return 'fa-solid fa-file-pdf';
  if (extension === 'doc' || extension === 'docx') return 'fa-solid fa-file-word';
  if (['jpg', 'jpeg', 'png'].includes(extension)) return 'fa-solid fa-file-image';
  return 'fa-solid fa-file';
}

/** Trả về câu lỗi nêu rõ cách khắc phục, hoặc null khi file hợp lệ. */
export function validateWorkFile(file: File): string | null {
  const extension = fileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return t('work.filePicker.invalidExtension', { fileName: file.name });
  }
  if (file.size >= MAX_FILE_SIZE_MB * 1024 * 1024) {
    return t('work.filePicker.tooLarge', { fileName: file.name, size: formatFileSize(file.size), max: String(MAX_FILE_SIZE_MB) });
  }
  if (file.size === 0) {
    return t('work.filePicker.emptyFile', { fileName: file.name });
  }
  return null;
}

interface FilePickerProps {
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
  label?: string;
  hint?: string;
  buttonLabel?: string;
}

export default function FilePicker({
  files,
  onChange,
  disabled = false,
  label,
  hint,
  buttonLabel,
}: FilePickerProps) {
  const { t: tr } = useTranslation();
  const resolvedButtonLabel = buttonLabel ?? tr('work.filePicker.selectFile');
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  const handleSelect = (selected: FileList | null) => {
    if (!selected || !selected.length) return;

    const accepted: File[] = [];
    const rejected: string[] = [];

    Array.from(selected).forEach((file) => {
      const error = validateWorkFile(file);
      if (error) {
        rejected.push(error);
        return;
      }
      const isDuplicate = files.some((item) => item.name === file.name && item.size === file.size);
      if (isDuplicate) {
        rejected.push(tr('work.filePicker.duplicate', { fileName: file.name }));
        return;
      }
      accepted.push(file);
    });

    setErrors(rejected);
    if (accepted.length) {
      onChange([...files, ...accepted]);
    }
    // Xóa giá trị input để chọn lại đúng file vừa bỏ ra vẫn nhận được sự kiện change.
    if (inputRef.current) inputRef.current.value = '';
  };

  const removeAt = (index: number) => {
    onChange(files.filter((_, position) => position !== index));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {label && (
        <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{label}</label>
      )}

      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT_ATTRIBUTE}
        disabled={disabled}
        onChange={(event) => handleSelect(event.target.files)}
        style={{ display: 'none' }}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '9px 14px',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-subtle)',
            background: 'var(--bg-surface-hover)',
            color: 'var(--text-main)',
            fontWeight: 600,
            fontSize: '0.85rem',
            cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.6 : 1,
          }}
        >
          <i className="fa-solid fa-paperclip" />
          {resolvedButtonLabel}
        </button>
        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
          {hint || tr('work.filePicker.hint', { max: String(MAX_FILE_SIZE_MB) })}
        </span>
      </div>

      {errors.length > 0 && (
        <WorkAlert variant="danger" onClose={() => setErrors([])}>
          <ul style={{ margin: 0, paddingLeft: '18px' }}>
            {errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </WorkAlert>
      )}

      {files.length > 0 && (
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {files.map((file, index) => (
            <li
              key={`${file.name}-${file.size}-${index}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-surface)',
              }}
            >
              <i className={fileIconClass(file.name)} style={{ color: 'var(--color-primary)' }} />
              <span
                style={{
                  flex: 1,
                  minWidth: 0,
                  fontSize: '0.84rem',
                  color: 'var(--text-main)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={file.name}
              >
                {file.name}
              </span>
              <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{formatFileSize(file.size)}</span>
              <button
                type="button"
                onClick={() => removeAt(index)}
                disabled={disabled}
                aria-label={tr('work.filePicker.removeFileLabel', { fileName: file.name })}
                title={tr('work.filePicker.removeFile')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-danger)',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  padding: '2px 6px',
                  fontSize: '0.85rem',
                }}
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
