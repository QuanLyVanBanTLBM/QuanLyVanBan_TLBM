import { useEffect, useMemo, useState } from 'react';
import { apiClient, ApiError } from '@lib/apiClient';
import { t as translate, useTranslation } from '@i18n/translate';
import BirthdayEmailLogs from './BirthdayEmailLogs';
import './BirthdayPage.css';

export interface BirthdayStaff {
  id: number;
  ho_ten: string;
  ngay: number;
  thang: number;
  chuc_vu: string;
  don_vi: string;
}

export interface CalendarApiResponse {
  success: boolean;
  month: number;
  year: number;
  days_in_month: number;
  total_staff: number;
  days: Record<string, number>;
}

export interface DayApiResponse {
  success: boolean;
  date: string;
  day: number;
  month: number;
  year: number;
  total: number;
  page: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  employees: BirthdayStaff[];
}

interface SelectedDate {
  day: number;
  month: number;
  year: number;
}

interface LoadState<T> {
  key: string;
  data: T | null;
  error: string | null;
}

interface CalendarCell {
  day: number;
  month: number;
  year: number;
  isAdjacent: boolean;
  isSunday: boolean;
}

const WEEKDAY_KEYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const;

function projectToday(): SelectedDate {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  }).formatToParts(new Date());
  const number = (type: string) => Number(parts.find((part) => part.type === type)?.value);
  return { year: number('year'), month: number('month'), day: number('day') };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? translate(error.message) : fallback;
}

