import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { setLanguage } from '@i18n/translate';
import { ApiError, apiClient } from '@lib/apiClient';
import BirthdayEmailLogs from './BirthdayEmailLogs';

const permissionState = vi.hoisted(() => ({ isSystemAdmin: true }));
vi.mock('@lib/permissions', () => ({
  usePermissions: () => ({
    loaded: true,
    isSuperuser: permissionState.isSystemAdmin,
    isSystemAdmin: permissionState.isSystemAdmin,
    can: () => permissionState.isSystemAdmin,
  }),
}));

const templates = [
  { id: 'layout:01', layout: '01', name: null, subject: 'Lời chúc', message: 'Chúc mừng sinh nhật' },
  { id: 'layout:02', layout: '02', name: null, subject: 'Thư chúc', message: 'Chúc mừng sinh nhật' },
];
const recipients = [{ id: 12, name: 'Nguyễn Văn A', position: 'Giám đốc Ban', email: 'leader@example.test' }];

const acceptedLog = {
  id: 21,
  employee_name: 'Nguyễn Văn A',
  recipient_email: 'leader@example.test',
  position: 'Giám đốc Ban',
  department: 'Ban lãnh đạo',
  sent_date: '12/11/2026',
  sent_at: '12/11/2026 14:32:00',
  trang_thai: 'SUCCESS' as const,
  retry_count: 0,
  error_message: '',
  smtp_response_code: '250',
  delivery_source: 'MANUAL' as const,
  delivery_uncertain: false,
  template_version: null,
  last_operator: 'admin',
  can_retry: false,
  current_recipient: null,
};

const previewResponse = {
  subject: 'Lời chúc',
  html: '<p>Chúc mừng sinh nhật</p>',
  recipient: 'leader@example.test',
  birthday_date: '2026-05-20',
  card_url: 'https://staging.example.test/birthday-cards/05.html#token=signed-token',
  preview_token: 'confirmed-preview',
};

function mockManualEmailApi(sendLog: Record<string, unknown>) {
  let logLoads = 0;
  const get = vi.spyOn(apiClient, 'get').mockImplementation(async (path) => {
    if (path.includes('/templates/')) return { templates } as never;
    if (path.includes('/recipients/')) return { recipients } as never;
    logLoads += 1;
    return {
      total: logLoads > 1 ? 1 : 0,
      total_pages: 1,
      logs: logLoads > 1 ? [sendLog] : [],
    } as never;
  });
  const post = vi.spyOn(apiClient, 'post').mockImplementation(async (path) => {
    if (path.endsWith('/preview/')) return previewResponse as never;
    return { log: sendLog } as never;
  });
  return { get, post };
}

