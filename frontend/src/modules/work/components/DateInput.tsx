/* eslint-disable react-refresh/only-export-components -- file này export kèm vài hàm tiện ích dùng chung; quy ước module chỉ có 4 thư mục api/components/pages/types nên không tách utils riêng. */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import './DateInput.css';

/**
 * Ô nhập ngày luôn hiển thị dd/mm/yyyy, kèm lịch tự vẽ.
 *
 * Không dùng <input type="date"> vì ô ngày của trình duyệt hiển thị theo ngôn ngữ máy
 * (máy để tiếng Anh sẽ ra mm/dd/yyyy), còn nghiệp vụ bắt buộc dd/mm/yyyy.
 *
 * Giá trị trao đổi với bên ngoài luôn là chuỗi ISO "YYYY-MM-DD" đúng định dạng API,
 * chỉ phần hiển thị mới là dd/mm/yyyy.
 */

const WEEKDAY_KEYS = ['weekdayMo', 'weekdayTu', 'weekdayWe', 'weekdayTh', 'weekdayFr', 'weekdaySa', 'weekdaySu'] as const;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Hôm nay theo giờ máy người dùng (không dùng UTC để không lệch một ngày). */
export function todayIso(): string {
  return toIsoDate(new Date());
}

export function isoToDisplay(iso: string): string {
  if (!iso) return '';
  const [year, month, day] = iso.split('-');
  if (!year || !month || !day) return '';
  return `${day}/${month}/${year}`;
}

/**
 * Mốc thời gian API trả về (ví dụ "2026-09-19T14:03:05.123+07:00") thành "19/09/2026 14:03:05".
 * Đọc thẳng từ chuỗi vì backend đã trả theo giờ Việt Nam; không đổi qua Date để máy
 * đặt múi giờ khác vẫn hiện đúng.
 */
export function isoDateTimeToDisplay(value: string | null | undefined, withSeconds = true): string {
  if (!value) return '';
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/.exec(value);
  if (!match) return value;
  const [, year, month, day, hour, minute, second] = match;
  return `${day}/${month}/${year} ${hour}:${minute}${withSeconds ? `:${second}` : ''}`;
}

/** Số ngày từ hôm nay tới hạn: dương là còn hạn, âm là đã quá hạn, 0 là hạn hôm nay. */
export function daysUntil(isoDate: string): number {
  const [year, month, day] = isoDate.split('-').map(Number);
  const [todayYear, todayMonth, todayDay] = todayIso().split('-').map(Number);
  const target = Date.UTC(year, month - 1, day);
  const today = Date.UTC(todayYear, todayMonth - 1, todayDay);
  return Math.round((target - today) / 86400000);
}

/** Kiểm tra ngày có thật không: 31/02 hay 31/04 đều bị loại. */
function isRealDate(day: number, month: number, year: number): boolean {
  if (year < 1900 || year > 2200 || month < 1 || month > 12 || day < 1) return false;
  const date = new Date(year, month - 1, day);
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day;
}

/** "25/12/2026" thành "2026-12-25"; chuỗi chưa đủ hoặc ngày không có thật thì trả về ''. */
export function displayToIso(text: string): string {
  const digits = text.replace(/\D/g, '');
  if (digits.length !== 8) return '';
  const day = Number(digits.slice(0, 2));
  const month = Number(digits.slice(2, 4));
  const year = Number(digits.slice(4, 8));
  if (!isRealDate(day, month, year)) return '';
  return `${year}-${pad(month)}-${pad(day)}`;
}