export default function BirthdayPage() {
  const { t } = useTranslation();
  const today = useMemo(() => projectToday(), []);
  const [selected, setSelected] = useState<SelectedDate>(today);
  const [displayMonth, setDisplayMonth] = useState(today.month);
  const [displayYear, setDisplayYear] = useState(today.year);
  const [dayPage, setDayPage] = useState(1);
  const [calendarRetry, setCalendarRetry] = useState(0);
  const [dayRetry, setDayRetry] = useState(0);

  // Zoom view state: 'days' | 'months' | 'years'
  const [zoomView, setZoomView] = useState<'days' | 'months' | 'years'>('days');
  const [navYear, setNavYear] = useState<number>(today.year);
  const [decadeStart, setDecadeStart] = useState<number>(Math.floor(today.year / 10) * 10);
  const [slideAnim, setSlideAnim] = useState<'calendar-slide-left' | 'calendar-slide-right' | ''>('');

  const [calendarState, setCalendarState] = useState<LoadState<CalendarApiResponse>>({
    key: '', data: null, error: null,
  });
  const [dayState, setDayState] = useState<LoadState<DayApiResponse>>({
    key: '', data: null, error: null,
  });

  const { day, month, year } = selected;
  const calendarKey = `${year}-${month}-${calendarRetry}`;
  const dayKey = `${year}-${month}-${day}-${dayPage}-${dayRetry}`;
  const calendarLoading = calendarState.key !== calendarKey;
  const dayLoading = dayState.key !== dayKey;
  const calendarData = calendarLoading ? null : calendarState.data;
  const dayData = dayLoading ? null : dayState.data;
  const calendarError = calendarLoading ? null : calendarState.error;
  const dayError = dayLoading ? null : dayState.error;

  useEffect(() => {
    let active = true;
    apiClient.get<CalendarApiResponse>(`/api/birthdays/calendar/?month=${month}&year=${year}`)
      .then((data) => {
        if (active) setCalendarState({ key: calendarKey, data, error: null });
      })
      .catch((error: unknown) => {
        if (active) setCalendarState({ key: calendarKey, data: null, error: errorMessage(error, translate('birthdayPage.calendarError')) });
      });
    return () => { active = false; };
  }, [calendarKey, month, year]);

  useEffect(() => {
    let active = true;
    apiClient.get<DayApiResponse>(
      `/api/birthdays/day/?month=${month}&day=${day}&year=${year}&page=${dayPage}&page_size=10`
    )
      .then((data) => {
        if (active) setDayState({ key: dayKey, data, error: null });
      })
      .catch((error: unknown) => {
        if (active) setDayState({ key: dayKey, data: null, error: errorMessage(error, translate('birthdayPage.dayError')) });
      });
    return () => { active = false; };
  }, [dayKey, day, month, year, dayPage]);

  // Full calendar grid cells with trailing previous month and leading next month days
  const calendarCells = useMemo((): CalendarCell[] => {
    const firstWeekday = new Date(year, month - 1, 1).getDay();
    const offset = (firstWeekday + 6) % 7; // Monday = 0, Sunday = 6
    const daysInMonth = new Date(year, month, 0).getDate();
    const prevMonthDays = new Date(year, month - 1, 0).getDate();

    const totalCells = Math.ceil((offset + daysInMonth) / 7) * 7;
    const cells: CalendarCell[] = [];

    for (let i = 0; i < totalCells; i++) {
      const colIndex = i % 7;
      const isSunday = colIndex === 6;

      if (i < offset) {
        // Previous month trailing days
        const d = prevMonthDays - (offset - 1 - i);
        let m = month - 1;
        let y = year;
        if (m === 0) { m = 12; y--; }
        cells.push({ day: d, month: m, year: y, isAdjacent: true, isSunday });
      } else if (i >= offset + daysInMonth) {
        // Next month leading days
        const d = i - (offset + daysInMonth) + 1;
        let m = month + 1;
        let y = year;
        if (m === 13) { m = 1; y++; }
        cells.push({ day: d, month: m, year: y, isAdjacent: true, isSunday });
      } else {
        // Current month days
        const d = i - offset + 1;
        cells.push({ day: d, month, year, isAdjacent: false, isSunday });
      }
    }

    return cells;
  }, [month, year]);

  const selectDate = (date: SelectedDate) => {
    setSelected(date);
    setDisplayMonth(date.month);
    setDisplayYear(date.year);
    setDayPage(1);
    setNavYear(date.year);
    setDecadeStart(Math.min(2090, Math.floor(date.year / 10) * 10));
    setZoomView('days');
  };

  const changeMonth = (step: -1 | 1) => {
    const next = new Date(year, month - 1 + step, 1);
    const nextYear = next.getFullYear();
    if (nextYear >= 1900 && nextYear <= 2100) {
      setSlideAnim(step === 1 ? 'calendar-slide-left' : 'calendar-slide-right');
      const nextMonth = next.getMonth() + 1;
      const lastDay = new Date(nextYear, nextMonth, 0).getDate();
      selectDate({ day: Math.min(day, lastDay), month: nextMonth, year: nextYear });
    }
  };

  const handleHeaderTitleClick = () => {
    if (zoomView === 'days') {
      setSlideAnim('calendar-slide-left');
      setNavYear(year);
      setDisplayMonth(month);
      setDisplayYear(year);
      setZoomView('months');
    } else if (zoomView === 'months') {
      setSlideAnim('calendar-slide-left');
      setNavYear(displayYear);
      setDecadeStart(Math.min(2090, Math.floor(displayYear / 10) * 10));
      setZoomView('years');
    } else {
      setSlideAnim('calendar-slide-right');
      setZoomView('months');
    }
  };

  const handlePrev = () => {
    setSlideAnim('calendar-slide-right');
    if (zoomView === 'days') {
      changeMonth(-1);
    } else if (zoomView === 'months') {
      const nextYear = Math.max(1900, navYear - 1);
      setNavYear(nextYear);
      setDisplayYear(nextYear);
    } else if (zoomView === 'years') {
      setDecadeStart((prev) => Math.max(1900, prev - 12));
    }
  };

  const handleNext = () => {
    setSlideAnim('calendar-slide-left');
    if (zoomView === 'days') {
      changeMonth(1);
    } else if (zoomView === 'months') {
      const nextYear = Math.min(2100, navYear + 1);
      setNavYear(nextYear);
      setDisplayYear(nextYear);
    } else if (zoomView === 'years') {
      setDecadeStart((prev) => Math.min(2090, prev + 12));
    }
  };

  const selectMonthFromGrid = (m: number) => {
    const maxDay = new Date(displayYear, m, 0).getDate();
    selectDate({ day: Math.min(day, maxDay), month: m, year: displayYear });
    setSlideAnim('calendar-slide-right');
    setZoomView('days');
  };

  const selectYearFromGrid = (y: number) => {
    setNavYear(y);
    setDisplayYear(y);
    setSlideAnim('calendar-slide-right');
    setZoomView('months');
  };

  return (
    <main className="birthday-calendar-page space-y-4 pb-28 sm:pb-8">
      <h1 className="sr-only">{t('birthdayPage.title')}</h1>
      {/* Bố cục 7:3 - Cột trái 7 phần (Lịch), Cột phải 3 phần (Chi tiết) */}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-10">

        {/* CỘT TRÁI (7 PHẦN): LỊCH THÁNG TRUYỀN THỐNG */}
        <section
          aria-label={t('birthdayPage.calendarLabel')}
          className="birthday-calendar-panel flex flex-col overflow-hidden rounded-[4px] border border-border bg-surface shadow-xs lg:col-span-7"
        >
          <div className="birthday-calendar-nav flex min-h-12 flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2 sm:px-4">
            {/* Left: Navigation and Multi-level Zoom Title */}
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={handlePrev}
                disabled={
                  (zoomView === 'days' && year === 1900 && month === 1)
                  || (zoomView === 'months' && navYear === 1900)
                  || (zoomView === 'years' && decadeStart === 1900)
                }
                aria-label={
                  zoomView === 'days'
                    ? t('birthdayPage.previousMonth')
                    : zoomView === 'months'
                      ? t('birthdayPage.previousYear')
                      : t('birthdayPage.previousDecade')
                }
                className="birthday-control-button flex h-9 w-9 items-center justify-center rounded-[3px] border border-border text-lg font-bold text-primary transition-colors hover:bg-primary-subtle active:bg-primary-subtle disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
              >
                ‹
              </button>

              <button
                type="button"
                onClick={handleHeaderTitleClick}
                aria-label={
                    zoomView === 'days'
                      ? t('birthdayPage.zoomToMonthView')
                    : zoomView === 'months'
                      ? t('birthdayPage.zoomToYearView')
                      : t('birthdayPage.returnToMonthPicker')
                }
                className="birthday-control-button group flex items-center gap-1.5 rounded-[3px] px-2.5 py-1 text-main transition-colors hover:bg-surface-hover active:bg-primary-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
              >
                <span className="text-base font-bold sm:text-lg">
                  {zoomView === 'days' && (
                    t('birthdayPage.monthYear', { month: String(month), year: String(year) })
                  )}
                  {zoomView === 'months' && (
                    t('birthdayPage.yearTitle', { year: String(navYear) })
                  )}
                  {zoomView === 'years' && (
                    t('birthdayPage.decadeTitle', { start: String(decadeStart), end: String(decadeStart + 11) })
                  )}
                </span>
                <span className="text-xs text-primary transition-transform group-hover:translate-y-0.5" aria-hidden="true">
                  ▼
                </span>
              </button>

              <button
                type="button"
                onClick={handleNext}
                disabled={
                  (zoomView === 'days' && year === 2100 && month === 12)
                  || (zoomView === 'months' && navYear === 2100)
                  || (zoomView === 'years' && decadeStart >= 2090)
                }
                aria-label={
                  zoomView === 'days'
                    ? t('birthdayPage.nextMonth')
                    : zoomView === 'months'
                      ? t('birthdayPage.nextYear')
                      : t('birthdayPage.nextDecade')
                }
                className="birthday-control-button flex h-9 w-9 items-center justify-center rounded-[3px] border border-border text-lg font-bold text-primary transition-colors hover:bg-primary-subtle active:bg-primary-subtle disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
              >
                ›
              </button>
              <button
                type="button"
                onClick={() => {
                  setSlideAnim('calendar-slide-right');
                  selectDate(today);
                }}
                className="birthday-control-button ml-1 rounded-[3px] border border-primary/25 px-2.5 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 sm:text-sm"
              >
                {t('birthdayPage.today')}
              </button>
            </div>
          </div>

          {/* MULTI-LEVEL ZOOM CONTAINER (Windows 11 Calendar Style) */}
          <div className="p-3 sm:p-4 flex-1 min-h-[460px]">

            {/* LAYER 1: DAYS VIEW (Lưới ngày truyền thống) */}
            {zoomView === 'days' && (
              <div key={`days-${year}-${month}`} className={`w-full ${slideAnim}`}>
                {/* Weekdays Header Row */}
                <div className="birthday-calendar-weekdays mb-3.5 grid grid-cols-7 border-b border-border pb-2.5 text-xs font-bold text-secondary sm:text-sm">
                  {WEEKDAY_KEYS.map((key) => {
                    const isSunday = key === 'sunday';
                    return (
                      <div
                        key={key}
                        className={`flex min-w-0 items-center justify-center px-0.5 py-1 text-center leading-tight ${isSunday ? 'text-danger' : ''}`}
                      >
                        <span className="hidden sm:inline">{t(`birthdayPage.fullWeekdays.${key}`)}</span>
                        <span className="sm:hidden">{t(`birthdayPage.weekdays.${key}`)}</span>
                      </div>
                    );
                  })}
                </div>

                {calendarLoading ? (
                  <div className="flex min-h-64 items-center justify-center text-sm text-muted" role="status">
                    {t('birthdayPage.calendarLoading')}
                  </div>
                ) : calendarError ? (
                  <div className="flex min-h-64 flex-col items-center justify-center gap-3 p-6 text-center" role="alert">
                    <p className="text-sm text-danger">{calendarError}</p>
                    <button
                      type="button"
                      onClick={() => setCalendarRetry((v) => v + 1)}
                      className="rounded-xs bg-danger px-3 py-1.5 text-sm font-semibold text-white hover:bg-danger-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"
                    >
                      {t('birthdayPage.retry')}
                    </button>
                  </div>
                ) : (
                  <div className="birthday-calendar-days-grid bg-surface">
                    {calendarCells.map((cell, idx) => {
                      const birthdayCount = cell.isAdjacent ? 0 : (calendarData?.days[String(cell.day)] ?? 0);
                      const isSelected = cell.day === day && cell.month === month && cell.year === year;
                      const isToday = cell.day === today.day && cell.month === today.month && cell.year === today.year && !cell.isAdjacent;

                      return (
                        <button
                          key={`${cell.year}-${cell.month}-${cell.day}-${idx}`}
                          type="button"
                          onClick={() => selectDate({ day: cell.day, month: cell.month, year: cell.year })}
                          aria-label={t('birthdayPage.selectDay', { day: String(cell.day), month: String(cell.month), year: String(cell.year) })}
                          aria-pressed={isSelected}
                          aria-current={isToday ? 'date' : undefined}
                          className={`birthday-calendar-day-cell group relative flex min-w-0 flex-col justify-between p-1.5 text-left transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 sm:p-2.5 ${
                            isSelected
                              ? 'bg-primary-subtle ring-2 ring-inset ring-primary z-20'
                              : cell.isAdjacent
                                ? 'bg-app/40 opacity-40 hover:opacity-75 hover:bg-surface-hover'
                                : 'hover:bg-surface-hover'
                          }`}
                        >
                          <div className="birthday-calendar-day-heading flex h-7 items-center justify-between sm:h-8">
                            <span
                              className={`birthday-calendar-day-number text-xl leading-none font-bold sm:text-2xl ${
                                cell.isAdjacent
                                  ? 'text-muted'
                                  : cell.isSunday
                                    ? 'text-danger'
                                    : isSelected
                                      ? 'text-primary'
                                      : 'text-main'
                              } ${isToday ? 'underline decoration-primary decoration-2 underline-offset-4' : ''}`}
                            >
                              {String(cell.day).padStart(2, '0')}
                            </span>

                            <span
                              className={`birthday-calendar-today-indicator h-2.5 w-2.5 shrink-0 rounded-full bg-info ring-2 ring-info-subtle ${isToday ? '' : 'invisible'}`}
                              aria-hidden="true"
                              title={isToday ? t('birthdayPage.today') : undefined}
                            />
                          </div>

                          <div className="birthday-calendar-badge-slot mt-1 flex h-6 items-center justify-start">
                            {birthdayCount > 0 && (
                              <span
                                className="birthday-calendar-count-badge inline-flex h-5 items-center gap-1 rounded-[4px] bg-pink px-1.5 text-[11px] font-bold leading-none text-white shadow-xs"
                                title={t('birthdayPage.birthdayCount', { count: String(birthdayCount) })}
                                aria-label={t('birthdayPage.birthdayCount', { count: String(birthdayCount) })}
                              >
                                <span aria-hidden="true">🎂</span>
                                <span>{birthdayCount}</span>
                              </span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* LAYER 2: MONTHS VIEW (Lưới 12 tháng) */}
            {zoomView === 'months' && (
              <div key={`months-${navYear}`} className={`w-full ${slideAnim}`}>
                <div className="mb-3 border-b border-border pb-2">
                  <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-secondary">
                    {t('birthdayPage.selectMonthPrompt')}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-2 py-3 sm:gap-3">
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
                    const isCurrent = m === displayMonth;
                    return (
                      <button
                        key={m}
                        type="button"
                        onClick={() => selectMonthFromGrid(m)}
                        aria-label={t('birthdayPage.monthTitle', { month: String(m) })}
                        aria-pressed={isCurrent}
                        className={`birthday-picker-choice flex min-h-[56px] items-center justify-center rounded-[3px] border px-0.5 py-2 text-center text-[11px] font-semibold transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:min-h-[64px] sm:text-sm ${
                          isCurrent
                            ? 'border-primary bg-primary text-white'
                            : 'border-border bg-surface text-main hover:border-primary/40 hover:bg-surface-hover'
                        }`}
                      >
                        {t('birthdayPage.monthTitle', { month: String(m) })}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* LAYER 3: YEARS VIEW (Lưới 12 năm thập kỷ) */}
            {zoomView === 'years' && (
              <div key={`years-${decadeStart}`} className={`w-full ${slideAnim}`}>
                <div className="mb-3 border-b border-border pb-2">
                  <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-secondary">
                    {t('birthdayPage.selectYearPrompt')}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-2 py-3 sm:gap-3">
                  {Array.from({ length: 12 }, (_, i) => decadeStart + i)
                    .filter((yearValue) => yearValue <= 2100)
                    .map((y) => {
                    const isCurrent = y === navYear;
                    return (
                      <button
                        key={y}
                        type="button"
                        onClick={() => selectYearFromGrid(y)}
                        aria-label={String(y)}
                        aria-pressed={isCurrent}
                        className={`birthday-picker-choice flex min-h-[56px] items-center justify-center rounded-[3px] border px-1 py-2 text-center text-sm font-semibold transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:min-h-[64px] sm:text-base ${
                          isCurrent
                            ? 'border-primary bg-primary text-white'
                            : 'border-border bg-surface text-main hover:border-primary/40 hover:bg-surface-hover'
                        }`}
                      >
                        {y}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

          </div>
        </section>

        {/* CỘT PHẢI (3 PHẦN): DANH SÁCH SINH NHẬT THEO NGÀY */}
        <section
          aria-label={t('birthdayPage.detailsLabel')}
          className="sticky top-6 flex flex-col justify-between rounded-xl border border-border bg-surface p-4 shadow-xs sm:p-5 lg:col-span-3"
        >
          <div>
            <div className="border-b border-border pb-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-bold text-main sm:text-base">
                  {t('birthdayPage.selectedDate', { day: String(day), month: String(month), year: String(year) })}
                </h2>
                <span className="h-2.5 w-2.5 rounded-full bg-primary" aria-hidden="true" />
              </div>
              {dayData && (
                <p className="mt-0.5 text-xs text-secondary">
                  {t('birthdayPage.staffCount', { count: String(dayData.total) })}
                </p>
              )}
            </div>

            {dayLoading ? (
              <div className="py-12 text-center text-sm text-muted" role="status">
                {t('birthdayPage.dayLoading')}
              </div>
            ) : dayError ? (
              <div className="space-y-3 py-12 text-center" role="alert">
                <p className="text-sm text-danger">{dayError}</p>
                <button
                  type="button"
                  onClick={() => setDayRetry((v) => v + 1)}
                  className="rounded-xs bg-danger px-3 py-1.5 text-sm font-semibold text-white hover:bg-danger-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"
                >
                  {t('birthdayPage.retry')}
                </button>
              </div>
            ) : (dayData?.employees?.length ?? 0) === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center text-secondary">
                <p className="text-xs font-medium text-secondary">{t('birthdayPage.emptyDay')}</p>
              </div>
            ) : (
              <ul className="mt-3.5 space-y-2.5 max-h-[560px] overflow-y-auto pr-1">
                {(dayData?.employees ?? []).map((staff) => (
                  <li
                    key={staff.id}
                    className="flex min-w-0 items-start gap-3 rounded-[6px] border border-border bg-surface p-3.5 shadow-xs transition hover:bg-surface-hover/60 hover:border-primary/40"
                  >
                    <span
                      aria-hidden="true"
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-white shadow-xs"
                    >
                      {staff.ho_ten.charAt(0)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-main">
                        {staff.ho_ten}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-secondary">
                        {staff.chuc_vu}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {staff.don_vi}
                      </p>
                      <div className="mt-1 flex items-center justify-between">
                        <span className="inline-flex items-center gap-1 rounded-[4px] border border-pink-border bg-pink-subtle px-2 py-0.5 text-xs font-semibold text-pink">
                          <span aria-hidden="true">🎂</span>
                          <span>{t('birthdayPage.birthDayMonth', { day: String(staff.ngay), month: String(staff.thang) })}</span>
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Phân trang danh sách sinh nhật */}
          {dayData && dayData.total_pages > 1 && (
            <nav
              aria-label={t('birthdayPage.paginationLabel')}
              className="mt-4 flex items-center justify-between gap-2 border-t border-border pt-3 text-xs text-secondary"
            >
              <button
                type="button"
                disabled={!dayData.has_previous}
                onClick={() => setDayPage(dayData.page - 1)}
                className="rounded-xs bg-surface-hover px-2.5 py-1 text-main disabled:opacity-40 hover:bg-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
              >
                {t('birthdayPage.previousPage')}
              </button>
              <span>{t('birthdayPage.pageCount', { page: String(dayData.page), total: String(dayData.total_pages) })}</span>
              <button
                type="button"
                disabled={!dayData.has_next}
                onClick={() => setDayPage(dayData.page + 1)}
                className="rounded-xs bg-surface-hover px-2.5 py-1 text-main disabled:opacity-40 hover:bg-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1"
              >
                {t('birthdayPage.nextPage')}
              </button>
            </nav>
          )}
        </section>

      </div>

      <BirthdayEmailLogs month={displayMonth} year={displayYear} />
    </main>
  );
}
