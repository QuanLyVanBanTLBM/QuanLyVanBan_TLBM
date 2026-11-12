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
      { id: 1, employee_name: 'CBNV A', trang_thai: 'FAILED', can_retry: false, delivery_uncertain: true },
      { id: 2, employee_name: 'CBNV B', trang_thai: 'FAILED', can_retry: true, current_recipient: 'corrected@example.test' },
    ] });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ log: { trang_thai: 'SUCCESS' } });
    render(<BirthdayEmailLogs />);
    expect(await screen.findByText('Kết quả gửi chưa xác định. Cần đối soát.')).toBeInTheDocument();
    const retries = screen.getAllByRole('button', { name: 'Gửi lại' });
    expect(retries[0]).toBeDisabled();
    expect(retries[1]).toBeEnabled();
    fireEvent.click(retries[1]);
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('corrected@example.test'));
    expect(post).toHaveBeenCalledWith('/api/birthdays/logs/2/retry/', { recipient: 'corrected@example.test' });
    expect(await screen.findByText('Máy chủ email đã chấp nhận thư để gửi.')).toBeInTheDocument();
  });
});
