/**
 * Ngữ cảnh không an toàn (HTTP không phải localhost): không có `crypto.randomUUID` và `crypto.subtle`.
 * - Khóa chống trùng vẫn sinh được UUID v4 hợp lệ.
 * - Các hàm mật mã (Ed25519, HKDF, AES-GCM) tự động chuyển sang fallback pure-JS an toàn,
 *   giúp trang Khóa ký và các thao tác ký hoạt động bình thường trên staging HTTP (Issue #534).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { b64, tuHex } from './khoaKy';
import { taoKhoaChongTrung } from './api';
import { bocKhoa, hoTroEd25519, kyBytes, moBanBoc, sinhCapKhoa, verifierTuMaster } from './khoaKy';

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

  it('các hàm mật mã hoạt động bình thường qua fallback khi thiếu crypto.subtle (HTTP)', async () => {
    giaLapKhongAnToan();
    expect(await hoTroEd25519()).toBe(true);

    const cap = await sinhCapKhoa();
    expect(cap.khoaCongKhai).toBeTruthy();
    expect(cap.privatePkcs8).toHaveLength(48);

    const master = Uint8Array.from({ length: 32 }, (_, i) => i);
    const verifier = await verifierTuMaster(master);
    expect(verifier).toBe('bffdbgw8LhLP+Al+NmLk7j0CNbl90+tECHWP0vHdoTQ=');

    const kSrv = b64(new Uint8Array(32));
    const ban = await bocKhoa(cap.privatePkcs8, master, kSrv);
    expect(ban.nonce).toBeTruthy();
    expect(ban.banBoc).toBeTruthy();

    const mo = await moBanBoc(ban, master, kSrv);
    expect(b64(mo)).toBe(b64(cap.privatePkcs8));

    const duLieu = tuHex('abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789');
    const chuKy = await kyBytes(mo, duLieu);
    expect(chuKy).toBeTruthy();
  });

  it('ném khong_ho_tro_webcrypto khi thiếu hoàn toàn crypto hoặc getRandomValues', async () => {
    vi.stubGlobal('crypto', undefined);
    expect(await hoTroEd25519()).toBe(false);
    await expect(sinhCapKhoa()).rejects.toThrow('khong_ho_tro_webcrypto');
  });
});
