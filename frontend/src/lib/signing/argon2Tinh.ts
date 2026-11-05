/**
 * Phép tính Argon2id (RFC 9106) cho khóa ký, không phụ thuộc môi trường chạy.
 * Được gọi từ Web Worker (`argon2.worker.ts`) và từ luồng hiện tại khi không tạo được Worker.
 */
import { argon2id } from 'hash-wasm';

export interface ThamSoArgon2 {
  password: string;
  salt: Uint8Array<ArrayBuffer>;
  /** Bộ nhớ tính bằng KiB. */
  m: number;
  t: number;
  p: number;
}

/** Trả 32 byte master (bản sao độc lập, bộ đệm đúng 32 byte để chuyển được bằng transfer). */
export async function tinhArgon2(ts: ThamSoArgon2): Promise<Uint8Array<ArrayBuffer>> {
  const ra = await argon2id({
    password: ts.password, salt: ts.salt, parallelism: ts.p, iterations: ts.t,
    memorySize: ts.m, hashLength: 32, outputType: 'binary',
  });
  return new Uint8Array(ra);
}
