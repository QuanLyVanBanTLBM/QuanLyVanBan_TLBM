/**
 * Khóa ký Ed25519 và PIN phía trình duyệt — contract #79 (signing-backend-plan.md mục 3.4).
 *
 * - Private key sinh bằng WebCrypto khi khả dụng, có fallback pure-JS (@noble/curves, @noble/ciphers, @noble/hashes)
 *   cho môi trường HTTP không an toàn (staging) hoặc trình duyệt chưa hỗ trợ WebCrypto Ed25519.
 * - Private key không rời trình duyệt; chỉ bản bọc AES-GCM nằm trong IndexedDB.
 * - master = Argon2id(PIN, salt 16 byte, m = 64 MiB, t = 3, p = 1); salt mới mỗi lần đặt/đổi PIN.
 * - verifier = HKDF-SHA256(master, salt rỗng, info "verify") gửi server; server trả k_srv khi verifier đúng.
 * - khóa bọc = HKDF-SHA256(master, salt = k_srv, info "wrap"); hai nhãn tách biệt để lộ CSDL server không suy
 *   ra được khóa bọc. Đổi PIN: server xoay vòng k_srv, client mở bằng k_srv cũ và bọc lại bằng k_srv mới.
 * - Server không nhận PIN, không nhận private key hay bản bọc.
 */
import { gcm } from '@noble/ciphers/aes.js';
import { ed25519 } from '@noble/curves/ed25519.js';
import { hkdf as nobleHkdf } from '@noble/hashes/hkdf.js';
import { sha256 as nobleSha256 } from '@noble/hashes/sha2.js';
import { sha256 } from 'hash-wasm';
import { dinhArgon2 } from './argon2';
import type { ThamSoKdf } from './types';

export const KDF_MAC_DINH = { thuat_toan: 'argon2id' as const, m: 64 * 1024, t: 3, p: 1, phien_ban: 19 };

/** Bytes trên ArrayBuffer thường (WebCrypto không nhận SharedArrayBuffer). */
export type Bytes = Uint8Array<ArrayBuffer>;

const DB_TEN = 'tlbm-signing';
const DB_KHO = 'ban-boc-khoa';

export interface BanBocKhoa {
  /** `${userId}:${keyId}` */
  ma: string;
  userId: number;
  keyId: number;
  maKhoa: string;
  khoaCongKhai: string;
  nonce: string;
  banBoc: string;
  thamSoKdf: ThamSoKdf;
  taoLuc: string;
}

// ── Base64, bytes ─────────────────────────────────────────────────────────────

export function b64(bytes: ArrayBuffer | Uint8Array): string {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = '';
  u8.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s);
}

export function tuB64(s: string): Bytes {
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
}

export function tuHex(hex: string): Bytes {
  return Uint8Array.from(hex.match(/.{2}/g) || [], (h) => parseInt(h, 16));
}

export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto?.subtle?.digest) {
    const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
    return Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('');
  }
  return sha256(new Uint8Array(data));
}

// ── Chính sách PIN (6 chữ số; PIN 8 chữ số đặt trước đây vẫn dùng để ký) ─────────────────────

const PIN_PHO_BIEN = new Set(['123456', '654321', '112233', '123123', '000000', '159753', '111222', '520520']);

/** Trả mã lỗi i18n hoặc null nếu PIN đạt chính sách (plan mục 3.4). */
export function kiemTraPin(pin: string): string | null {
  if (!/^\d{6}$/.test(pin)) return 'pin_6_chu_so';
  const so = pin.split('').map(Number);
  if (so.every((d) => d === so[0])) return 'pin_lap_mot_chu_so';
  const tang = so.every((d, i) => i === 0 || d === (so[i - 1] + 1) % 10);
  const giam = so.every((d, i) => i === 0 || d === (so[i - 1] + 9) % 10);
  if (tang || giam) return 'pin_day_lien_tiep';
  const ngay = Number(pin.slice(0, 2));
  const thang = Number(pin.slice(2, 4));
  if (ngay >= 1 && ngay <= 31 && thang >= 1 && thang <= 12) return 'pin_dang_ngay';
  if (PIN_PHO_BIEN.has(pin)) return 'pin_pho_bien';
  return null;
}