/** Vừa gõ vừa chèn dấu gạch chéo để người dùng không phải tự gõ. */
function maskDigits(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

interface DateInputProps {
  /** Chuỗi ISO "YYYY-MM-DD", hoặc '' khi chưa chọn. */
  value: string;
  onChange: (isoDate: string) => void;
  /** Giới hạn ISO; ngày ngoài khoảng sẽ mờ đi và không bấm được. */
  min?: string;
  max?: string;
  disabled?: boolean;
  placeholder?: string;
  /** true thì viền đổi sang màu đỏ, dùng khi trường này đang có lỗi. */
  invalid?: boolean;
  id?: string;
  ariaLabel?: string;
}

export default function DateInput({
  value,
  onChange,
  min,
  max,
  disabled = false,
  placeholder,
  invalid = false,
  id,
  ariaLabel,
}: DateInputProps) {
  const { t } = useTranslation();
  const [text, setText] = useState(() => isoToDisplay(value));
  const [open, setOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const [hint, setHint] = useState('');
  const containerRef = useRef<HTMLDivElement | null>(null);
  // Nhớ giá trị chính ô này vừa phát ra, để hiệu ứng đồng bộ bên dưới không xóa chữ đang gõ.
  const lastEmitted = useRef(value);

  const emit = (isoDate: string) => {
    lastEmitted.current = isoDate;
    onChange(isoDate);
  };

  const anchorIso = value || todayIso();
  const [viewYear, setViewYear] = useState(() => Number(anchorIso.slice(0, 4)));
  const [viewMonth, setViewMonth] = useState(() => Number(anchorIso.slice(5, 7)) - 1);

  // Chỉ cập nhật ô khi giá trị đổi từ bên ngoài, ví dụ khi mở form sửa hoặc cha đặt lại dữ liệu.
  useEffect(() => {
    if (value === lastEmitted.current) return;
    lastEmitted.current = value;
    setText(isoToDisplay(value));
    setHint('');
  }, [value]);

  useEffect(() => {
    if (!open) return undefined;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        // Chỉ đóng lịch, không để phím Esc đóng luôn modal đang chứa ô ngày.
        event.stopPropagation();
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [open]);

  const openCalendar = () => {
    if (disabled) return;
    const base = value || min || todayIso();
    setViewYear(Number(base.slice(0, 4)));
    setViewMonth(Number(base.slice(5, 7)) - 1);
    setOpen((prev) => !prev);
  };

  const isOutOfRange = (iso: string): boolean => {
    if (min && iso < min) return true;
    if (max && iso > max) return true;
    return false;
  };

  const outOfRangeMessage = (): string => {
    if (min && max) return t('work.dateInput.rangeMinMax', { min: isoToDisplay(min), max: isoToDisplay(max) });
    if (min) return t('work.dateInput.rangeMin', { min: isoToDisplay(min) });
    return t('work.dateInput.rangeMax', { max: isoToDisplay(max || '') });
  };

  const handleTextChange = (raw: string) => {
    const masked = maskDigits(raw);
    setText(masked);
    const digitCount = masked.replace(/\D/g, '').length;

    // Đang gõ dở thì chưa báo lỗi, nhưng cũng chưa có giá trị hợp lệ để gửi đi.
    if (digitCount < 8) {
      setHint('');
      emit('');
      return;
    }

    const iso = displayToIso(masked);
    if (!iso) {
      // Không âm thầm giữ ngày cũ: người dùng phải thấy đúng cái mình đang nhập.
      setHint(t('work.dateInput.invalidDate', { date: masked }));
      emit('');
      return;
    }

    setHint(isOutOfRange(iso) ? outOfRangeMessage() : '');
    emit(iso);
    setViewYear(Number(iso.slice(0, 4)));
    setViewMonth(Number(iso.slice(5, 7)) - 1);
  };

  const handleBlur = () => {
    setFocused(false);
    const digitCount = text.replace(/\D/g, '').length;
    if (digitCount > 0 && digitCount < 8) {
      setHint(t('work.dateInput.incompleteDate'));
    }
  };

  const days = useMemo(() => {
    const firstOfMonth = new Date(viewYear, viewMonth, 1);
    // getDay() trả CN = 0, đổi lại để tuần bắt đầu từ Thứ Hai.
    const leading = (firstOfMonth.getDay() + 6) % 7;
    const start = new Date(viewYear, viewMonth, 1 - leading);
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index);
      return {
        iso: toIsoDate(date),
        day: date.getDate(),
        inCurrentMonth: date.getMonth() === viewMonth && date.getFullYear() === viewYear,
      };
    });
  }, [viewMonth, viewYear]);

  const shiftMonth = (offset: number) => {
    const next = new Date(viewYear, viewMonth + offset, 1);
    setViewYear(next.getFullYear());
    setViewMonth(next.getMonth());
  };

  const today = todayIso();

  const navButtonStyle: React.CSSProperties = {
    width: '28px',
    height: '28px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-subtle)',
    background: 'var(--bg-surface)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: '0.75rem',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const borderColor = invalid || hint
    ? 'var(--color-danger)'
    : focused || open
      ? 'var(--border-focus)'
      : 'var(--border-subtle)';

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '0 10px',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${borderColor}`,
          background: disabled ? 'var(--bg-surface-hover)' : 'var(--bg-surface)',
          opacity: disabled ? 0.65 : 1,
          transition: 'border-color var(--transition-fast)',
        }}
      >
        <input
          id={id}
          type="text"
          className="work-date-input-field"
          inputMode="numeric"
          autoComplete="off"
          aria-label={ariaLabel || t('work.dateInput.ariaLabel')}
          value={text}
          placeholder={placeholder || t('work.dateInput.placeholder')}
          disabled={disabled}
          onChange={(event) => handleTextChange(event.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={handleBlur}
          style={{
            flex: 1,
            minWidth: 0,
            padding: '9px 0',
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: 'var(--text-main)',
            fontSize: '0.88rem',
            fontFamily: 'inherit',
          }}
        />
        <button
          type="button"
          onClick={openCalendar}
          disabled={disabled}
          aria-label={t('work.dateInput.openCalendar')}
          style={{
            background: 'transparent',
            border: 'none',
            color: open ? 'var(--color-primary)' : 'var(--text-secondary)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            padding: '4px',
            fontSize: '0.9rem',
          }}
        >
          <i className="fa-regular fa-calendar" />
        </button>
      </div>

      {hint && (
        <div style={{ marginTop: '4px', fontSize: '0.75rem', color: 'var(--color-danger)', lineHeight: 1.5 }}>
          {hint}
        </div>
      )}

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            zIndex: 30,
            width: '280px',
            maxWidth: 'calc(100vw - 32px)',
            boxSizing: 'border-box',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface-elevated)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button type="button" style={navButtonStyle} onClick={() => shiftMonth(-12)} aria-label={t('work.dateInput.prevYear')}>
                <i className="fa-solid fa-angles-left" />
              </button>
              <button type="button" style={navButtonStyle} onClick={() => shiftMonth(-1)} aria-label={t('work.dateInput.prevMonth')}>
                <i className="fa-solid fa-angle-left" />
              </button>
            </div>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-main)' }}>
              {t('work.dateInput.monthYear', { month: String(viewMonth + 1), year: String(viewYear) })}
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button type="button" style={navButtonStyle} onClick={() => shiftMonth(1)} aria-label={t('work.dateInput.nextMonth')}>
                <i className="fa-solid fa-angle-right" />
              </button>
              <button type="button" style={navButtonStyle} onClick={() => shiftMonth(12)} aria-label={t('work.dateInput.nextYear')}>
                <i className="fa-solid fa-angles-right" />
              </button>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              gap: '2px',
              marginTop: '10px',
              marginBottom: '4px',
            }}
          >
            {WEEKDAY_KEYS.map((key) => (
              <div
                key={key}
                style={{
                  textAlign: 'center',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  color: 'var(--text-muted)',
                  padding: '2px 0',
                }}
              >
                {t(`work.dateInput.${key}`)}
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '2px' }}>
            {days.map((item) => {
              const disabledDay = isOutOfRange(item.iso);
              const selected = item.iso === value;
              const isToday = item.iso === today;
              return (
                <button
                  key={item.iso}
                  type="button"
                  disabled={disabledDay}
                  title={disabledDay ? t('work.dateInput.outOfRangeDay') : undefined}
                  onClick={() => {
                    emit(item.iso);
                    setText(isoToDisplay(item.iso));
                    setHint('');
                    setOpen(false);
                  }}
                  style={{
                    height: '32px',
                    borderRadius: 'var(--radius-sm)',
                    border: isToday && !selected ? '1px solid var(--color-primary)' : '1px solid transparent',
                    background: selected ? 'var(--color-primary)' : 'transparent',
                    color: selected ? '#ffffff' : item.inCurrentMonth ? 'var(--text-main)' : 'var(--text-muted)',
                    fontSize: '0.8rem',
                    fontWeight: selected || isToday ? 700 : 500,
                    cursor: disabledDay ? 'not-allowed' : 'pointer',
                    opacity: disabledDay ? 0.3 : 1,
                  }}
                >
                  {item.day}
                </button>
              );
            })}
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '8px',
              marginTop: '10px',
              paddingTop: '10px',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <button
              type="button"
              onClick={() => {
                if (isOutOfRange(today)) return;
                emit(today);
                setText(isoToDisplay(today));
                setHint('');
                setOpen(false);
              }}
              disabled={isOutOfRange(today)}
              style={{
                border: 'none',
                background: 'transparent',
                color: isOutOfRange(today) ? 'var(--text-muted)' : 'var(--color-primary)',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: isOutOfRange(today) ? 'not-allowed' : 'pointer',
                padding: 0,
              }}
            >
              {t('work.dateInput.today')}
            </button>
            <button
              type="button"
              onClick={() => {
                emit('');
                setText('');
                setHint('');
                setOpen(false);
              }}
              style={{
                border: 'none',
                background: 'transparent',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              {t('work.dateInput.clearDate')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
