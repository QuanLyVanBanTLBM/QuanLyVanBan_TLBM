import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '../hooks/useIsMobile';
import { TASK_STATUS_LABELS, TaskFilters, TaskStatus } from '../types/task';
import DateInput, { isoToDisplay } from './DateInput';

/**
 * Thanh lọc phía trên bảng. Ô tìm kiếm tự áp dụng sau khi ngừng gõ (debounce), kể cả khi
 * xóa trắng (danh sách trở lại đầy đủ). Trạng thái và khoảng ngày vẫn áp dụng khi bấm
 * "Tìm kiếm" hoặc Enter, để thao tác chọn ngày/trạng thái giữa chừng không bị gọi API.
 */

const SEARCH_DEBOUNCE_MS = 350;

export type FilterDraft = Required<Pick<TaskFilters, 'search' | 'status' | 'createdFrom' | 'createdTo'>>;

interface TaskFilterBarProps {
  value: FilterDraft;
  busy?: boolean;
  onSearch: (filters: FilterDraft) => void;
  onCreate: () => void;
}

const STATUS_OPTIONS = Object.entries(TASK_STATUS_LABELS) as [TaskStatus, string][];

const fieldLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: '6px',
  fontSize: '0.78rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  maxWidth: '100%',
  boxSizing: 'border-box',
  padding: '9px 12px',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-subtle)',
  background: 'var(--bg-surface)',
  color: 'var(--text-main)',
  fontSize: '0.88rem',
  fontFamily: 'inherit',
  outline: 'none',
};

export default function TaskFilterBar({ value, busy = false, onSearch, onCreate }: TaskFilterBarProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [draft, setDraft] = useState<FilterDraft>(value);
  const [error, setError] = useState('');

  const hasFilter = Boolean(value.search || value.status || value.createdFrom || value.createdTo);

  const submit = () => {
    if (draft.createdFrom && draft.createdTo && draft.createdFrom > draft.createdTo) {
      setError(
        t('work.filter.dateRangeError', { from: isoToDisplay(draft.createdFrom), to: isoToDisplay(draft.createdTo) }),
      );
      return;
    }
    setError('');
    onSearch({ ...draft, search: draft.search.trim() });
  };

  // Ô tìm kiếm tự áp dụng sau khi ngừng gõ; dropdown tình trạng áp dụng ngay khi chọn.
  // Lần render đầu bỏ qua để không gọi API thừa khi mở trang.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return undefined;
    }
    const timer = window.setTimeout(submit, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.search]);

  const statusFirstRender = useRef(true);
  useEffect(() => {
    if (statusFirstRender.current) {
      statusFirstRender.current = false;
      return;
    }
    submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.status]);

  const reset = () => {
    const empty: FilterDraft = { search: '', status: '', createdFrom: '', createdTo: '' };
    setError('');
    setDraft(empty);
    onSearch(empty);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, minmax(0, 1fr))',
          gap: isMobile ? '10px' : '16px',
          alignItems: 'end',
        }}
      >
        <div>
          <label htmlFor="work-filter-status" style={fieldLabelStyle}>
            {t('work.filter.status')}
          </label>
          <select
            id="work-filter-status"
            value={draft.status}
            onChange={(event) => setDraft({ ...draft, status: event.target.value as TaskStatus | '' })}
            style={inputStyle}
          >
            <option value="">{t('work.filter.all')}</option>
            {STATUS_OPTIONS.map(([status]) => (
              <option key={status} value={status}>
                {t(`work.status.${status}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <span style={fieldLabelStyle}>{t('work.filter.createdFrom')}</span>
          <DateInput
            value={draft.createdFrom}
            onChange={(createdFrom) => setDraft({ ...draft, createdFrom })}
            max={draft.createdTo || undefined}
            ariaLabel={t('work.filter.createdFrom')}
          />
        </div>

        <div>
          <span style={fieldLabelStyle}>{t('work.filter.createdTo')}</span>
          <DateInput
            value={draft.createdTo}
            onChange={(createdTo) => setDraft({ ...draft, createdTo })}
            min={draft.createdFrom || undefined}
            ariaLabel={t('work.filter.createdTo')}
          />
        </div>
      </div>

      {error && <div style={{ fontSize: '0.8rem', color: 'var(--color-danger)' }}>{error}</div>}

      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          alignItems: isMobile ? 'stretch' : 'center',
        }}
      >
        <button
          type="button"
          onClick={onCreate}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            background: 'var(--color-primary)',
            color: '#ffffff',
            fontWeight: 700,
            fontSize: '0.86rem',
            cursor: 'pointer',
            boxShadow: '0 4px 12px var(--color-primary-glow)',
            whiteSpace: 'nowrap',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <i className="fa-solid fa-plus" />
          {t('work.filter.addTask')}
        </button>

        <div
          style={{
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '8px',
            flexWrap: 'wrap',
            alignItems: isMobile ? 'stretch' : 'center',
            flex: isMobile ? '1 1 auto' : '1 1 320px',
            justifyContent: isMobile ? 'stretch' : 'flex-end',
          }}
        >
          <input
            id="work-filter-search"
            type="search"
            value={draft.search}
            placeholder={t('work.filter.searchPlaceholder')}
            aria-label={t('work.filter.searchAriaLabel')}
            onChange={(event) => setDraft({ ...draft, search: event.target.value })}
            onKeyDown={(event) => {
              if (event.key === 'Enter') submit();
            }}
            style={{ ...inputStyle, flex: isMobile ? '1 1 auto' : '1 1 220px', width: isMobile ? '100%' : 'auto', maxWidth: isMobile ? '100%' : '360px' }}
          />
          {hasFilter && (
            <button
              type="button"
              onClick={reset}
              disabled={busy}
              style={{
                padding: '9px 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-surface)',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.86rem',
                cursor: busy ? 'not-allowed' : 'pointer',
              }}
            >
              {t('work.filter.clearFilters')}
            </button>
          )}
          <button
            type="button"
            onClick={submit}
            disabled={busy}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-primary-border)',
              background: 'var(--color-primary-subtle)',
              color: 'var(--color-primary)',
              fontWeight: 700,
              fontSize: '0.86rem',
              cursor: busy ? 'not-allowed' : 'pointer',
            }}
          >
            <i className="fa-solid fa-magnifying-glass" />
            {t('work.filter.search')}
          </button>
        </div>
      </div>
    </div>
  );
}
