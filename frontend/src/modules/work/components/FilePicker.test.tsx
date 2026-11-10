import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FilePicker, { previewLocalFile } from './FilePicker';

describe('previewLocalFile', () => {
  let revokeObjectURL: ReturnType<typeof vi.fn>;
  let createObjectURL: ReturnType<typeof vi.fn>;
  let windowOpen: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers();
    createObjectURL = vi.fn(() => 'blob:http://localhost/fake-id');
    revokeObjectURL = vi.fn();
    globalThis.URL.createObjectURL = createObjectURL as unknown as typeof URL.createObjectURL;
    globalThis.URL.revokeObjectURL = revokeObjectURL as unknown as typeof URL.revokeObjectURL;
    windowOpen = vi.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('PDF mở trong tab mới, revoke URL sau 60s', () => {
    const file = new File(['%PDF-1.4'], 'report.pdf', { type: 'application/pdf' });
    previewLocalFile(file);

    expect(createObjectURL).toHaveBeenCalledWith(file);
    expect(windowOpen).toHaveBeenCalledWith('blob:http://localhost/fake-id', '_blank');
    expect(revokeObjectURL).not.toHaveBeenCalled();

    vi.advanceTimersByTime(60_000);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/fake-id');
  });

  it('ảnh JPG mở trong tab mới', () => {
    const file = new File(['image-data'], 'photo.jpg', { type: 'image/jpeg' });
    previewLocalFile(file);

    expect(windowOpen).toHaveBeenCalledWith('blob:http://localhost/fake-id', '_blank');
  });

  it('DOCX tải về qua thẻ <a> download, revoke URL sau 5s', () => {
    const clickSpy = vi.fn();
    vi.spyOn(document, 'createElement').mockReturnValue({
      set href(_v: string) { /* noop */ },
      set download(_v: string) { /* noop */ },
      click: clickSpy,
    } as unknown as HTMLAnchorElement);

    const file = new File(['doc-data'], 'contract.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    previewLocalFile(file);

    expect(windowOpen).not.toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    vi.advanceTimersByTime(5_000);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/fake-id');
  });
});

describe('FilePicker — bấm tên file mở xem trước', () => {
  it('bấm tên file gọi previewLocalFile (tên hiện dưới dạng button)', () => {
    const file = new File(['data'], 'test.pdf', { type: 'application/pdf' });
    const onChange = vi.fn();

    vi.spyOn(window, 'open').mockImplementation(() => null);
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:fake') as unknown as typeof URL.createObjectURL;
    globalThis.URL.revokeObjectURL = vi.fn() as unknown as typeof URL.revokeObjectURL;

    render(<FilePicker files={[file]} onChange={onChange} />);

    const fileButton = screen.getByRole('button', { name: 'test.pdf' });
    expect(fileButton).toBeDefined();
    fireEvent.click(fileButton);
    expect(window.open).toHaveBeenCalled();
  });

  it('bấm nút X xóa file, không mở file', () => {
    const file = new File(['data'], 'test.pdf', { type: 'application/pdf' });
    const onChange = vi.fn();

    vi.spyOn(window, 'open').mockImplementation(() => null);
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:fake') as unknown as typeof URL.createObjectURL;

    render(<FilePicker files={[file]} onChange={onChange} />);

    const removeButton = screen.getByLabelText(/test\.pdf/);
    fireEvent.click(removeButton);

    expect(onChange).toHaveBeenCalledWith([]);
    expect(window.open).not.toHaveBeenCalled();
  });
});
