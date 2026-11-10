import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { employeeLabel, employeeMeta, useEmployeeSearch } from './EmployeeSelect';

/** Ô chọn nhiều cán bộ, hiển thị dạng thẻ. Dùng cho Chỉ đạo - Theo dõi và Cán bộ tham gia. */

interface EmployeeMultiSelectProps {
  value: number[];
  onChange: (employeeIds: number[]) => void;
  /** Những người đã giữ vai trò khác trong cùng công việc: không cho chọn lại. */
  excludeIds?: number[];
  disabled?: boolean;
  placeholder?: string;
  invalid?: boolean;
}

export default function EmployeeMultiSelect({
  value,
  onChange,
  excludeIds = [],
  disabled = false,
  placeholder,
  invalid = false,
}: EmployeeMultiSelectProps) {
  const { t } = useTranslation();
  const resolvedPlaceholder = placeholder ?? t('work.employees.selectPlaceholder');
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { keyword, setKeyword, options, cache, loading, error } = useEmployeeSearch(open);

  useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const toggle = (employeeId: number) => {
    if (value.includes(employeeId)) {
      onChange(value.filter((item) => item !== employeeId));
    } else {
      onChange([...value, employeeId]);
    }
  };

  const visibleOptions = options.filter((item) => !excludeIds.includes(item.id));

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && setOpen((previous) => !previous)}
        onKeyDown={(event) => {
          if (!disabled && (event.key === 'Enter' || event.key === ' ')) {
            event.preventDefault();
            setOpen((previous) => !previous);
          }
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          flexWrap: 'wrap',
          minHeight: '40px',
          padding: '6px 10px',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${invalid ? 'var(--color-danger)' : open ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
          background: disabled ? 'var(--bg-surface-hover)' : 'var(--bg-surface)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.65 : 1,
        }}
      >
        {value.length === 0 && (
          <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>{resolvedPlaceholder}</span>
        )}

        {value.map((employeeId) => {
          const employee = cache[employeeId];
          return (
            <span
              key={employeeId}
              title={employee ? employeeLabel(employee) : undefined}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '3px 8px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-primary-subtle)',
                border: '1px solid var(--color-primary-border)',
                color: 'var(--text-main)',
                fontSize: '0.78rem',
                fontWeight: 600,
              }}
            >
              {employee ? employee.fullName : t('work.common.employeeId', { id: String(employeeId) })}
              {!disabled && (
                <span
                  role="button"
                  tabIndex={-1}
                  aria-label={t('work.employees.removeEmployee')}
                  onClick={(event) => {
                    event.stopPropagation();
                    onChange(value.filter((item) => item !== employeeId));
                  }}
                  style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}
                >
                  <i className="fa-solid fa-xmark" />
                </span>
              )}
            </span>
          );
        })}

        <i
          className="fa-solid fa-chevron-down"
          style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}
        />
      </div>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            zIndex: 30,
            padding: '10px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface-elevated)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <input
            type="text"
            autoFocus
            value={keyword}
            placeholder={t('work.employees.searchPlaceholder')}
            onChange={(event) => setKeyword(event.target.value)}
            style={{
              width: '100%',
              padding: '8px 10px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
              fontFamily: 'inherit',
              outline: 'none',
            }}
          />

          <div style={{ maxHeight: '220px', overflowY: 'auto', marginTop: '8px' }}>
            {loading && (
              <div style={{ padding: '10px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>{t('work.common.loading')}</div>
            )}
            {!loading && error && (
              <div style={{ padding: '10px', fontSize: '0.82rem', color: 'var(--color-danger)' }}>{error}</div>
            )}
            {!loading && !error && visibleOptions.length === 0 && (
              <div style={{ padding: '10px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {t('work.employees.noResults')}
              </div>
            )}
            {!loading &&
              !error &&
              visibleOptions.map((employee) => {
                const checked = value.includes(employee.id);
                return (
                  <button
                    key={employee.id}
                    type="button"
                    onClick={() => toggle(employee.id)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      border: 'none',
                      background: checked ? 'var(--color-primary-subtle)' : 'transparent',
                      color: 'var(--text-main)',
                      fontSize: '0.85rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <i
                      className={checked ? 'fa-solid fa-square-check' : 'fa-regular fa-square'}
                      style={{ color: checked ? 'var(--color-primary)' : 'var(--text-muted)' }}
                    />
                    <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, gap: '1px' }}>
                      <span style={{ fontWeight: 600 }}>{employee.fullName}</span>
                      {employeeMeta(employee) && (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          {employeeMeta(employee)}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
          </div>

          <div
            style={{
              marginTop: '8px',
              paddingTop: '8px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '0.76rem',
              color: 'var(--text-muted)',
            }}
          >
            {t('work.employees.selectedCount', { count: String(value.length) })}
          </div>
        </div>
      )}
    </div>
  );
}
