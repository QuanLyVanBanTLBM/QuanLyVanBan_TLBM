/**
 * Ngữ cảnh không an toàn (HTTP không phải localhost): không có `crypto.randomUUID` và `crypto.subtle`.
 * Khóa chống trùng vẫn sinh được; hàm mật mã báo lỗi có mã thay vì TypeError thô (Issue #343).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { taoKhoaChongTrung } from './api';
import { bocKhoa, kyBytes, moBanBoc, verifierTuMaster } from './khoaKy';

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

const CRYPTO_THAT = globalThis.crypto;

function giaLapKhongAnToan() {
  vi.stubGlobal('crypto', { getRandomValues: (a: Uint8Array<ArrayBuffer>) => CRYPTO_THAT.getRandomValues(a) });
}

describe('ngữ cảnh không an toàn', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('taoKhoaChongTrung sinh UUID v4 hợp lệ, không trùng khi thiếu crypto.randomUUID', () => {
    giaLapKhongAnToan();
    const a = taoKhoaChongTrung();
    const b = taoKhoaChongTrung();
    expect(a).toMatch(UUID_V4);
    expect(a).not.toBe(b);
  });

  it('taoKhoaChongTrung dùng crypto.randomUUID khi có', () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'ma-co-san' });
    expect(taoKhoaChongTrung()).toBe('ma-co-san');
  });

  it('các hàm mật mã ném khong_ho_tro_webcrypto khi thiếu crypto.subtle', async () => {
    giaLapKhongAnToan();
    const byte = new Uint8Array(32) as Uint8Array<ArrayBuffer>;
    await expect(verifierTuMaster(byte)).rejects.toThrow('khong_ho_tro_webcrypto');
    await expect(kyBytes(byte, byte)).rejects.toThrow('khong_ho_tro_webcrypto');
    await expect(bocKhoa(byte, byte, 'AAAA')).rejects.toThrow('khong_ho_tro_webcrypto');
    await expect(moBanBoc({ nonce: 'AAAA', banBoc: 'AAAA' }, byte, 'AAAA')).rejects.toThrow('khong_ho_tro_webcrypto');
  });
});
