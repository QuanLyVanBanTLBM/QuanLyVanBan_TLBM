import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLanguage, t } from '@i18n/translate';
import apiClient, { ApiError, downloadBlob } from './apiClient';

describe('API response errors', () => {
  beforeEach(() => {
    localStorage.clear();
    setLanguage('vi');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setLanguage('vi');
  });

  it.each([
    ['text/html', '<!doctype html><html><body>Traceback with private data</body></html>'],
    ['text/plain', '  <html><body>Proxy error</body></html>'],
  ])('does not expose HTML error pages served as %s', async (contentType, body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, {
      status: 500,
      headers: { 'content-type': contentType },
    })));

    await expect(apiClient('/api/dashboard/overview/')).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      message: t('common.apiError', { status: '500' }),
    });
  });

  it('uses the selected language for HTML errors', async () => {
    setLanguage('en');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Bad gateway</html>', {
      status: 502,
      headers: { 'content-type': 'text/html' },
    })));

    await expect(apiClient('/api/records/dossiers/')).rejects.toThrow(
      t('common.apiError', { status: '502' }, 'en')
    );
  });

  it('preserves structured JSON validation errors', async () => {
    const data = { detail: 'Validation failed', ten_ho_so: ['Required'] };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(data), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    })));

    await expect(apiClient('/api/records/dossiers/')).rejects.toMatchObject({
      status: 400,
      data,
    });
  });

  it('preserves plain text errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Service unavailable', {
      status: 503,
      headers: { 'content-type': 'text/plain' },
    })));

    await expect(apiClient('/api/records/dossiers/')).rejects.toEqual(
      new ApiError(503, { error: 'Service unavailable' })
    );
  });

  it('preserves successful text responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Preview</html>', {
      headers: { 'content-type': 'text/html' },
    })));

    await expect(apiClient('/api/preview/')).resolves.toBe('<html>Preview</html>');
  });
});

describe('downloadBlob', () => {
  beforeEach(() => {
    localStorage.clear();
    setLanguage('vi');
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    window.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('ưu tiên defaultFilename thay vì bị ghi đè bởi Content-Disposition bị mã hóa', async () => {
    const mockBlob = new Blob(['pdf-data'], { type: 'application/pdf' });
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    let capturedFilename = '';

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({
        'Content-Disposition': 'attachment; filename="3D=22ITC_-_Django.pdf=22"',
      }),
      blob: vi.fn().mockResolvedValue(mockBlob),
    }));

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = originalCreateElement(tagName);
      if (tagName === 'a') {
        const origSetAttribute = el.setAttribute.bind(el);
        el.setAttribute = (name: string, value: string) => {
          if (name === 'download') {
            capturedFilename = value;
          }
          return origSetAttribute(name, value);
        };
        el.click = vi.fn();
      }
      return el;
    });

    await downloadBlob('/api/documents/1/download/', 'ITC - Đồ án - Tổng quan.pdf');

    expect(capturedFilename).toBe('ITC - Đồ án - Tổng quan.pdf');
    expect(appendSpy).toHaveBeenCalled();
  });

  it('fallback sang Content-Disposition khi không truyền defaultFilename', async () => {
    const mockBlob = new Blob(['pdf-data'], { type: 'application/pdf' });
    let capturedFilename = '';

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({
        'Content-Disposition': 'attachment; filename="tailieu_goc.pdf"',
      }),
      blob: vi.fn().mockResolvedValue(mockBlob),
    }));

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = originalCreateElement(tagName);
      if (tagName === 'a') {
        const origSetAttribute = el.setAttribute.bind(el);
        el.setAttribute = (name: string, value: string) => {
          if (name === 'download') {
            capturedFilename = value;
          }
          return origSetAttribute(name, value);
        };
        el.click = vi.fn();
      }
      return el;
    });

    await downloadBlob('/api/documents/1/download/');

    expect(capturedFilename).toBe('tailieu_goc.pdf');
  });
});

describe('apiClient HTTP methods & FormData body serialization', () => {
  beforeEach(() => {
    localStorage.clear();
    setLanguage('vi');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('apiClient.post với FormData giữ nguyên FormData và không gắn Content-Type application/json', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    const fd = new FormData();
    fd.append('tep', new Blob(['test-png']), 'sig.png');

    await apiClient.post('/api/signing/anh-chu-ky-ca-nhan/', fd);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(fd);
    const headers = init.headers as Headers;
    expect(headers.has('Content-Type')).toBe(false);
  });

  it('apiClient.post với plain object chuyển thành JSON và gắn Content-Type application/json', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1 }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    vi.stubGlobal('fetch', fetchMock);

    await apiClient.post('/api/test/', { name: 'demo' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ name: 'demo' }));
    const headers = init.headers as Headers;
    expect(headers.get('Content-Type')).toBe('application/json');
  });
});
