/**
 * Mật mã phía trình duyệt theo contract #79: vector đối chiếu chéo với thư viện `cryptography` (Python) để bảo đảm
 * HKDF("verify"), HKDF(k_srv, "wrap") và AES-GCM khớp chuẩn mà backend/test Python dùng.
 */
import { describe, expect, it } from 'vitest';
import {
  b64, bocKhoa, danXuatPin, kiemTraPin, kyBytes, moBanBoc, sha256Hex, sinhCapKhoa, taoThamSoKdf, tuB64, tuHex,
  verifierTuMaster,
} from './khoaKy';
import en from './i18n/en.json';
import vi from './i18n/vi.json';
import { khungTuDiemBam } from './viTri';

const MASTER = Uint8Array.from({ length: 32 }, (_, i) => i);
const K_SRV = 'ZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoM=';

describe('dẫn xuất khóa khớp vector Python (cryptography)', () => {
  it('verifier = HKDF-SHA256(master, salt rỗng, "verify")', async () => {
    expect(await verifierTuMaster(MASTER)).toBe('bffdbgw8LhLP+Al+NmLk7j0CNbl90+tECHWP0vHdoTQ=');
  });

  it('khóa bọc = HKDF-SHA256(master, salt = k_srv, "wrap") mở được bản mã AES-GCM tạo bằng Python', async () => {
    const pt = await moBanBoc({ nonce: b64(new Uint8Array(12)), banBoc: 'P9d2vzT1U2fw8nwOXT1bdxx7L/qVmqrW3mXCBRkQKQ==' },
      MASTER, K_SRV);
    expect(new TextDecoder().decode(pt)).toBe('khoa-bi-mat-mau');
  });
});

describe('khóa Ed25519 và bản bọc', () => {
  it('bọc rồi mở lại private key; k_srv sai thì không mở được; chữ ký verify được', async () => {
    const cap = await sinhCapKhoa();
    const ban = await bocKhoa(cap.privatePkcs8, MASTER, K_SRV);
    const mo = await moBanBoc(ban, MASTER, K_SRV);
    expect(b64(mo)).toBe(b64(cap.privatePkcs8));
    await expect(moBanBoc(ban, MASTER, b64(new Uint8Array(32)))).rejects.toBeTruthy();

    const hash = await sha256Hex(new TextEncoder().encode('tai lieu').buffer as ArrayBuffer);
    const chu_ky = await kyBytes(mo, tuHex(hash));
    const pub = await crypto.subtle.importKey('raw', tuB64(cap.khoaCongKhai), { name: 'Ed25519' }, false, ['verify']);
    expect(await crypto.subtle.verify({ name: 'Ed25519' }, pub, tuB64(chu_ky), tuHex(hash))).toBe(true);
  });

  it('Argon2id: cùng PIN khác salt cho verifier khác; salt 16 byte mới mỗi lần', async () => {
    const a = taoThamSoKdf();
    const b = taoThamSoKdf();
    expect(tuB64(a.salt)).toHaveLength(16);
    expect(a.salt).not.toBe(b.salt);
    expect([a.m, a.t, a.p]).toEqual([65536, 3, 1]);
    const [va, vb, va2] = await Promise.all([danXuatPin('48273916', a), danXuatPin('48273916', b), danXuatPin('48273916', a)]);
    expect(va.verifier).not.toBe(vb.verifier);
    expect(va.verifier).toBe(va2.verifier);
  }, 30000);
});

describe('chính sách PIN 8 chữ số', () => {
  it.each([
    ['1234567', 'pin_8_chu_so'], ['1234567a', 'pin_8_chu_so'], ['77777777', 'pin_lap_mot_chu_so'],
    ['23456789', 'pin_day_lien_tiep'], ['98765432', 'pin_day_lien_tiep'], ['15081990', 'pin_dang_ngay'],
    ['11223344', 'pin_pho_bien'], ['48273916', null],
  ])('%s → %s', (pin, ma) => {
    expect(kiemTraPin(pin)).toBe(ma);
  });
});

describe('vị trí ký', () => {
  it('khung mặc định có tâm tại điểm bấm và nằm trọn trong trang', () => {
    expect(khungTuDiemBam(2, 50, 50)).toEqual({
      trang_ky: 2, toa_do_x: '35', toa_do_y: '45', chieu_rong_khung: '30', chieu_cao_khung: '10',
    });
    expect(khungTuDiemBam(1, 99, 99)).toMatchObject({ toa_do_x: '70', toa_do_y: '90' });
    expect(khungTuDiemBam(1, 0, 0)).toMatchObject({ toa_do_x: '0', toa_do_y: '0' });
  });
});

describe('từ điển vi/en', () => {
  const khoa = (o: object, tien_to = ''): string[] => Object.entries(o).flatMap(([k, v]) =>
    (v && typeof v === 'object' ? khoa(v, `${tien_to}${k}.`) : [`${tien_to}${k}`]));
  it('hai ngôn ngữ có cùng tập khóa', () => {
    expect(khoa(en).sort()).toEqual(khoa(vi).sort());
  });
});
