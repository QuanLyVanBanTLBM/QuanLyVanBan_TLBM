/** E2EE v1: AES-256-GCM + RSA-OAEP-SHA256 envelopes + ECDSA-P256 provenance.
 * Public-key fingerprints must be verified outside this server before first use.
 * No signing-module keys/PIN, private-key persistence or admin recovery key.
 */
import { argon2id } from 'hash-wasm';

type Bytes = Uint8Array<ArrayBuffer>;
export interface Vault { salt: string; nonce: string; ciphertext: string; recovery_nonce: string; recovery_ciphertext: string }
export interface PublicKeyRecord {
  id: number; user_id: number; username: string;
  encryption_public_key: string; signing_public_key: string; fingerprint: string;
}
export interface KeyRecord extends PublicKeyRecord { vault: Vault }
export interface UnlockedKey { record: KeyRecord; encryption: CryptoKey; signing: CryptoKey; privateData: string }
export interface SecretPayload { number: string; title: string; note: string; files: { name: string; data: string }[] }
export interface Envelope { key_id: number; wrapped_key: string; user_id?: number; revoked?: boolean }
export interface SealedDocument { id: string; nonce: string; ciphertext: string; envelopes: Envelope[]; signature: string }
export interface DeliveredDocument extends SealedDocument { author_id: number; author_fingerprint: string }
const encoder = new TextEncoder();
const MAX_BYTES = 16 * 1024 * 1024;
export const MAX_FILE_BYTES = 10 * 1024 * 1024;

