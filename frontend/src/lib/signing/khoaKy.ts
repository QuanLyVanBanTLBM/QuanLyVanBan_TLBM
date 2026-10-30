/**
 * Khóa ký Ed25519 và PIN phía trình duyệt — contract #79 (signing-backend-plan.md mục 3.4).
 *
 * - Private key sinh bằng WebCrypto, không rời trình duyệt; chỉ bản bọc AES-GCM nằm trong IndexedDB.
 * - master = Argon2id(PIN, salt 16 byte, m = 64 MiB, t = 3, p = 1); salt mới mỗi lần đặt/đổi PIN.
 * - verifier = HKDF-SHA256(master, salt rỗng, info "verify") gửi server; server trả k_srv khi verifier đúng.
 * - khóa bọc = HKDF-SHA256(master, salt = k_srv, info "wrap"); hai nhãn tách biệt để lộ CSDL server không suy
 *   ra được khóa bọc. Đổi PIN: server xoay vòng k_srv, client mở bằng k_srv cũ và bọc lại bằng k_srv mới.
 * - Server không nhận PIN, không nhận private key hay bản bọc.
 */
import { argon2id, sha256 } from 'hash-wasm';
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

// ── Chính sách PIN (8 chữ số) ─────────────────────────────────────────────────

const PIN_PHO_BIEN = new Set(['12345678', '87654321', '11223344', '12341234', '00000000', '20202020', '19001900']);

/** Trả mã lỗi i18n hoặc null nếu PIN đạt chính sách (plan mục 3.4). */
export function kiemTraPin(pin: string): string | null {
  if (!/^\d{8}$/.test(pin)) return 'pin_8_chu_so';
  const so = pin.split('').map(Number);
  if (so.every((d) => d === so[0])) return 'pin_lap_mot_chu_so';
  const tang = so.every((d, i) => i === 0 || d === (so[i - 1] + 1) % 10);
  const giam = so.every((d, i) => i === 0 || d === (so[i - 1] + 9) % 10);
  if (tang || giam) return 'pin_day_lien_tiep';
  const ngay = Number(pin.slice(0, 2));
  const thang = Number(pin.slice(2, 4));
  const nam = Number(pin.slice(4));
  if (ngay >= 1 && ngay <= 31 && thang >= 1 && thang <= 12 && nam >= 1900 && nam <= 2100) return 'pin_dang_ngay';
  if (PIN_PHO_BIEN.has(pin)) return 'pin_pho_bien';
  return null;
}

// ── Dẫn xuất khóa ─────────────────────────────────────────────────────────────

/** `crypto.subtle` chỉ có ở ngữ cảnh an toàn (HTTPS hoặc localhost); thiếu thì báo lỗi có mã thay vì TypeError thô. */
function subtle(): SubtleCrypto {
  if (typeof crypto === 'undefined' || !crypto.subtle) throw new Error('khong_ho_tro_webcrypto');
  return crypto.subtle;
}

export function taoThamSoKdf(): ThamSoKdf {
  return { ...KDF_MAC_DINH, salt: b64(crypto.getRandomValues(new Uint8Array(16))) };
}

async function master(pin: string, tham_so: ThamSoKdf): Promise<Bytes> {
  return new Uint8Array(await argon2id({
    password: pin, salt: tuB64(tham_so.salt), parallelism: tham_so.p, iterations: tham_so.t,
    memorySize: tham_so.m, hashLength: 32, outputType: 'binary',
  }));
}

async function hkdf(ikm: Bytes, salt: Bytes, info: string, dung: 'bits' | 'aes'): Promise<ArrayBuffer | CryptoKey> {
  const goc = await subtle().importKey('raw', ikm, 'HKDF', false, ['deriveBits', 'deriveKey']);
  const tham_so = { name: 'HKDF', hash: 'SHA-256', salt, info: new TextEncoder().encode(info) };
  if (dung === 'bits') return subtle().deriveBits(tham_so, goc, 256);
  return subtle().deriveKey(tham_so, goc, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
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
  return b64((await hkdf(m, new Uint8Array(0), 'verify', 'bits')) as ArrayBuffer);
}

async function khoaBoc(master_pin: Bytes, kSrvB64: string): Promise<CryptoKey> {
  return (await hkdf(master_pin, tuB64(kSrvB64), 'wrap', 'aes')) as CryptoKey;
}

// ── Khóa Ed25519 ──────────────────────────────────────────────────────────────

export function hoTroEd25519(): Promise<boolean> {
  if (typeof crypto === 'undefined' || !crypto?.subtle?.generateKey) {
    return Promise.resolve(false);
  }
  return crypto.subtle
    .generateKey({ name: 'Ed25519' }, false, ['sign', 'verify'])
    .then(() => true)
    .catch(() => false);
}

export interface CapKhoaMoi {
  khoaCongKhai: string;
  privatePkcs8: Bytes;
}

export async function sinhCapKhoa(): Promise<CapKhoaMoi> {
  if (typeof crypto === 'undefined' || !crypto?.subtle?.generateKey) {
    throw new Error('khong_ho_tro_webcrypto');
  }
  const cap = (await crypto.subtle.generateKey({ name: 'Ed25519' }, true, ['sign', 'verify'])) as CryptoKeyPair;
  const raw = await crypto.subtle.exportKey('raw', cap.publicKey);
  const pkcs8 = await crypto.subtle.exportKey('pkcs8', cap.privateKey);
  return { khoaCongKhai: b64(raw), privatePkcs8: new Uint8Array(pkcs8) };
}

async function nhapPrivate(pkcs8: Bytes): Promise<CryptoKey> {
  return subtle().importKey('pkcs8', pkcs8, { name: 'Ed25519' }, false, ['sign']);
}

/** Ký Base64 trên bytes cho trước (challenge UTF-8 hoặc raw SHA-256 của tài liệu). */
export async function kyBytes(pkcs8: Bytes, du_lieu: Bytes): Promise<string> {
  return b64(await subtle().sign({ name: 'Ed25519' }, await nhapPrivate(pkcs8), du_lieu));
}

export async function bocKhoa(pkcs8: Bytes, master_pin: Bytes, kSrv: string) {
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ct = await subtle().encrypt({ name: 'AES-GCM', iv: nonce }, await khoaBoc(master_pin, kSrv), pkcs8);
  return { nonce: b64(nonce), banBoc: b64(ct) };
}

/** Mở bản bọc; sai master/k_srv thì AES-GCM báo lỗi. */
export async function moBanBoc(ban: Pick<BanBocKhoa, 'nonce' | 'banBoc'>, master_pin: Bytes, kSrv: string): Promise<Bytes> {
  const pt = await subtle().decrypt({ name: 'AES-GCM', iv: tuB64(ban.nonce) }, await khoaBoc(master_pin, kSrv),
    tuB64(ban.banBoc));
  return new Uint8Array(pt);
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
