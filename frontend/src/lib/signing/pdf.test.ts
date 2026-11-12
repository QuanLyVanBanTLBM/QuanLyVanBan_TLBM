import { describe, expect, it, vi, beforeEach } from 'vitest';
import { laLoiHuyVe, layWorkerSrc, moPdf } from './pdf';

const PDF_MINIMAL = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >> endobj
xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000059 00000 n 
0000000116 00000 n 
trailer << /Size 4 /Root 1 0 R >>
startxref
192
%%EOF`;

describe('pdf module', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('nhan dien dung loi huy ve', () => {
    expect(laLoiHuyVe({ name: 'RenderingCancelledException' })).toBe(true);
    expect(laLoiHuyVe({ name: 'OtherException' })).toBe(false);
    expect(laLoiHuyVe(null)).toBe(false);
    expect(laLoiHuyVe(undefined)).toBe(false);
  });

  it('layWorkerSrc tao Blob URL hop le khi fetch thanh cong', async () => {
    const fakeContent = 'console.log("worker")';
    const fakeBlob = new Blob([fakeContent], { type: 'application/octet-stream' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    }));

    const src = await layWorkerSrc();
    expect(typeof src).toBe('string');
    expect(src.length).toBeGreaterThan(0);
  });

  it('layWorkerSrc tra ve fallback url khi fetch that bai', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));
    const src = await layWorkerSrc();
    expect(typeof src).toBe('string');
  });

  it('moPdf mo tai lieu thanh cong bang WorkerMessageHandler truc tiep (#328)', async () => {
    const bytes = new TextEncoder().encode(PDF_MINIMAL);
    const pdf = await moPdf(bytes.buffer);
    expect(pdf.numPages).toBe(1);
    await pdf.destroy();
  });
});