async function previewManualEmail() {
  fireEvent.click(await screen.findByRole('button', { name: 'Thêm thủ công' }));
  await screen.findByRole('option', { name: /Nguyễn Văn A/ });
  fireEvent.change(screen.getByLabelText('Người nhận email'), { target: { value: '12' } });
  fireEvent.click(screen.getByRole('button', { name: 'Xem trước nội dung email' }));
  return screen.findByRole('button', { name: 'Xác nhận gửi email' });
}

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

  it('labels the email-safe preview and opens the matching web card separately', async () => {
    mockManualEmailApi(acceptedLog);
    render(<BirthdayEmailLogs />);
    const send = await previewManualEmail();

    const iframe = screen.getByTitle('Xem trước nội dung email');
    expect(iframe).toHaveAttribute('srcdoc', previewResponse.html);
    expect(screen.getByText(
      'Một số hiệu ứng động không được Gmail/Outlook hỗ trợ. Email thực tế sẽ dùng phiên bản tương thích, không có hiệu ứng web 3D.',
    )).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '🎁 Mở thiệp sinh nhật 3D' })).toHaveAttribute(
      'href', previewResponse.card_url,
    );
    expect(screen.getByText('Đây là trải nghiệm đầy đủ mà người nhận mở từ nút trong email.')).toBeInTheDocument();
    expect(send).toBeInTheDocument();
  });

  it('applies the AI draft on request and sends only after confirmation', async () => {
    let logLoads = 0;
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (path) => {
      if (path.includes('/templates/')) return { templates } as never;
      if (path.includes('/recipients/')) return { recipients } as never;
      logLoads += 1;
      return { total: logLoads > 1 ? 1 : 0, logs: logLoads > 1 ? [acceptedLog] : [] } as never;
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
        return { ...previewResponse, subject: 'Tiêu đề từ AI', html: '<p>Lời chúc từ AI</p>' } as never;
      }
      return { log: acceptedLog } as never;
    });
    render(<BirthdayEmailLogs />);
    fireEvent.click(await screen.findByRole('button', { name: 'Thêm thủ công' }));
    await screen.findByRole('option', { name: /Nguyễn Văn A/ });
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

    fireEvent.click(screen.getByRole('button', { name: 'Xem trước nội dung email' }));
    const send = await screen.findByRole('button', { name: 'Xác nhận gửi email' });
    expect(post).toHaveBeenCalledTimes(3);
    fireEvent.click(send);
    await waitFor(() => expect(post).toHaveBeenCalledWith('/api/birthdays/manual/send/', expect.objectContaining({
      employee_id: 12, template_id: 'saved:1', preview_token: 'confirmed-preview',
    })));
    expect(await screen.findByText('Gửi email thành công')).toBeInTheDocument();
    expect(screen.getByText(
      'Email sinh nhật cho Nguyễn Văn A (leader@example.test) đã được máy chủ thư chấp nhận để tiếp tục gửi lúc 12/11/2026 14:32:00.',
    )).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(get.mock.calls.filter(([url]) => String(url).includes('/api/birthdays/logs/')).length).toBeGreaterThanOrEqual(2);
    const deliveredLog = await screen.findByRole('row', { name: /Nguyễn Văn A/ });
    expect(within(deliveredLog).getByText('SMTP đã chấp nhận')).toBeInTheDocument();
    expect(within(deliveredLog).getByText('Thủ công')).toBeInTheDocument();
    expect(within(deliveredLog).getByText('leader@example.test')).toBeInTheDocument();
  });

  it('shows a failure message without a success notice when manual delivery fails', async () => {
    const failedLog = { ...acceptedLog, trang_thai: 'FAILED', delivery_uncertain: false };
    mockManualEmailApi(failedLog);
    render(<BirthdayEmailLogs />);
    fireEvent.click(await previewManualEmail());

    expect(await screen.findByText('Gửi email thất bại')).toBeInTheDocument();
    expect(screen.getByText('Gửi email thất bại. Kiểm tra chi tiết trong Nhật ký email.')).toBeInTheDocument();
    expect(screen.queryByText('Gửi email thành công')).not.toBeInTheDocument();
    expect(screen.queryByText(/đã được máy chủ thư chấp nhận/)).not.toBeInTheDocument();
  });

  it('shows reconciliation guidance instead of success when delivery is uncertain', async () => {
    const uncertainLog = { ...acceptedLog, delivery_uncertain: true };
    mockManualEmailApi(uncertainLog);
    render(<BirthdayEmailLogs />);
    fireEvent.click(await previewManualEmail());

    expect(await screen.findByText('Cần đối soát kết quả gửi')).toBeInTheDocument();
    expect(within(screen.getByRole('alert')).getByText(
      'Kết quả gửi trước chưa xác định; gửi lại có thể làm người nhận nhận email trùng.',
    )).toBeInTheDocument();
    expect(screen.queryByText(/Gửi email thành công/)).not.toBeInTheDocument();
    expect(screen.queryByText(/đã được máy chủ thư chấp nhận/)).not.toBeInTheDocument();
  });

  it('disables sending and ignores a second submit while the request is pending', async () => {
    let resolveSend: ((value: { log: typeof acceptedLog }) => void) | undefined;
    const pendingSend = new Promise<{ log: typeof acceptedLog }>((resolve) => { resolveSend = resolve; });
    const get = vi.spyOn(apiClient, 'get').mockImplementation(async (path) => {
      if (path.includes('/templates/')) return { templates } as never;
      if (path.includes('/recipients/')) return { recipients } as never;
      return { total: 0, logs: [] } as never;
    });
    const post = vi.spyOn(apiClient, 'post').mockImplementation(async (path) => {
      if (path.endsWith('/preview/')) return previewResponse as never;
      return pendingSend as never;
    });
    render(<BirthdayEmailLogs />);
    const send = await previewManualEmail();
    act(() => {
      send.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      send.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(send).toBeDisabled();
    expect(await screen.findByText('Đang xử lý…')).toBeInTheDocument();
    expect(post.mock.calls.filter(([path]) => String(path).endsWith('/manual/send/'))).toHaveLength(1);

    resolveSend?.({ log: acceptedLog });
    expect(await screen.findByText(/Gửi email thành công/)).toBeInTheDocument();
    await waitFor(() => {
      expect(get.mock.calls.filter(([url]) => String(url).includes('/api/birthdays/logs/')).length)
        .toBeGreaterThanOrEqual(2);
    });
  });

  it('shows a full resend button for every status and resends an unprocessed birthday by employee and date', async () => {
    const states = ['SUCCESS', 'FAILED', 'RETRY', 'UNKNOWN', 'NOT_PROCESSED'] as const;
    const logs = states.map((status, index) => ({
      id: status === 'NOT_PROCESSED' ? null : index + 1,
      employee_id: index + 1,
      employee_name: `CBNV ${status}`,
      recipient_email: `employee${index + 1}@example.test`,
      current_recipient: `employee${index + 1}@example.test`,
      position: 'Chuyên viên',
      department: 'Đơn vị A',
      sent_date: '12/11/2026',
      sent_date_iso: '2026-11-12',
      sent_at: status === 'NOT_PROCESSED' ? null : '12/11/2026 07:07:00',
      trang_thai: status,
      retry_count: 0,
      error_message: '',
      smtp_response_code: '',
      delivery_source: 'AUTO',
      delivery_context: 'SCHEDULED',
      delivery_uncertain: status === 'UNKNOWN',
      template_version: null,
      last_operator: null,
      can_retry: false,
      retry_block_reason: status === 'UNKNOWN' ? 'needsReview' : 'notRetryable',
    }));
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ total: logs.length, logs } as never);
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
      log: { ...acceptedLog, employee_name: 'CBNV NOT_PROCESSED' },
    });
    render(<BirthdayEmailLogs />);
    expect(await screen.findByRole('columnheader', { name: 'Thao tác' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Gửi lại' })).toHaveLength(states.length);
    for (const status of states) {
      const row = screen.getByRole('row', { name: new RegExp(`CBNV ${status}`) });
      const resend = within(row).getByRole('button', { name: 'Gửi lại' });
      expect(resend).toBeEnabled();
      expect(resend).toHaveClass('bg-primary');
    }
    const unknownRow = screen.getByRole('row', { name: /CBNV UNKNOWN/ });
    expect(within(unknownRow).getByText('Chưa rõ kết quả SMTP')).toBeInTheDocument();

    const unprocessedRow = screen.getByRole('row', { name: /CBNV NOT_PROCESSED/ });
    fireEvent.click(within(unprocessedRow).getByRole('button', { name: 'Gửi lại' }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('employee5@example.test'));
    expect(post).toHaveBeenCalledWith('/api/birthdays/logs/resend/', {
      employee_id: 5,
      sent_date: '2026-11-12',
    });
    expect(await screen.findByText('Đã gửi lại email')).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  });

  it('sends one resend request while the admin action is pending', async () => {
    const resendableLog = {
      ...acceptedLog,
      employee_id: 12,
      sent_date_iso: '2026-11-12',
    };
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [resendableLog] } as never);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    let resolveResend: ((value: { log: typeof acceptedLog }) => void) | undefined;
    const pendingResend = new Promise<{ log: typeof acceptedLog }>((resolve) => {
      resolveResend = resolve;
    });
    const post = vi.spyOn(apiClient, 'post').mockReturnValue(pendingResend as never);
    render(<BirthdayEmailLogs />);

    const resend = await screen.findByRole('button', { name: 'Gửi lại' });
    fireEvent.click(resend);
    expect(await screen.findByRole('button', { name: 'Gửi lại' })).toBeDisabled();
    fireEvent.click(resend);

    expect(post).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolveResend?.({ log: acceptedLog });
      await pendingResend;
    });
  });

  it('shows resend failure and refreshes the log list after a failed request', async () => {
    const resendableLog = {
      ...acceptedLog,
      id: 7,
      employee_id: 7,
      sent_date_iso: '2026-11-12',
    };
    let logLoads = 0;
    vi.spyOn(apiClient, 'get').mockImplementation(async (path) => {
      if (path.includes('/templates/')) return { templates } as never;
      if (path.includes('/recipients/')) return { recipients } as never;
      logLoads += 1;
      return { total: 1, logs: [resendableLog] } as never;
    });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const post = vi.spyOn(apiClient, 'post').mockRejectedValue(
      new ApiError(503, { error: 'smtpUnavailable' }),
    );
    render(<BirthdayEmailLogs />);

    fireEvent.click(await screen.findByRole('button', { name: 'Gửi lại' }));

    expect(await screen.findByText('Gửi email thất bại')).toBeInTheDocument();
    expect(screen.getByText('Chưa có cấu hình SMTP dùng cho email sinh nhật.')).toBeInTheDocument();
    expect(screen.queryByText('Đã gửi lại email')).not.toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(logLoads).toBeGreaterThanOrEqual(2));
  });

  it('shows unprocessed birthdays and distinguishes scheduled, recovery, and manual sources', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 5, logs: [
      {
        id: null, employee_id: 1, employee_name: 'CBNV chưa xử lý', recipient_email: '', position: 'Chuyên viên',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_date_iso: '2026-11-12', sent_at: null, trang_thai: 'NOT_PROCESSED', retry_count: 0,
        error_message: '', smtp_response_code: '', delivery_source: 'AUTO', delivery_context: null,
        delivery_uncertain: false, template_version: null, last_operator: null, can_retry: false,
        current_recipient: null, retry_block_reason: null,
      },
      {
        id: 2, employee_id: 2, employee_name: 'CBNV đã gửi', recipient_email: 'sent@example.test', position: 'Chuyên viên',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_at: '12/11/2026 07:07:00', trang_thai: 'SUCCESS',
        retry_count: 0, error_message: '', smtp_response_code: '250 OK', delivery_source: 'AUTO',
        delivery_context: 'SCHEDULED', delivery_uncertain: false, template_version: null, last_operator: null,
        can_retry: false, current_recipient: null, retry_block_reason: 'alreadySent',
      },
      {
        id: 3, employee_id: 3, employee_name: 'CBNV gửi bù', recipient_email: 'recovery@example.test', position: 'Chuyên viên',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_at: '12/11/2026 12:30:00', trang_thai: 'SUCCESS',
        retry_count: 0, error_message: '', smtp_response_code: '250 OK', delivery_source: 'AUTO',
        delivery_context: 'RECOVERY', delivery_uncertain: false, template_version: null, last_operator: null,
        can_retry: false, current_recipient: null, retry_block_reason: 'alreadySent',
      },
      {
        id: 4, employee_id: 4, employee_name: 'CBNV gửi thủ công', recipient_email: 'manual@example.test', position: 'Giám đốc',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_at: '12/11/2026 12:45:00', trang_thai: 'SUCCESS',
        retry_count: 0, error_message: '', smtp_response_code: '250 OK', delivery_source: 'MANUAL',
        delivery_context: null, delivery_uncertain: false, template_version: null, last_operator: 'admin',
        can_retry: false, current_recipient: null, retry_block_reason: 'alreadySent',
      },
      {
        id: 5, employee_id: 5, employee_name: 'CBNV gửi lại thư thủ công', recipient_email: 'resent@example.test', position: 'Giám đốc',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_at: '12/11/2026 12:46:00', trang_thai: 'SUCCESS',
        retry_count: 1, error_message: '', smtp_response_code: '250 OK', delivery_source: 'MANUAL_RESEND',
        delivery_context: 'MANUAL_RESEND', delivery_uncertain: false, template_version: null, last_operator: 'admin',
        can_retry: false, current_recipient: null, retry_block_reason: 'alreadySent',
      },
    ] });
    render(<BirthdayEmailLogs />);

    expect(await screen.findByText('Chưa được xử lý')).toBeInTheDocument();
    expect(screen.getByText('Chưa có bản ghi gửi cho ngày sinh này; kiểm tra lượt scheduler hoặc chạy gửi bù.')).toBeInTheDocument();
    const notProcessedRow = screen.getByRole('row', { name: /CBNV chưa xử lý/ });
    const scheduledRow = screen.getByRole('row', { name: /CBNV đã gửi/ });
    const recoveryRow = screen.getByRole('row', { name: /CBNV gửi bù/ });
    const manualRow = screen.getByRole('row', { name: /CBNV gửi thủ công/ });
    const manualRetryRow = screen.getByRole('row', { name: /CBNV gửi lại thư thủ công/ });
    expect(within(notProcessedRow).getByText('Chưa được xử lý')).toBeInTheDocument();
    expect(within(notProcessedRow).queryByText('Tự động theo lịch')).not.toBeInTheDocument();
    expect(within(scheduledRow).getByText('Tự động theo lịch')).toBeInTheDocument();
    expect(within(recoveryRow).getByText('Chạy bù')).toBeInTheDocument();
    expect(within(manualRow).getByText('Thủ công')).toBeInTheDocument();
    expect(within(manualRetryRow).getByText('Quản trị viên gửi lại')).toBeInTheDocument();
    expect(within(notProcessedRow).getByRole('button', { name: 'Gửi lại' })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Gửi lại' })).toHaveLength(5);
  });

  it('keeps the resend button visible when the employee email needs correction', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [{
      id: 7, employee_id: 7, employee_name: 'CBNV', recipient_email: 'wrong-address', position: '', department: '',
      sent_date: '12/11/2026', sent_at: '12/11/2026 07:07:00', trang_thai: 'FAILED', retry_count: 0,
      error_message: 'Invalid email', smtp_response_code: '', delivery_source: 'AUTO', delivery_context: 'SCHEDULED',
      delivery_uncertain: false, template_version: null, last_operator: null, can_retry: false,
      current_recipient: null, retry_block_reason: 'invalidEmail',
    }] });
    render(<BirthdayEmailLogs />);

    expect(await screen.findByText('Invalid email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gửi lại' })).toBeEnabled();
  });

  it('does not show resend controls for non-admin users', async () => {
    permissionState.isSystemAdmin = false;
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [acceptedLog] } as never);
    render(<BirthdayEmailLogs />);
    expect(await screen.findByText('SMTP đã chấp nhận')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Thao tác' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi lại' })).not.toBeInTheDocument();
  });
});
