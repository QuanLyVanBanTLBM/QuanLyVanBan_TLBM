import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { setLanguage } from '@i18n/translate';
import { ApiError, apiClient } from '@lib/apiClient';
import BirthdayEmailLogs from './BirthdayEmailLogs';

const templates = [
  { id: 'layout:01', layout: '01', name: null, subject: 'Lời chúc', message: 'Chúc mừng sinh nhật' },
  { id: 'layout:02', layout: '02', name: null, subject: 'Thư chúc', message: 'Chúc mừng sinh nhật' },
];
const recipients = [{ id: 12, name: 'CBNV', position: 'Giám đốc Ban', email: 'leader@example.test' }];

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

  it('offers a retry only for the log that can be resent and confirms its current address', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 2, logs: [
      {
        id: 1, employee_id: 1, employee_name: 'CBNV A', trang_thai: 'FAILED', can_retry: false,
        current_recipient: null, retry_block_reason: 'needsReview', delivery_uncertain: true,
      },
      {
        id: 2, employee_id: 2, employee_name: 'CBNV B', trang_thai: 'FAILED', can_retry: true,
        current_recipient: 'corrected@example.test', retry_block_reason: null, delivery_uncertain: false,
      },
    ] });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ log: { trang_thai: 'SUCCESS' } });
    render(<BirthdayEmailLogs />);
    expect(await screen.findByText('Kết quả gửi chưa xác định. Cần đối soát.')).toBeInTheDocument();
    const retries = screen.getAllByRole('button', { name: 'Gửi lại' });
    expect(retries).toHaveLength(1);
    expect(retries[0]).toBeEnabled();
    fireEvent.click(retries[0]);
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('corrected@example.test'));
    expect(post).toHaveBeenCalledWith('/api/birthdays/logs/2/retry/', { recipient: 'corrected@example.test' });
    expect(await screen.findByText('Máy chủ email đã chấp nhận thư để gửi.')).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledTimes(2);
  });

  it('shows unprocessed birthdays and distinguishes scheduled, recovery, and manual sources', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 5, logs: [
      {
        id: null, employee_id: 1, employee_name: 'CBNV chưa xử lý', recipient_email: '', position: 'Chuyên viên',
        department: 'Đơn vị A', sent_date: '12/11/2026', sent_at: null, trang_thai: 'NOT_PROCESSED', retry_count: 0,
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
        retry_count: 1, error_message: '', smtp_response_code: '250 OK', delivery_source: 'MANUAL',
        delivery_context: 'RETRY', delivery_uncertain: false, template_version: null, last_operator: 'admin',
        can_retry: false, current_recipient: null, retry_block_reason: 'alreadySent',
      },
    ] });
    render(<BirthdayEmailLogs />);

    expect(await screen.findByText('Chưa được xử lý')).toBeInTheDocument();
    expect(screen.getByText('Chưa có bản ghi gửi cho ngày sinh này; kiểm tra lượt scheduler hoặc chạy gửi bù.')).toBeInTheDocument();
    expect(screen.getAllByText('Tự động theo lịch')).toHaveLength(2);
    expect(screen.getByText('Chạy bù')).toBeInTheDocument();
    expect(screen.getByText('Thủ công')).toBeInTheDocument();
    expect(screen.getByText('Quản trị viên gửi lại')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi lại' })).not.toBeInTheDocument();
  });

  it('explains when a failed record cannot be resent because its email is invalid', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ total: 1, logs: [{
      id: 7, employee_id: 7, employee_name: 'CBNV', recipient_email: 'wrong-address', position: '', department: '',
      sent_date: '12/11/2026', sent_at: '12/11/2026 07:07:00', trang_thai: 'FAILED', retry_count: 0,
      error_message: 'Invalid email', smtp_response_code: '', delivery_source: 'AUTO', delivery_context: 'SCHEDULED',
      delivery_uncertain: false, template_version: null, last_operator: null, can_retry: false,
      current_recipient: null, retry_block_reason: 'invalidEmail',
    }] });
    render(<BirthdayEmailLogs />);

    expect(await screen.findByText('Cần cập nhật địa chỉ email hợp lệ trong hồ sơ CBNV.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gửi lại' })).not.toBeInTheDocument();
  });
});
