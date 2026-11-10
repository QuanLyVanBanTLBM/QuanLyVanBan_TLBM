import { sha256 } from '@noble/hashes/sha2.js';

/** SHA-256 hex của bytes PDF; Web Crypto được ưu tiên, thư viện thuần JS dùng cho ngữ cảnh không an toàn. */
export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto?.subtle?.digest) {
    const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
    return Array.from(digest, (byte) => byte.toString(16).padStart(2, '0')).join('');
  }
  return Array.from(sha256(new Uint8Array(data)), (byte) => byte.toString(16).padStart(2, '0')).join('');
}
