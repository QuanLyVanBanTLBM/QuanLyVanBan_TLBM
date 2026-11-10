import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { escapeHtml, generateDocxPreviewHtml, previewAttachmentInNewTab } from './filePreview';

vi.mock('@lib/apiClient', () => ({
  apiClientBlob: vi.fn(),
  downloadBlob: vi.fn(),
}));

vi.mock('@lib/fileUtils', () => ({
  getAbsoluteFileUrl: vi.fn((url: string) => `http://localhost:8000${url}`),
  formatFileSize: vi.fn((bytes?: number) => (bytes ? `${bytes} B` : '0 B')),
}));

describe('filePreview utility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('escapeHtml escapes special characters properly', () => {
    const raw = '<script>alert("XSS" & \'test\')</script>';
    const escaped = escapeHtml(raw);
    expect(escaped).not.toContain('<script>');
    expect(escaped).toContain('&lt;script&gt;');
    expect(escaped).toContain('&quot;XSS&quot;');
    expect(escaped).toContain('&#039;test&#039;');
    expect(escaped).toContain('&amp;');
  });

  it('generateDocxPreviewHtml generates formatted HTML with title and paragraphs', () => {
    const html = generateDocxPreviewHtml('test_doc.docx', ['Đoạn văn thứ nhất', 'Đoạn văn thứ hai']);
    expect(html).toContain('test_doc.docx');
    expect(html).toContain('Đoạn văn thứ nhất');
    expect(html).toContain('Đoạn văn thứ hai');
    expect(html).toContain('In văn bản');
  });

  it('previewAttachmentInNewTab handles client-side local PDF file', async () => {
    const mockOpen = vi.spyOn(window, 'open').mockReturnValue({
      location: { href: '' },
      closed: false,
      close: vi.fn(),
      document: { title: '' },
    } as unknown as Window);

    const fakeFile = new File(['%PDF-1.4 test'], 'vanban.pdf', { type: 'application/pdf' });
    await previewAttachmentInNewTab({ name: 'vanban.pdf', file: fakeFile });

    expect(mockOpen).toHaveBeenCalled();
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(fakeFile);
  });

  it('previewAttachmentInNewTab handles client-side image file', async () => {
    const mockOpen = vi.spyOn(window, 'open').mockReturnValue({
      location: { href: '' },
      closed: false,
      close: vi.fn(),
      document: { title: '' },
    } as unknown as Window);

    const fakeFile = new File(['image-bytes'], 'anh_minh_chung.png', { type: 'image/png' });
    await previewAttachmentInNewTab({ name: 'anh_minh_chung.png', file: fakeFile });

    expect(mockOpen).toHaveBeenCalled();
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(fakeFile);
  });

  it('previewAttachmentInNewTab handles server-side PDF with apiClientBlob', async () => {
    const { apiClientBlob } = await import('@lib/apiClient');
    vi.mocked(apiClientBlob).mockResolvedValueOnce(new Blob(['pdf content'], { type: 'application/pdf' }));

    const mockOpen = vi.spyOn(window, 'open').mockReturnValue({
      location: { href: '' },
      closed: false,
      close: vi.fn(),
      document: { title: '' },
    } as unknown as Window);

    await previewAttachmentInNewTab({ name: 'vanban_den.pdf', url: '/media/documents/vb.pdf' });

    expect(apiClientBlob).toHaveBeenCalledWith('/media/documents/vb.pdf');
    expect(mockOpen).toHaveBeenCalled();
  });
});
