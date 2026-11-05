import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError, apiClient } from '@lib/apiClient';
import { setLanguage } from '@i18n/translate';
import BirthdayPage, { type CalendarApiResponse, type DayApiResponse } from './BirthdayPage';

const calendar: CalendarApiResponse = {
  success: true,
  month: 5,
  year: 2026,
  days_in_month: 31,
  total_staff: 1,
  days: { '12': 1 },
};

const emptyDay: DayApiResponse = {
  success: true,
  date: '12/05/2026',
  day: 12,
  month: 5,
  year: 2026,
  total: 0,
  page: 1,
  total_pages: 1,
  has_next: false,
  has_previous: false,
  employees: [],
};

describe('BirthdayPage', () => {
  beforeEach(() => {
    setLanguage('vi');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('shows loading states while both requests are pending', () => {
    vi.spyOn(apiClient, 'get').mockImplementation(() => new Promise(() => {}));
    render(<BirthdayPage />);

    expect(screen.getByText('Đang tải lịch sinh nhật...')).toBeInTheDocument();
    expect(screen.getByText('Đang tải danh sách sinh nhật...')).toBeInTheDocument();
  });

  it('filters logs by date/status, returns to today, and refreshes without sending email', async () => {
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      if (url.includes('/day/')) return emptyDay as never;
      return { success: true, date: null, total: 0, page: 1, total_pages: 1, logs: [] } as never;
    });
    const post = vi.spyOn(apiClient, 'post');
    const todayParts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(new Date());
    const today = `${todayParts.find((part) => part.type === 'year')?.value}-${todayParts.find((part) => part.type === 'month')?.value}-${todayParts.find((part) => part.type === 'day')?.value}`;
    render(<BirthdayPage />);

    const dateFilter = screen.getByLabelText('Ngày xem') as HTMLInputElement;
    expect(dateFilter.value).toBe(today);
    await screen.findByText('Tổng số bản ghi: 0');
    expect(get.mock.calls.some(([url]) => String(url).includes(`/logs/?date=${today}&page=1`))).toBe(true);

    fireEvent.change(dateFilter, { target: { value: '2026-11-03' } });
    fireEvent.change(screen.getByLabelText('Lọc trạng thái'), { target: { value: 'FAILED' } });
    await waitFor(() => {
      expect(get.mock.calls.some(([url]) => String(url).includes('/logs/?date=2026-11-03&page=1&trang_thai=FAILED'))).toBe(true);
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'Hôm nay' })[1]);
    await waitFor(() => expect(dateFilter.value).toBe(today));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Tải lại nhật ký' })).toBeEnabled());

    const requestsBeforeRefresh = get.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: 'Tải lại nhật ký' }));
    await waitFor(() => expect(get.mock.calls.length).toBe(requestsBeforeRefresh + 1));
    expect(String(get.mock.calls.at(-1)?.[0])).toContain('/logs/');
    expect(post).not.toHaveBeenCalled();
  });

  it('shows the empty state when today has no birthday email log entries', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      if (url.includes('/day/')) return emptyDay as never;
      return { success: true, date: null, total: 0, page: 1, total_pages: 1, logs: [] } as never;
    });
    render(<BirthdayPage />);

    expect(await screen.findByText('Chưa có nhật ký gửi email sinh nhật trong ngày hôm nay.')).toBeInTheDocument();
    expect(screen.getByText('Tổng số bản ghi: 0')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows an explicit error when the birthday email log request fails', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      if (url.includes('/day/')) return emptyDay as never;
      throw new ApiError(500, { error: 'server error' });
    });
    render(<BirthdayPage />);

    expect(await screen.findByText('Không thể tải nhật ký email.')).toBeInTheDocument();
    expect(screen.queryByText('Chưa có nhật ký gửi email sinh nhật trong ngày hôm nay.')).not.toBeInTheDocument();
  });

  it('advances today mode at Vietnam midnight and keeps a historical date selected', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-04T16:59:00.000Z'));
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      if (url.includes('/day/')) return emptyDay as never;
      return { success: true, date: null, total: 0, page: 1, total_pages: 1, logs: [] } as never;
    });
    render(<BirthdayPage />);
    const dateFilter = screen.getByLabelText('Ngày xem') as HTMLInputElement;
    expect(dateFilter.value).toBe('2026-11-04');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(61_000);
    });
    expect(dateFilter.value).toBe('2026-11-05');
    expect(get.mock.calls.some(([url]) => String(url).includes('/logs/?date=2026-11-05&page=1'))).toBe(true);

    fireEvent.change(dateFilter, { target: { value: '2026-11-03' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(24 * 60 * 60 * 1000);
    });
    expect(dateFilter.value).toBe('2026-11-03');
  });

  it('shows calendar counts and only permitted staff fields', async () => {
    const day: DayApiResponse = {
      ...emptyDay,
      total: 1,
      employees: [{
        id: 7,
        ho_ten: 'Nguyễn Văn Minh',
        ngay: 12,
        thang: 5,
        chuc_vu: 'Chuyên viên',
        don_vi: 'Văn phòng',
      }],
    };
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : day) as never
    );
    render(<BirthdayPage />);

    expect(await screen.findByText('Nguyễn Văn Minh')).toBeInTheDocument();
    expect(screen.getByText('Ngày sinh nhật: 12/5')).toBeInTheDocument();
    expect(screen.getByTitle('1 cán bộ nhân viên có sinh nhật')).toBeInTheDocument();
    expect(screen.queryByText(/Gửi thiệp|Gửi email tự động/)).not.toBeInTheDocument();
  });

  it.each([
    ['vi', 'Bạn không có quyền thực hiện thao tác này.'],
    ['en', 'You do not have permission to perform this action.'],
  ] as const)('translates permission errors in both birthday panels (%s)', async (language, message) => {
    setLanguage(language);
    vi.spyOn(apiClient, 'get').mockRejectedValue(
      new ApiError(403, { detail: 'roles.messages.permissionDenied' })
    );
    render(<BirthdayPage />);

    expect(await screen.findAllByText(message)).toHaveLength(2);
    expect(screen.queryByText('roles.messages.permissionDenied')).not.toBeInTheDocument();
  });

  it('distinguishes an empty day from a failed day request and retries', async () => {
    let dayAttempts = 0;
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      if (url.includes('/logs/')) return { success: true, total: 0, page: 1, total_pages: 1, logs: [] } as never;
      dayAttempts += 1;
      if (dayAttempts === 1) throw new Error('Temporary failure');
      return emptyDay as never;
    });
    render(<BirthdayPage />);

    expect(await screen.findByText('Không thể tải danh sách sinh nhật theo ngày.')).toBeInTheDocument();
    expect(screen.queryByText('Không có cán bộ nhân viên nào sinh vào ngày này.')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByText('Không có cán bộ nhân viên nào sinh vào ngày này.')).toBeInTheDocument();
    expect(dayAttempts).toBe(2);
  });

  it('shows a calendar error and reloads the monthly counts', async () => {
    let calendarAttempts = 0;
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/day/')) return emptyDay as never;
      if (url.includes('/logs/')) return { success: true, total: 0, page: 1, total_pages: 1, logs: [] } as never;
      calendarAttempts += 1;
      if (calendarAttempts === 1) throw new Error('Temporary failure');
      return calendar as never;
    });
    render(<BirthdayPage />);

    expect(await screen.findByText('Không thể tải lịch sinh nhật.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByTitle('1 cán bộ nhân viên có sinh nhật')).toBeInTheDocument();
    expect(calendarAttempts).toBe(2);
  });

  it('loads the next page from the day endpoint', async () => {
    const firstPage: DayApiResponse = {
      ...emptyDay,
      total: 11,
      total_pages: 2,
      has_next: true,
      employees: [{ id: 1, ho_ten: 'Người đầu', ngay: 12, thang: 5, chuc_vu: 'Nhân viên', don_vi: 'Đơn vị A' }],
    };
    const secondPage: DayApiResponse = {
      ...firstPage,
      page: 2,
      has_next: false,
      has_previous: true,
      employees: [{ id: 2, ho_ten: 'Người sau', ngay: 12, thang: 5, chuc_vu: 'Nhân viên', don_vi: 'Đơn vị B' }],
    };
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/')) return calendar as never;
      return (url.includes('page=2') ? secondPage : firstPage) as never;
    });
    render(<BirthdayPage />);

    expect(await screen.findByText('Người đầu')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Trang sau' }));
    expect(await screen.findByText('Người sau')).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledWith(expect.stringContaining('page=2&page_size=10')));
  });

  it('requests the adjacent months and the selected day', async () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: 'numeric', day: 'numeric',
    }).formatToParts(new Date());
    const todayYear = Number(parts.find((part) => part.type === 'year')?.value);
    const todayMonth = Number(parts.find((part) => part.type === 'month')?.value);
    const next = new Date(todayYear, todayMonth, 1);
    const nextMonth = next.getMonth() + 1;
    const nextYear = next.getFullYear();
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    fireEvent.click(screen.getByRole('button', { name: 'Tháng sau' }));
    await waitFor(() => expect(get).toHaveBeenCalledWith(
      `/api/birthdays/calendar/?month=${nextMonth}&year=${nextYear}`
    ));
    expect(screen.getByText(`Tháng ${nextMonth} / ${nextYear}`)).toBeInTheDocument();

    fireEvent.click(await screen.findByRole('button', { name: `Chọn ngày 13/${nextMonth}/${nextYear}` }));
    await waitFor(() => expect(get).toHaveBeenCalledWith(
      `/api/birthdays/day/?month=${nextMonth}&day=13&year=${nextYear}&page=1&page_size=10`
    ));

    fireEvent.click(screen.getByRole('button', { name: 'Tháng trước' }));
    expect(screen.getByText(`Tháng ${todayMonth} / ${todayYear}`)).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledWith(
      `/api/birthdays/day/?month=${todayMonth}&day=13&year=${todayYear}&page=1&page_size=10`
    ));
  });

  it('allows zooming out to months view and selecting a month', async () => {
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Click header title to zoom out to months view
    const headerTitleBtn = screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i });
    act(() => {
      fireEvent.click(headerTitleBtn);
    });

    // Month buttons (Tháng 1 to Tháng 12) should be displayed
    expect(screen.getByRole('button', { name: 'Tháng 8' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tháng 10' })).toBeInTheDocument();

    // Clicking Tháng 10 zooms back in to days view and loads month 10
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 10' }));
    });
    await waitFor(() => expect(get).toHaveBeenCalledWith(
      expect.stringContaining('/api/birthdays/calendar/?month=10')
    ));
  });

  it('allows zooming out to decade years view and selecting a year', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Click header title to go to months view
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });

    // Click year button to zoom out to years view
    const zoomToYearsBtn = screen.getByRole('button', { name: /Bấm để xem danh sách năm/i });
    act(() => {
      fireEvent.click(zoomToYearsBtn);
    });

    // Year buttons should be displayed
    expect(screen.getByRole('button', { name: '2025' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2027' })).toBeInTheDocument();

    // Click year 2027 to zoom back to months view for 2027
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: '2027' }));
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Tháng 1' })).toBeInTheDocument();
    });
  });

  it('handles year boundary navigation across December and January', async () => {
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Switch to month view, select 2026, then Tháng 12
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 12' }));
    });
    await waitFor(() => expect(screen.getByText('Tháng 12 / 2026')).toBeInTheDocument());

    // Click next month: should roll over to Tháng 1 / 2027
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng sau' }));
    });
    await waitFor(() => expect(screen.getByText('Tháng 1 / 2027')).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith(expect.stringContaining('month=1&year=2027'));

    // Click previous month: should roll back to Tháng 12 / 2026
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng trước' }));
    });
    await waitFor(() => expect(screen.getByText('Tháng 12 / 2026')).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith(expect.stringContaining('month=12&year=2026'));
  });

  it('correctly handles February in leap year (2024: 29 days) vs non-leap year (2025: 28 days)', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? { ...calendar, month: 2, year: 2024, days_in_month: 29 } : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Select Year 2024 -> Tháng 2
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách năm/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: '2024' }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 2' }));
    });

    // In 2024 leap year, 29th of Feb must exist
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Chọn ngày 29/2/2024' })).toBeInTheDocument();
    });

    // Switch to 2025 non-leap year
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách năm/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: '2025' }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 2' }));
    });

    // In 2025 non-leap year, 29/2/2025 does NOT exist as a current-month day
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Chọn ngày 28/2/2025' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Chọn ngày 29/2/2025' })).not.toBeInTheDocument();
    });
  });

  it('preserves month highlight when navigating and selecting year in year picker', async () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: 'numeric', day: 'numeric',
    }).formatToParts(new Date());
    const currentMonth = Number(parts.find((part) => part.type === 'month')?.value);

    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Go to month view
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    // Current month should be marked as pressed
    const currentMonthBtn = screen.getByRole('button', { name: `Tháng ${currentMonth}` });
    expect(currentMonthBtn).toHaveAttribute('aria-pressed', 'true');

    // Go to year view and select 2025
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách năm/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: '2025' }));
    });

    // In month picker for year 2025, current month must STILL have aria-pressed="true"
    await waitFor(() => {
      expect(screen.getByRole('button', { name: `Tháng ${currentMonth}` })).toHaveAttribute('aria-pressed', 'true');
    });

    // Selecting current month switches to days view of year 2025
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: `Tháng ${currentMonth}` }));
    });
    await waitFor(() => {
      expect(screen.getByText(`Tháng ${currentMonth} / 2025`)).toBeInTheDocument();
    });
  });

  it('renders independent visual states when today is also selected day', async () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: 'numeric', day: 'numeric',
    }).formatToParts(new Date());
    const todayDay = Number(parts.find((part) => part.type === 'day')?.value);
    const todayMonth = Number(parts.find((part) => part.type === 'month')?.value);
    const todayYear = Number(parts.find((part) => part.type === 'year')?.value);

    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // Initially today is selected
    const todayBtn = await screen.findByRole('button', { name: `Chọn ngày ${todayDay}/${todayMonth}/${todayYear}` });
    expect(todayBtn).toHaveAttribute('aria-pressed', 'true');
    expect(todayBtn).toHaveAttribute('aria-current', 'date');
    expect(screen.getByTitle('Hôm nay')).toBeInTheDocument();

    // Select a different day (e.g. day 1 if today is not 1, otherwise day 2)
    const otherDay = todayDay === 1 ? 2 : 1;
    const otherBtn = screen.getByRole('button', { name: `Chọn ngày ${otherDay}/${todayMonth}/${todayYear}` });
    fireEvent.click(otherBtn);

    // Now other day is selected, but not today
    await waitFor(() => {
      expect(otherBtn).toHaveAttribute('aria-pressed', 'true');
    });
    expect(otherBtn).not.toHaveAttribute('aria-current');

    // Today is no longer selected, but still has today marker
    expect(todayBtn).toHaveAttribute('aria-pressed', 'false');
    expect(todayBtn).toHaveAttribute('aria-current', 'date');
    expect(screen.getByTitle('Hôm nay')).toBeInTheDocument();
  });

  it('uses month and year pickers without resetting the selected day or month', async () => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: 'numeric', day: 'numeric',
    }).formatToParts(new Date());
    const todayDay = Number(parts.find((part) => part.type === 'day')?.value);
    const todayYear = Number(parts.find((part) => part.type === 'year')?.value);
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Tháng 10' }));
    await waitFor(() => expect(screen.getByText(`Tháng 10 / ${todayYear}`)).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith(expect.stringContaining(`month=10&day=${todayDay}&year=${todayYear}`));

    const chooseYearAndReturnToOctober = async (year: number) => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách năm/i }));
      fireEvent.click(screen.getByRole('button', { name: String(year) }));

      const octoberButton = await screen.findByRole('button', { name: 'Tháng 10' });
      expect(octoberButton).toHaveAttribute('aria-pressed', 'true');
      fireEvent.click(octoberButton);

      await waitFor(() => expect(screen.getByText(`Tháng 10 / ${year}`)).toBeInTheDocument());
      expect(get).toHaveBeenCalledWith(expect.stringContaining(`month=10&day=${todayDay}&year=${year}`));
    };

    // Changing only the year leaves October highlighted and keeps the selected day.
    await chooseYearAndReturnToOctober(2025);
    await chooseYearAndReturnToOctober(2026);
    await chooseYearAndReturnToOctober(2025);
  });

  it('updates navigation button ARIA labels according to current zoom level', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) =>
      (url.includes('/calendar/') ? calendar : emptyDay) as never
    );
    render(<BirthdayPage />);

    // In days view: Tháng trước / Tháng sau
    expect(await screen.findByRole('button', { name: 'Tháng trước' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tháng sau' })).toBeInTheDocument();

    // Switch to month view: Năm trước / Năm sau
    fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Năm trước' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Năm sau' })).toBeInTheDocument();

    // Switch to year view: 12 năm trước / 12 năm sau
    fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách năm/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '12 năm trước' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: '12 năm sau' })).toBeInTheDocument();
  });

  it('ignores out-of-order API responses so stale data does not overwrite newer data', async () => {
    let resolveFirst: ((val: unknown) => void) | null = null;
    const firstPromise = new Promise((resolve) => { resolveFirst = resolve; });

    const month1Data = { ...calendar, month: 1, days: { '10': 5 } };
    const month2Data = { ...calendar, month: 2, days: { '15': 9 } };

    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url.includes('/calendar/?month=1&')) {
        return firstPromise as never;
      }
      if (url.includes('/calendar/?month=2&')) {
        return month2Data as never;
      }
      return emptyDay as never;
    });

    render(<BirthdayPage />);

    // Go to month view and select Tháng 1 (starts slow request)
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 1' }));
    });

    // Quickly select Tháng 2 (starts fast request)
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /Bấm để xem danh sách tháng/i }));
    });
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Tháng 2' }));
    });

    // Month 2 resolves and shows its badge
    expect(await screen.findByTitle('9 cán bộ nhân viên có sinh nhật')).toBeInTheDocument();

    // Now slow month 1 request resolves late
    act(() => {
      if (resolveFirst) resolveFirst(month1Data);
    });

    // Wait a tick: badge from month 1 (5 count) must NOT overwrite month 2 (9 count)
    expect(screen.queryByTitle('5 cán bộ nhân viên có sinh nhật')).not.toBeInTheDocument();
    expect(screen.getByTitle('9 cán bộ nhân viên có sinh nhật')).toBeInTheDocument();
  });
});
