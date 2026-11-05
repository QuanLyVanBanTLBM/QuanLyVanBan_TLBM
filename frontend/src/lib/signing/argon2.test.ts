import { afterEach, describe, expect, it, vi } from 'vitest';
import { dinhArgon2 } from './argon2';
import { type ThamSoArgon2, tinhArgon2 } from './argon2Tinh';

// Tham số nhỏ để test nhanh; kiểm giao thức và đường tính, không kiểm mức sàn bảo mật (đã có ở backend và khoaKy.test).
const SALT = new Uint8Array(16).fill(3) as Uint8Array<ArrayBuffer>;
const TS: ThamSoArgon2 = { password: '482739', salt: SALT, m: 32, t: 1, p: 1 };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('tinhArgon2', () => {
  it('trả đúng 32 byte và cùng đầu vào thì cùng kết quả', async () => {
    const a = await tinhArgon2(TS);
    const b = await tinhArgon2(TS);
    expect(a.byteLength).toBe(32);
    expect(a.buffer.byteLength).toBe(32);
    expect(Array.from(a)).toEqual(Array.from(b));
  });

  it('đổi PIN thì đổi master', async () => {
    const a = await tinhArgon2(TS);
    const b = await tinhArgon2({ ...TS, password: '482738' });
    expect(Array.from(a)).not.toEqual(Array.from(b));
  });
});

describe('argon2.worker (giao thức yêu cầu/phản hồi)', () => {
  it('trả master trong một thông điệp có transfer, khớp tinhArgon2', async () => {
    const spy = vi.fn();
    vi.stubGlobal('postMessage', spy);
    await import('./argon2.worker');
    const onmessage = (globalThis as unknown as { onmessage: (e: unknown) => Promise<void> }).onmessage;

    await onmessage({ data: { id: 7, ...TS } });

    expect(spy).toHaveBeenCalledTimes(1);
    const [msg, transfer] = spy.mock.calls[0];
    expect(msg.id).toBe(7);
    expect(msg.loi).toBeUndefined();
    expect(transfer).toHaveLength(1);
    expect(Array.from(new Uint8Array(msg.master))).toEqual(Array.from(await tinhArgon2(TS)));
  });

  it('tham số không hợp lệ trả lỗi có id, không ném ra ngoài worker', async () => {
    const spy = vi.fn();
    vi.stubGlobal('postMessage', spy);
    await import('./argon2.worker');
    const onmessage = (globalThis as unknown as { onmessage: (e: unknown) => Promise<void> }).onmessage;

    await onmessage({ data: { id: 9, ...TS, m: 0 } });

    expect(spy).toHaveBeenCalledTimes(1);
    const [msg, transfer] = spy.mock.calls[0];
    expect(msg.id).toBe(9);
    expect(typeof msg.loi).toBe('string');
    expect(transfer).toEqual([]);
  });
});

describe('dinhArgon2 khi không có Worker', () => {
  it('dùng luồng hiện tại và cho kết quả giống tinhArgon2', async () => {
    vi.stubGlobal('Worker', undefined);
    const a = await dinhArgon2(TS);
    expect(Array.from(a)).toEqual(Array.from(await tinhArgon2(TS)));
  });
});
