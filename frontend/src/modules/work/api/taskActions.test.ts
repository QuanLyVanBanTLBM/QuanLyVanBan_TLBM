import { describe, it, expect, vi, beforeEach } from 'vitest';

async function loadResolver(apiBaseUrl: string) {
  vi.resetModules();
  vi.doMock('./client', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./client')>()),
    API_BASE_URL: apiBaseUrl,
  }));
  return (await import('./taskActions')).resolveDownloadUrl;
}

describe('resolveDownloadUrl', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('API_BASE_URL tương đối: ghép đường dẫn với origin trang (giữ nguyên cổng)', async () => {
    const resolve = await loadResolver('/api');
    expect(resolve('/api/work/attachments/8/download/')).toBe(
      `${window.location.origin}/api/work/attachments/8/download/`,
    );
  });

  it('API_BASE_URL tuyệt đối: ghép đường dẫn với origin của API (kể cả cổng 8088)', async () => {
    const resolve = await loadResolver('https://staging.example.vn:8088/api');
    expect(resolve('/api/work/attachments/8/download/')).toBe(
      'https://staging.example.vn:8088/api/work/attachments/8/download/',
    );
  });

  it('URL tuyệt đối cũ được giữ nguyên', async () => {
    const resolve = await loadResolver('/api');
    const old = 'https://staging.example.vn/api/work/attachments/8/download/';
    expect(resolve(old)).toBe(old);
  });
});
