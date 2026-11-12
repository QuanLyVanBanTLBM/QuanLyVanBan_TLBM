/* eslint-disable react-refresh/only-export-components -- file này export kèm vài hàm tiện ích dùng chung; quy ước module chỉ có 4 thư mục api/components/pages/types nên không tách utils riêng. */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { listEmployees } from '../api/employees';
import { toMessage } from '../api/client';
import { Employee } from '../types/employee';

/** Ô chọn một cán bộ, có tìm kiếm theo tên. Hiển thị dạng "Họ Tên (Chức vụ - Phòng ban)". */

/**
 * Phần "Chức vụ - Phòng ban". Ghép có điều kiện để không bị cụt đuôi khi thiếu dữ liệu:
 * đủ cả hai → "Chức vụ - Phòng ban"; thiếu phòng ban → "Chức vụ"; thiếu chức vụ → "Phòng ban";
 * thiếu cả hai → "".
 */
export function employeeMeta(employee: Employee): string {
  return [employee.position, employee.department].filter(Boolean).join(' - ');
}

/** Nhãn đầy đủ: "Họ Tên (Chức vụ - Phòng ban)", gọn lại khi thiếu chức vụ/phòng ban. */
export function employeeLabel(employee: Employee): string {
  const meta = employeeMeta(employee);
  return meta ? `${employee.fullName} (${meta})` : employee.fullName;
}

/**
 * Tải danh sách cán bộ theo từ khóa, có chờ 300ms để không gọi API sau mỗi phím gõ.
 * Dùng chung cho EmployeeSelect và EmployeeMultiSelect.
 */
export function useEmployeeSearch(enabled: boolean) {
  const [keyword, setKeyword] = useState('');
  const [options, setOptions] = useState<Employee[]>([]);
  const [cache, setCache] = useState<Record<number, Employee>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (!enabled && loadedOnce.current) return undefined;

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError('');
      listEmployees(keyword, controller.signal)
        .then((data) => {
          loadedOnce.current = true;
          setOptions(data);
          setCache((previous) => {
            const next = { ...previous };
            data.forEach((item) => {
              next[item.id] = item;
            });
            return next;
          });
        })
        .catch((cause) => {
          if (cause instanceof DOMException && cause.name === 'AbortError') return;
          setError(toMessage(cause));
        })
        .finally(() => setLoading(false));
    }, keyword ? 300 : 0);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [keyword, enabled]);

  return { keyword, setKeyword, options, cache, loading, error };
}

interface EmployeeSelectProps {
  value: number | null;
  onChange: (employeeId: number | null) => void;
  /** Những người đã giữ vai trò khác trong cùng công việc: không cho chọn lại. */
  excludeIds?: number[];
  disabled?: boolean;
  placeholder?: string;
  invalid?: boolean;
  allowClear?: boolean;
}

export default function EmployeeSelect({
  value,
  onChange,
  excludeIds = [],
  disabled = false,
  placeholder,
  invalid = false,
  allowClear = true,
}: EmployeeSelectProps) {
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

  const selected = value !== null ? cache[value] : undefined;
  const visibleOptions = options.filter((item) => !excludeIds.includes(item.id));

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => !disabled && setOpen((previous) => !previous)}
        disabled={disabled}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          padding: '9px 12px',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${invalid ? 'var(--color-danger)' : open ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
          background: disabled ? 'var(--bg-surface-hover)' : 'var(--bg-surface)',
          color: selected ? 'var(--text-main)' : 'var(--text-muted)',
          fontSize: '0.88rem',
          fontWeight: selected ? 600 : 400,
          textAlign: 'left',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.65 : 1,
        }}
      >
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? employeeLabel(selected) : value !== null ? t('work.common.employeeId', { id: String(value) }) : resolvedPlaceholder}
        </span>
        {allowClear && value !== null && !disabled && (
          <span
            role="button"
            tabIndex={-1}
            aria-label={t('work.employees.deselect')}
            onClick={(event) => {
              event.stopPropagation();
              onChange(null);
            }}
            style={{ color: 'var(--text-muted)', padding: '0 2px' }}
          >
            <i className="fa-solid fa-xmark" />
          </span>
        )}
        <i className="fa-solid fa-chevron-down" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }} />
      </button>

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
                const isSelected = employee.id === value;
                return (
                  <button
                    key={employee.id}
                    type="button"
                    onClick={() => {
                      onChange(employee.id);
                      setOpen(false);
                    }}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      border: 'none',
                      background: isSelected ? 'var(--color-primary-subtle)' : 'transparent',
                      color: 'var(--text-main)',
                      fontSize: '0.85rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, gap: '1px' }}>
                      <span style={{ fontWeight: 600 }}>{employee.fullName}</span>
                      {employeeMeta(employee) && (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          {employeeMeta(employee)}
                        </span>
                      )}
                    </span>
                    {isSelected && <i className="fa-solid fa-check" style={{ color: 'var(--color-primary)' }} />}
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
