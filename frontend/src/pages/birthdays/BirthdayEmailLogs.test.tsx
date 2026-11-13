import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { setLanguage } from '@i18n/translate';
import { ApiError, apiClient } from '@lib/apiClient';
import BirthdayEmailLogs from './BirthdayEmailLogs';

const permissionState = vi.hoisted(() => ({ isSystemAdmin: true }));
vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({ isSystemAdmin: permissionState.isSystemAdmin }),
}));

const templates = [
  { id: 'layout:01', layout: '01', name: null, subject: 'Lời chúc', message: 'Chúc mừng sinh nhật' },
  { id: 'layout:02', layout: '02', name: null, subject: 'Thư chúc', message: 'Chúc mừng sinh nhật' },
];
const recipients = [{ id: 12, name: 'CBNV', position: 'Giám đốc Ban', email: 'leader@example.test' }];

describe('Birthday email log actions', () => {
  beforeEach(() => {
    setLanguage('vi');
    permissionState.isSystemAdmin = true;
    if (!HTMLDialogElement.prototype.showModal) {
      Object.defineProperties(HTMLDialogElement.prototype, {
        showModal: { value(this: HTMLDialogElement) { this.setAttribute('open', ''); } },
        close: { value(this: HTMLDialogElement) { this.removeAttribute('open'); } },
      });
    }
  });
  afterEach(() => vi.restoreAllMocks());

  it('hides manual sending when the log denies access', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new ApiError(403, {}));
    render(<BirthdayEmailLogs />);
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Thêm thủ công' })).not.toBeInTheDocument();
  });

  it('applies the AI draft on request and sends only after confirmation', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (path) => {
      if (path.includes('/templates/')) return { templates } as never;
      if (path.includes('/recipients/')) return { recipients } as never;
      return { total: 0, logs: [] } as never;
    });
    const post = vi.spyOn(apiClient, 'post').mockImplementation(async (path) => {
      if (path.endsWith('/draft/')) {
        return { draft: { layout: '02', subject: 'Tiêu đề từ AI', message: 'Lời chúc từ AI' } } as never;
      }
      if (path.endsWith('/templates/')) {
        return { template: {
          id: 'saved:1', name: 'Mẫu lãnh đạo', layout: '02', subject: 'Tiêu đề từ AI', message: 'Lời chúc từ AI',
        } } as never;
      }
      if (path.endsWith('/preview/')) {
        return {
          subject: 'Tiêu đề từ AI', html: '<p>Lời chúc từ AI</p>', recipient: 'leader@example.test',
          birthday_date: '2026-05-20', preview_token: 'confirmed-preview',
        } as never;
      }
      return { log: { trang_thai: 'SUCCESS', delivery_uncertain: false } } as never;
    });
    render(<BirthdayEmailLogs />);
    fireEvent.click(await screen.findByRole('button', { name: 'Thêm thủ công' }));
    await screen.findByRole('option', { name: /CBNV/ });
    fireEvent.change(screen.getByLabelText('Người nhận email'), { target: { value: '12' } });
    expect(screen.queryByRole('button', { name: 'Xác nhận gửi email' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Trợ lý AI soạn mẫu' }));
    fireEvent.change(screen.getByLabelText('Yêu cầu soạn mẫu'), { target: { value: 'Dùng giọng văn trang trọng' } });
    fireEvent.click(screen.getByRole('button', { name: 'Tạo bản nháp' }));
    expect(await screen.findByText(/Tiêu đề từ AI/)).toBeInTheDocument();
    expect(screen.getByLabelText('Tiêu đề email')).toHaveValue('Lời chúc');
    expect(post).toHaveBeenCalledWith('/api/birthdays/templates/draft/', { instruction: 'Dùng giọng văn trang trọng' });
    fireEvent.click(screen.getByRole('button', { name: 'Dùng cho email này' }));
    expect(screen.getByLabelText('Tiêu đề email')).toHaveValue('Tiêu đề từ AI');
    fireEvent.change(screen.getByLabelText('Tên mẫu lưu vào thư viện'), { target: { value: 'Mẫu lãnh đạo' } });
    fireEvent.click(screen.getByRole('button', { name: 'Lưu vào thư viện' }));
    await screen.findByText('Đã lưu mẫu vào thư viện.');
    expect(screen.getByLabelText('Mẫu trong thư viện')).toHaveValue('saved:1');

    fireEvent.click(screen.getByRole('button', { name: 'Xem trước email' }));
    const send = await screen.findByRole('button', { name: 'Xác nhận gửi email' });
    expect(post).toHaveBeenCalledTimes(3);
    fireEvent.click(send);
    await waitFor(() => expect(post).toHaveBeenCalledWith('/api/birthdays/manual/send/', expect.objectContaining({
      employee_id: 12, template_id: 'saved:1', preview_token: 'confirmed-preview',
    })));
    expect(await screen.findByText('Máy chủ email đã chấp nhận thư để gửi.')).toBeInTheDocument();
  });

  it('shows resend on every delivery status, including unprocessed and unknown rows', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 5, logs: [
      { id: 1, employee_id: 1, employee_name: 'CBNV thành công', recipient_email: 'ok@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'SUCCESS', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'ok@example.test' },
      { id: 2, employee_id: 2, employee_name: 'CBNV thất bại', recipient_email: 'failed@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'FAILED', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'failed@example.test' },
      { id: 3, employee_id: 3, employee_name: 'CBNV chờ gửi', recipient_email: 'retry@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'RETRY', retry_count: 1, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'retry@example.test' },
      { id: null, employee_id: 4, employee_name: 'CBNV chưa xử lý', recipient_email: 'unprocessed@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'NOT_PROCESSED', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'unprocessed@example.test' },
      { id: 5, employee_id: 5, employee_name: 'CBNV chưa rõ', recipient_email: 'unknown@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'UNKNOWN', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: true, can_retry: false, current_recipient: 'unknown@example.test' },
    ] });
    render(<BirthdayEmailLogs />);

    const buttons = await screen.findAllByRole('button', { name: 'Gửi lại' });
    expect(buttons).toHaveLength(5);
    expect(screen.getByRole('columnheader', { name: 'Thao tác' })).toBeInTheDocument();
    expect(within(screen.getByRole('row', { name: /CBNV chưa xử lý/ })).getByRole('button', { name: 'Gửi lại' })).toBeEnabled();
    expect(within(screen.getByRole('row', { name: /CBNV chưa rõ/ })).getByRole('button', { name: 'Gửi lại' })).toBeEnabled();
  });

  it('confirms an admin resend, refreshes the log, and shows success feedback', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [
      { id: 7, employee_id: 42, employee_name: 'CBNV', recipient_email: 'old@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'SUCCESS', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'new@example.test' },
    ] });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const get = vi.spyOn(apiClient, 'get');
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ log: { trang_thai: 'SUCCESS', delivery_uncertain: false } });
    render(<BirthdayEmailLogs />);
    fireEvent.click(await screen.findByRole('button', { name: 'Gửi lại' }));

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('new@example.test'));
    await waitFor(() => expect(post).toHaveBeenCalledWith('/api/birthdays/logs/resend/', {
      employee_id: 42, sent_date: '2026-11-12',
    }));
    expect(await screen.findByText('Email gửi lại đã được máy chủ thư chấp nhận.')).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  });

  it('shows failure feedback and refreshes when SMTP rejects a resend', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [
      { id: 8, employee_id: 43, employee_name: 'CBNV', recipient_email: 'staff@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'FAILED', retry_count: 1, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'staff@example.test' },
    ] });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.spyOn(apiClient, 'post').mockResolvedValue({ log: { trang_thai: 'FAILED', delivery_uncertain: false } });
    render(<BirthdayEmailLogs />);
    fireEvent.click(await screen.findByRole('button', { name: 'Gửi lại' }));

    expect(await screen.findByText('Gửi email thất bại. Xem chi tiết trong nhật ký.')).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  });

  it('disables duplicate clicks while a resend request is running', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [
      { id: 7, employee_id: 42, employee_name: 'CBNV', recipient_email: 'staff@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'FAILED', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'staff@example.test' },
    ] });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    let finishRequest: (value: { log: { trang_thai: 'SUCCESS'; delivery_uncertain: false } }) => void = () => undefined;
    const post = vi.spyOn(apiClient, 'post').mockImplementation(() => new Promise((resolve) => { finishRequest = resolve; }) as never);
    render(<BirthdayEmailLogs />);
    const resend = await screen.findByRole('button', { name: 'Gửi lại' });
    fireEvent.click(resend);
    await waitFor(() => expect(resend).toBeDisabled());
    fireEvent.click(resend);
    expect(post).toHaveBeenCalledTimes(1);
    finishRequest({ log: { trang_thai: 'SUCCESS', delivery_uncertain: false } });
    await screen.findByText('Email gửi lại đã được máy chủ thư chấp nhận.');
  });

  it('hides resend actions for non-admin users', async () => {
    permissionState.isSystemAdmin = false;
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [
      { id: 7, employee_id: 42, employee_name: 'CBNV', recipient_email: 'staff@example.test', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'SUCCESS', retry_count: 0, delivery_source: 'AUTO', delivery_uncertain: false, can_retry: false, current_recipient: 'staff@example.test' },
    ] });
    render(<BirthdayEmailLogs />);

    await screen.findByText('SMTP đã chấp nhận');
    expect(screen.queryByRole('columnheader', { name: 'Thao tác' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi lại' })).not.toBeInTheDocument();
  });
});
