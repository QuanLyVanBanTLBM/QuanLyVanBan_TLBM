import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { setLanguage } from '@i18n/translate';
import { ApiError, apiClient } from '@lib/apiClient';
import BirthdayEmailLogs from './BirthdayEmailLogs';

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
  fireEvent.click(screen.getByRole('button', { name: 'Xem trước email' }));
  return screen.findByRole('button', { name: 'Xác nhận gửi email' });
}

describe('Birthday email log actions', () => {
  beforeEach(() => {
    setLanguage('vi');
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

    fireEvent.click(screen.getByRole('button', { name: 'Xem trước email' }));
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
      'Chưa thể xác định kết quả gửi email. Cần kiểm tra/đối soát trước khi gửi lại.',
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
    fireEvent.click(send);
    fireEvent.click(send);

    expect(send).toBeDisabled();
    expect(await screen.findByText('Đang xử lý…')).toBeInTheDocument();
    expect(post.mock.calls.filter(([path]) => String(path).endsWith('/manual/send/'))).toHaveLength(1);

    resolveSend?.({ log: acceptedLog });
    expect(await screen.findByText(/Gửi email thành công/)).toBeInTheDocument();
    expect(get.mock.calls.filter(([url]) => String(url).includes('/api/birthdays/logs/')).length).toBeGreaterThanOrEqual(2);
  });

  it('offers a retry only for the log that can be resent and confirms its current address', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 2, logs: [
      { id: 1, employee_name: 'CBNV A', trang_thai: 'FAILED', can_retry: false, delivery_uncertain: true },
      { id: 2, employee_name: 'CBNV B', trang_thai: 'FAILED', can_retry: true, current_recipient: 'corrected@example.test' },
    ] });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
      log: { ...acceptedLog, recipient_email: 'corrected@example.test' },
    });
    render(<BirthdayEmailLogs />);
    expect(await screen.findByText('Chưa thể xác định kết quả gửi email. Cần kiểm tra/đối soát trước khi gửi lại.')).toBeInTheDocument();
    const retries = screen.getAllByRole('button', { name: 'Gửi lại' });
    expect(retries[0]).toBeDisabled();
    expect(retries[1]).toBeEnabled();
    fireEvent.click(retries[1]);
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('corrected@example.test'));
    expect(post).toHaveBeenCalledWith('/api/birthdays/logs/2/retry/', { recipient: 'corrected@example.test' });
    expect(await screen.findByText(/Gửi email thành công/)).toBeInTheDocument();
  });
});