export function b64(data: ArrayBuffer | Bytes): string {
  const bytes = new Uint8Array(data);
  let text = '';
  for (let i = 0; i < bytes.length; i += 8192) text += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(text);
}
export function unb64(text: string): Bytes {
  if (text.length > Math.ceil(MAX_BYTES / 3) * 4 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text)) throw new Error('confidential.invalidPayload');
  return Uint8Array.from(atob(text), c => c.charCodeAt(0));
}
const json = (value: unknown) => encoder.encode(JSON.stringify(value));
const nonce = () => crypto.getRandomValues(new Uint8Array(12));
async function sha(data: Bytes): Promise<string> {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(b => b.toString(16).padStart(2, '0')).join('');
}
export async function fingerprint(record: Pick<PublicKeyRecord, 'encryption_public_key' | 'signing_public_key'>): Promise<string> {
  const a = unb64(record.encryption_public_key), b = unb64(record.signing_public_key);
  const bytes = new Uint8Array(a.length + b.length); bytes.set(a); bytes.set(b, a.length);
  return sha(bytes);
}
export async function verifyIdentity(record: PublicKeyRecord, expected: string): Promise<void> {
  if (!expected || record.fingerprint !== expected || await fingerprint(record) !== expected) throw new Error('confidential.unverifiedKey');
}
const vaultAAD = (record: PublicKeyRecord) => json(['vault-v1', record.user_id, record.fingerprint]);
const documentAAD = (id: string, authorId: number, fp: string) => json(['document-v1', id, authorId, fp]);
function vaultMessage(userId: number, fp: string, vault: Vault): Bytes {
  return json(['vault-v1', userId, fp, vault.ciphertext, vault.nonce, vault.recovery_ciphertext, vault.recovery_nonce, vault.salt]);
}
async function aes(raw: Bytes): Promise<CryptoKey> {
  if (raw.length !== 32) throw new Error('confidential.invalidKey');
  return crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['encrypt', 'decrypt']);
}
async function passwordKey(password: string, salt: string): Promise<CryptoKey> {
  if (password.length > 1024 || unb64(salt).length !== 16) throw new Error('confidential.invalidVault');
  const raw = new Uint8Array(await argon2id({ password, salt: unb64(salt), parallelism: 1, iterations: 3,
    memorySize: 64 * 1024, hashLength: 32, outputType: 'binary' }));
  try { return await aes(raw); } finally { raw.fill(0); }
}
async function sign(key: CryptoKey, bytes: Bytes): Promise<string> {
  return b64(await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, bytes));
}
async function loadPrivate(record: KeyRecord, privateData: string): Promise<UnlockedKey> {
  const data: { encryption: string; signing: string } = JSON.parse(privateData);
  const encryption = await crypto.subtle.importKey('pkcs8', unb64(data.encryption), { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['decrypt']);
  const signing = await crypto.subtle.importKey('pkcs8', unb64(data.signing), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  // Challenge both keys: a corrupt/mismatched vault must never silently change identity.
  const challenge = crypto.getRandomValues(new Uint8Array(32));
  const encPublic = await crypto.subtle.importKey('spki', unb64(record.encryption_public_key), { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['encrypt']);
  const recovered = new Uint8Array(await crypto.subtle.decrypt({ name: 'RSA-OAEP' }, encryption,
    await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, encPublic, challenge)));
  const signPublic = await crypto.subtle.importKey('spki', unb64(record.signing_public_key), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  if (!challenge.every((v, i) => v === recovered[i]) || !await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, signPublic,
    unb64(await sign(signing, challenge)), challenge)) throw new Error('confidential.invalidVault');
  return { record, encryption, signing, privateData };
}
export async function createIdentity(userId: number, password: string) {
  if (password.length < 16 || password.length > 1024) throw new Error('confidential.passwordPolicy');
  const enc = await crypto.subtle.generateKey({ name: 'RSA-OAEP', modulusLength: 3072, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['encrypt', 'decrypt']);
  const sig = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const publicData = { encryption_public_key: b64(await crypto.subtle.exportKey('spki', enc.publicKey)), signing_public_key: b64(await crypto.subtle.exportKey('spki', sig.publicKey)) };
  const record: KeyRecord = { id: 0, user_id: userId, username: '', ...publicData, fingerprint: await fingerprint(publicData), vault: {} as Vault };
  const privateData = JSON.stringify({ encryption: b64(await crypto.subtle.exportKey('pkcs8', enc.privateKey)), signing: b64(await crypto.subtle.exportKey('pkcs8', sig.privateKey)) });
  const recoveryBytes = crypto.getRandomValues(new Uint8Array(32));
  const recoveryCode = b64(recoveryBytes);
  const salt = b64(crypto.getRandomValues(new Uint8Array(16))), iv = nonce(), recoveryIv = nonce();
  record.vault = { salt, nonce: b64(iv), recovery_nonce: b64(recoveryIv),
    ciphertext: b64(await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: vaultAAD(record) }, await passwordKey(password, salt), encoder.encode(privateData))),
    recovery_ciphertext: b64(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: recoveryIv, additionalData: vaultAAD(record) }, await aes(recoveryBytes), encoder.encode(privateData))) };
  recoveryBytes.fill(0);
  return { record, recoveryCode, registration: { ...publicData, vault: record.vault, signature: await sign(sig.privateKey, vaultMessage(userId, record.fingerprint, record.vault)) } };
}
export async function unlock(record: KeyRecord, password: string): Promise<UnlockedKey> {
  await verifyIdentity(record, record.fingerprint);
  const bytes = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(record.vault.nonce), additionalData: vaultAAD(record) },
    await passwordKey(password, record.vault.salt), unb64(record.vault.ciphertext));
  return loadPrivate(record, new TextDecoder().decode(bytes));
}
export async function recover(record: KeyRecord, recoveryCode: string, newPassword: string) {
  if (newPassword.length < 16 || newPassword.length > 1024) throw new Error('confidential.passwordPolicy');
  await verifyIdentity(record, record.fingerprint);
  const bytes = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(record.vault.recovery_nonce), additionalData: vaultAAD(record) },
    await aes(unb64(recoveryCode.trim())), unb64(record.vault.recovery_ciphertext));
  const loaded = await loadPrivate(record, new TextDecoder().decode(bytes));
  const salt = b64(crypto.getRandomValues(new Uint8Array(16))), iv = nonce();
  const vault = { ...record.vault, salt, nonce: b64(iv), ciphertext: b64(await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData: vaultAAD(record) }, await passwordKey(newPassword, salt), encoder.encode(loaded.privateData))) };
  return { vault, signature: await sign(loaded.signing, vaultMessage(record.user_id, record.fingerprint, vault)) };
}
export async function seal(payload: SecretPayload, sender: UnlockedKey, recipients: { record: PublicKeyRecord; expected: string }[]): Promise<SealedDocument> {
  const id = crypto.randomUUID(), iv = nonce(), rawKey = crypto.getRandomValues(new Uint8Array(32));
  const bytes = json(payload);
  if (bytes.length + 16 > MAX_BYTES) throw new Error('confidential.tooLarge');
  const ciphertext = b64(await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: documentAAD(id, sender.record.user_id, sender.record.fingerprint) }, await aes(rawKey), bytes));
  try {
    const all = [{ record: sender.record, expected: sender.record.fingerprint }, ...recipients];
    const unique = new Map(all.map(r => [r.record.id, r]));
    const envelopes: Envelope[] = [];
    for (const { record, expected } of unique.values()) {
      await verifyIdentity(record, expected);
      const publicKey = await crypto.subtle.importKey('spki', unb64(record.encryption_public_key), { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['encrypt']);
      envelopes.push({ key_id: record.id, wrapped_key: b64(await crypto.subtle.encrypt({ name: 'RSA-OAEP', label: documentAAD(id, sender.record.user_id, sender.record.fingerprint) }, publicKey, rawKey)) });
    }
    envelopes.sort((a, b) => a.key_id - b.key_id);
    const doc = { id, nonce: b64(iv), ciphertext, envelopes, signature: '' };
    doc.signature = await sign(sender.signing, await signedDocumentBytes(doc, sender.record.user_id, sender.record.fingerprint));
    return doc;
  } finally { rawKey.fill(0); }
}
async function signedDocumentBytes(doc: SealedDocument, authorId: number, fp: string): Promise<Bytes> {
  return json(['document-v1', doc.id, authorId, fp, doc.nonce, await sha(unb64(doc.ciphertext)),
    [...doc.envelopes].sort((a, b) => a.key_id - b.key_id).map(e => [e.key_id, e.wrapped_key])]);
}
export async function open(doc: DeliveredDocument, recipient: UnlockedKey, author: PublicKeyRecord, expected: string): Promise<SecretPayload> {
  await verifyIdentity(author, expected);
  if (doc.author_fingerprint !== expected || doc.author_id !== author.user_id) throw new Error('confidential.invalidSignature');
  const sigKey = await crypto.subtle.importKey('spki', unb64(author.signing_public_key), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  if (!await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, sigKey, unb64(doc.signature), await signedDocumentBytes(doc, doc.author_id, expected))) throw new Error('confidential.invalidSignature');
  const envelope = doc.envelopes.find(e => e.key_id === recipient.record.id && !e.revoked);
  if (!envelope) throw new Error('confidential.notFound');
  const aad = documentAAD(doc.id, doc.author_id, expected);
  const key = new Uint8Array(await crypto.subtle.decrypt({ name: 'RSA-OAEP', label: aad }, recipient.encryption, unb64(envelope.wrapped_key)));
  try {
    const bytes = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(doc.nonce), additionalData: aad }, await aes(key), unb64(doc.ciphertext));
    const payload: SecretPayload = JSON.parse(new TextDecoder().decode(bytes));
    if (typeof payload.number !== 'string' || typeof payload.title !== 'string' || typeof payload.note !== 'string' || !Array.isArray(payload.files) ||
        payload.files.some(f => typeof f.name !== 'string' || typeof f.data !== 'string')) throw new Error('confidential.invalidPayload');
    return payload;
  } finally { key.fill(0); }
}
