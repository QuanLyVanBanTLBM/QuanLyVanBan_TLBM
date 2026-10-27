import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';

export interface SelectOption {
  value: string;
  label: string;
  group?: string;
  subLabel?: string;
  badge?: React.ReactNode;
  icon?: string;
  disabled?: boolean;
}

export interface SelectProps {
  id?: string;
  name?: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  label?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  searchable?: boolean;
  clearable?: boolean;
  className?: string;
  leftIcon?: string;
  size?: 'sm' | 'md' | 'lg';
  ariaLabel?: string;
}

export const Select: React.FC<SelectProps> = ({
  id,
  name,
  value,
  onChange,
  options,
  placeholder = 'Chọn một mục...',
  label,
  error,
  required = false,
  disabled = false,
  searchable,
  clearable = false,
  className = '',
  leftIcon,
  size = 'md',
  ariaLabel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Tìm option đang được chọn
  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  );

  // Tự động bật tìm kiếm nếu số lượng tùy chọn lớn hơn 7 hoặc được cấu hình rõ ràng
  const isSearchActive = searchable !== undefined ? searchable : options.length > 7;

  // Lọc options theo tìm kiếm
  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const query = searchQuery.toLowerCase().trim();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        (opt.subLabel && opt.subLabel.toLowerCase().includes(query)) ||
        (opt.group && opt.group.toLowerCase().includes(query))
    );
  }, [options, searchQuery]);

  // Nhóm options theo group (nếu có)
  const groupedOptions = useMemo(() => {
    const hasGroups = filteredOptions.some((opt) => opt.group);
    if (!hasGroups) return null;

    const map = new Map<string, SelectOption[]>();
    for (const opt of filteredOptions) {
      const g = opt.group || 'Khác';
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(opt);
    }
    return map;
  }, [filteredOptions]);

  // Xử lý đóng khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent | TouchEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchQuery('');
        setHighlightedIndex(-1);
      }
    }
    document.addEventListener('pointerdown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  // Tự động focus vào ô tìm kiếm khi mở menu
  useEffect(() => {
    if (isOpen && isSearchActive) {
      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen, isSearchActive]);

  // Xử lý chọn mục
  const handleSelect = useCallback(
    (val: string) => {
      onChange(val);
      setIsOpen(false);
      setSearchQuery('');
      setHighlightedIndex(-1);
    },
    [onChange]
  );

  // Xóa lựa chọn
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
    setSearchQuery('');
  };

  // Điều hướng bằng phím
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      setSearchQuery('');
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < filteredOptions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : filteredOptions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
        const item = filteredOptions[highlightedIndex];
        if (!item.disabled) {
          handleSelect(item.value);
        }
      }
    }
  };

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1.5 min-h-[32px]',
    md: 'text-sm px-3.5 py-2 min-h-[38px]',
    lg: 'text-base px-4 py-2.5 min-h-[44px]',
  };

  return (
    <div className={`relative w-full ${className}`} ref={containerRef}>
      {label && (
        <label
          htmlFor={id}
          className="block text-sm font-semibold text-secondary mb-1.5 select-none"
        >
          {label} {required && <span className="text-danger">*</span>}
        </label>
      )}

      {/* Hidden Native Input để tương thích 100% với form submit & HTML APIs */}
      <input
        type="hidden"
        id={id}
        name={name}
        value={value}
        data-testid={id ? `select-hidden-${id}` : undefined}
      />

      {/* Nút Trigger Dropdown */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel || label || placeholder}
        className={`w-full flex items-center justify-between gap-2 bg-surface-elevated border rounded-lg text-left select-none transition-all duration-fast cursor-pointer ${
          sizeClasses[size]
        } ${
          isOpen
            ? 'border-primary ring-2 ring-primary/20 shadow-sm'
            : error
            ? 'border-danger focus:border-danger ring-1 ring-danger/20'
            : 'border-border hover:border-primary/50'
        } ${disabled ? 'opacity-50 cursor-not-allowed bg-surface' : ''}`}
      >
        <div className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
          {leftIcon && (
            <i className={`fa-solid ${leftIcon} text-muted shrink-0 text-xs`} />
          )}

          {selectedOption ? (
            <div className="flex items-center gap-1.5 truncate">
              {selectedOption.icon && (
                <i className={`fa-solid ${selectedOption.icon} text-primary text-xs shrink-0`} />
              )}
              <span className="text-main font-medium truncate">{selectedOption.label}</span>
              {selectedOption.subLabel && (
                <span className="text-xs text-muted truncate hidden sm:inline">
                  ({selectedOption.subLabel})
                </span>
              )}
              {selectedOption.badge}
            </div>
          ) : (
            <span className="text-muted truncate">{placeholder}</span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0 ml-1">
          {clearable && value && !disabled && (
            <span
              role="button"
              tabIndex={0}
              onClick={handleClear}
              onKeyDown={(e) => e.key === 'Enter' && handleClear(e as unknown as React.MouseEvent)}
              title="Xóa lựa chọn"
              className="p-1 text-muted hover:text-danger rounded-full transition-colors"
            >
              <i className="fa-solid fa-xmark text-xs" />
            </span>
          )}
          <i
            className={`fa-solid fa-chevron-down text-[11px] text-muted transition-transform duration-200 ${
              isOpen ? 'rotate-180 text-primary' : ''
            }`}
          />
        </div>
      </button>

      {/* Menu Xổ Xuống (Dropdown Popover) */}
      {isOpen && (
        <div
          className="dropdown-animate absolute left-0 right-0 top-full mt-1.5 w-full max-w-full sm:min-w-[220px] rounded-xl bg-surface-elevated border border-border-subtle shadow-2xl p-1.5 z-[10002] flex flex-col box-border"
          role="listbox"
        >
          {/* Ô Tìm Kiếm Nhanh */}
          {isSearchActive && (
            <div className="p-1 border-b border-subtle mb-1 relative">
              <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-xs" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setHighlightedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Tìm kiếm nhanh..."
                className="w-full pl-8 pr-7 py-1.5 text-xs bg-surface border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main p-1"
                >
                  <i className="fa-solid fa-xmark text-xs" />
                </button>
              )}
            </div>
          )}

          {/* Danh Sách Tùy Chọn */}
          <div
            ref={listRef}
            className="max-h-60 overflow-y-auto space-y-0.5 custom-scrollbar pr-0.5"
          >
            {filteredOptions.length === 0 ? (
              <div className="py-6 px-3 text-center text-xs text-muted">
                <i className="fa-solid fa-inbox text-base mb-1 block opacity-40" />
                <span>Không tìm thấy kết quả phù hợp</span>
              </div>
            ) : groupedOptions ? (
              // Hiển thị theo nhóm
              Array.from(groupedOptions.entries()).map(([groupName, groupOpts]) => (
                <div key={groupName} className="mb-2 last:mb-0">
                  <div className="px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-muted bg-surface/60 rounded-md mb-1 flex items-center gap-1.5 select-none">
                    <i className="fa-solid fa-layer-group text-[10px] text-primary/70" />
                    <span className="truncate">{groupName}</span>
                    <span className="ml-auto text-[10px] font-normal opacity-70">
                      ({groupOpts.length})
                    </span>
                  </div>

                  <div className="space-y-0.5 pl-1">
                    {groupOpts.map((option) => {
                      const isSelected = option.value === value;
                      return (
                        <div
                          key={option.value}
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => !option.disabled && handleSelect(option.value)}
                          className={`w-full px-2.5 py-1.5 text-sm rounded-lg text-left flex items-center justify-between transition-colors cursor-pointer select-none ${
                            isSelected
                              ? 'bg-primary/15 text-primary font-semibold'
                              : 'text-main hover:bg-surface-hover hover:text-primary'
                          } ${option.disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            {option.icon && (
                              <i className={`fa-solid ${option.icon} text-xs shrink-0 ${isSelected ? 'text-primary' : 'text-muted'}`} />
                            )}
                            <span className="truncate">{option.label}</span>
                            {option.subLabel && (
                              <span className="text-xs text-muted truncate">
                                {option.subLabel}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 ml-2">
                            {option.badge}
                            {isSelected && (
                              <i className="fa-solid fa-check text-xs text-primary" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            ) : (
              // Hiển thị phẳng không phân nhóm
              filteredOptions.map((option) => {
                const isSelected = option.value === value;
                return (
                  <div
                    key={option.value}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => !option.disabled && handleSelect(option.value)}
                    className={`w-full px-3 py-2 text-sm rounded-lg text-left flex items-center justify-between transition-colors cursor-pointer select-none ${
                      isSelected
                        ? 'bg-primary/15 text-primary font-semibold'
                        : 'text-main hover:bg-surface-hover hover:text-primary'
                    } ${option.disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      {option.icon && (
                        <i className={`fa-solid ${option.icon} text-xs shrink-0 ${isSelected ? 'text-primary' : 'text-muted'}`} />
                      )}
                      <span className="truncate">{option.label}</span>
                      {option.subLabel && (
                        <span className="text-xs text-muted truncate">({option.subLabel})</span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      {option.badge}
                      {isSelected && (
                        <i className="fa-solid fa-check text-xs text-primary" />
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
};

export default Select;
