import React from 'react';

export interface DropdownSearchInputProps {
  value: string;
  onChange: (nextValue: string) => void;
  placeholder: string;
  clearLabel: string;
  ariaLabel?: string;
  autoFocus?: boolean;
  onEscape?: () => void;
  wrapperClassName?: string;
  inputClassName?: string;
}

/**
 * Ô tìm kiếm gọn bên trong các dropdown popover lọc Thư mục và Loại tài liệu.
 * Chặn nổi bọt mousedown/click để người dùng gõ hoặc xóa từ khóa không làm tự đóng menu.
 */
export const DropdownSearchInput: React.FC<DropdownSearchInputProps> = ({
  value,
  onChange,
  placeholder,
  clearLabel,
  ariaLabel,
  autoFocus = false,
  onEscape,
  wrapperClassName = '',
  inputClassName = 'bg-surface-elevated',
}) => {
  return (
    <div
      className={`relative ${wrapperClassName}`}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-muted text-[11px] pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape' && onEscape) {
            e.stopPropagation();
            onEscape();
          }
        }}
        placeholder={placeholder}
        aria-label={ariaLabel || placeholder}
        autoFocus={autoFocus}
        className={`w-full pl-7 pr-7 py-1.5 text-xs border border-border-subtle rounded-lg text-main placeholder:text-muted focus:outline-hidden focus:border-primary transition-colors ${inputClassName}`}
      />
      {value && (
        <button
          type="button"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            onChange('');
          }}
          aria-label={clearLabel}
          title={clearLabel}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-main text-[11px] p-0.5 cursor-pointer"
        >
          <i className="fa-solid fa-xmark" />
        </button>
      )}
    </div>
  );
};

