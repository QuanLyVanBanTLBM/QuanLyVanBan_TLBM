/** Các tiện ích trình duyệt không phụ thuộc key pair. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { taoKhoaChongTrung } from './api';
import { sha256Hex } from './hash';

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const CRYPTO_THAT = globalThis.crypto;

describe('ngữ cảnh không an toàn', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('taoKhoaChongTrung sinh UUID v4 hợp lệ khi thiếu crypto.randomUUID', () => {
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array<ArrayBuffer>) => CRYPTO_THAT.getRandomValues(a) });
    const a = taoKhoaChongTrung();
    const b = taoKhoaChongTrung();
    expect(a).toMatch(UUID_V4);
    expect(a).not.toBe(b);
  });

  it('taoKhoaChongTrung dùng crypto.randomUUID khi có', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'ma-co-san' });
    expect(taoKhoaChongTrung()).toBe('ma-co-san');
  });

  it('tính SHA-256 bằng thư viện thuần JS khi thiếu crypto.subtle', async () => {
    vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array<ArrayBuffer>) => CRYPTO_THAT.getRandomValues(a) });
    const bytes = new TextEncoder().encode('abc');
    expect(await sha256Hex(bytes.buffer)).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  });
});