// ── Dẫn xuất khóa ─────────────────────────────────────────────────────────────

export function taoThamSoKdf(): ThamSoKdf {
  return { ...KDF_MAC_DINH, salt: b64(crypto.getRandomValues(new Uint8Array(16))) };
}

async function master(pin: string, tham_so: ThamSoKdf): Promise<Bytes> {
  return dinhArgon2({ password: pin, salt: tuB64(tham_so.salt), m: tham_so.m, t: tham_so.t, p: tham_so.p });
}

async function hkdfBytes(ikm: Bytes, salt: Bytes, info: string): Promise<Bytes> {
  if (typeof crypto !== 'undefined' && crypto?.subtle?.importKey && crypto?.subtle?.deriveBits) {
    try {
      const goc = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
      const tham_so = { name: 'HKDF', hash: 'SHA-256', salt, info: new TextEncoder().encode(info) };
      return new Uint8Array(await crypto.subtle.deriveBits(tham_so, goc, 256));
    } catch {
      // Fallback sang noble
    }
  }
  return nobleHkdf(nobleSha256, ikm, salt, new TextEncoder().encode(info), 32);
}

export interface DanXuatPin {
  verifier: string;
  master: Bytes;
}

/** Argon2id + HKDF("verify"): verifier (Base64, 32 byte) gửi server. Giữ master trong bộ nhớ để bọc/mở khóa. */
export async function danXuatPin(pin: string, tham_so: ThamSoKdf): Promise<DanXuatPin> {
  const m = await master(pin, tham_so);
  return { verifier: await verifierTuMaster(m), master: m };
}

/** verifier = HKDF-SHA256(master, salt rỗng, info "verify"), Base64. */
export async function verifierTuMaster(m: Bytes): Promise<string> {
  return b64(await hkdfBytes(m, new Uint8Array(0), 'verify'));
}

// ── Khóa Ed25519 ──────────────────────────────────────────────────────────────

/**
 * ASN.1 DER prefix cho PKCS#8 Ed25519 (RFC 8410):
 * 30 2e 02 01 00 30 05 06 03 2b 65 70 04 22 04 20 (16 bytes) + 32-byte seed = 48 bytes.
 */
const PKCS8_ED25519_PREFIX = Uint8Array.from([
  0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
]);

async function coWebCryptoEd25519(): Promise<boolean> {
  if (typeof crypto === 'undefined' || !crypto?.subtle?.generateKey || !crypto?.subtle?.importKey) {
    return false;
  }
  try {
    await crypto.subtle.generateKey({ name: 'Ed25519' }, false, ['sign', 'verify']);
    return true;
  } catch {
    return false;
  }
}

export async function hoTroEd25519(): Promise<boolean> {
  return typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function';
}

export interface CapKhoaMoi {
  khoaCongKhai: string;
  privatePkcs8: Bytes;
}

export async function sinhCapKhoa(): Promise<CapKhoaMoi> {
  if (await coWebCryptoEd25519()) {
    try {
      const cap = (await crypto.subtle.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify'])) as CryptoKeyPair;
      const raw = await crypto.subtle.exportKey('raw', cap.publicKey);
      const pkcs8 = await crypto.subtle.exportKey('pkcs8', cap.privateKey);
      return { khoaCongKhai: b64(raw), privatePkcs8: new Uint8Array(pkcs8) };
    } catch {
      // Fallback sang noble
    }
  }
  if (typeof crypto === 'undefined' || typeof crypto.getRandomValues !== 'function') {
    throw new Error('khong_ho_tro_webcrypto');
  }
  const seed = crypto.getRandomValues(new Uint8Array(32));
  const pub = ed25519.getPublicKey(seed);
  const pkcs8 = new Uint8Array(48);
  pkcs8.set(PKCS8_ED25519_PREFIX, 0);
  pkcs8.set(seed, 16);
  return { khoaCongKhai: b64(pub), privatePkcs8: pkcs8 };
}

function trichXuatSeed(pkcs8: Bytes): Bytes {
  if (pkcs8.length === 48) {
    return pkcs8.slice(16, 48);
  }
  if (pkcs8.length === 32) {
    return pkcs8;
  }
  throw new Error('pkcs8_khong_hop_le');
}

/** Ký Base64 trên bytes cho trước (challenge UTF-8 hoặc raw SHA-256 của tài liệu). */
export async function kyBytes(pkcs8: Bytes, du_lieu: Bytes): Promise<string> {
  if (await coWebCryptoEd25519()) {
    try {
      const key = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'Ed25519' }, false, ['sign']);
      const sig = await crypto.subtle.sign({ name: 'Ed25519' }, key, du_lieu);
      return b64(sig);
    } catch {
      // Fallback sang noble
    }
  }
  const seed = trichXuatSeed(pkcs8);
  const sig = ed25519.sign(du_lieu, seed);
  return b64(sig);
}

export async function bocKhoa(pkcs8: Bytes, master_pin: Bytes, kSrv: string) {
  if (typeof crypto === 'undefined' || typeof crypto.getRandomValues !== 'function') {
    throw new Error('khong_ho_tro_webcrypto');
  }
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const khoaBytes = await hkdfBytes(master_pin, tuB64(kSrv), 'wrap');
  if (typeof crypto !== 'undefined' && crypto?.subtle?.importKey && crypto?.subtle?.encrypt) {
    try {
      const key = await crypto.subtle.importKey('raw', khoaBytes, { name: 'AES-GCM' }, false, ['encrypt']);
      const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, pkcs8);
      return { nonce: b64(nonce), banBoc: b64(ct) };
    } catch {
      // Fallback sang noble
    }
  }
  const aes = gcm(khoaBytes, nonce);
  const ct = aes.encrypt(pkcs8);
  return { nonce: b64(nonce), banBoc: b64(ct) };
}

/** Mở bản bọc; sai master/k_srv thì AES-GCM báo lỗi. */
export async function moBanBoc(
  ban: Pick<BanBocKhoa, 'nonce' | 'banBoc'>, master_pin: Bytes, kSrv: string,
): Promise<Bytes> {
  const nonce = tuB64(ban.nonce);
  const ct = tuB64(ban.banBoc);
  const khoaBytes = await hkdfBytes(master_pin, tuB64(kSrv), 'wrap');
  if (typeof crypto !== 'undefined' && crypto?.subtle?.importKey && crypto?.subtle?.decrypt) {
    try {
      const key = await crypto.subtle.importKey('raw', khoaBytes, { name: 'AES-GCM' }, false, ['decrypt']);
      const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, key, ct);
      return new Uint8Array(pt);
    } catch (err) {
      if ((err as Error)?.name === 'OperationError') {
        throw err;
      }
    }
  }
  const aes = gcm(khoaBytes, nonce);
  return aes.decrypt(ct);
}

// ── IndexedDB ─────────────────────────────────────────────────────────────────

function moDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_TEN, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(DB_KHO, { keyPath: 'ma' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function giaoDich<T>(che_do: IDBTransactionMode, fn: (kho: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await moDb();
  return new Promise<T>((resolve, reject) => {
    const req = fn(db.transaction(DB_KHO, che_do).objectStore(DB_KHO));
    req.onsuccess = () => resolve(req.result as T);
    req.onerror = () => reject(req.error);
  }).finally(() => db.close());
}

export function luuBanBoc(ban: BanBocKhoa): Promise<unknown> {
  return giaoDich('readwrite', (kho) => kho.put(ban));
}

export async function layBanBoc(userId: number, keyId: number): Promise<BanBocKhoa | undefined> {
  return giaoDich<BanBocKhoa | undefined>('readonly', (kho) => kho.get(`${userId}:${keyId}`));
}

export function xoaBanBoc(userId: number, keyId: number): Promise<unknown> {
  return giaoDich('readwrite', (kho) => kho.delete(`${userId}:${keyId}`));
}
