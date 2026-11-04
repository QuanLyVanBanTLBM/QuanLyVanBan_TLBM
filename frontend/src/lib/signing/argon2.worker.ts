/**
 * Web Worker dẫn xuất Argon2id: nhận `{ id, password, salt, m, t, p }`, trả `{ id, master }` hoặc `{ id, loi }`.
 * Chỉ đổi nơi tính so với luồng hiện tại; mỗi yêu cầu vẫn chạy đúng tham số mà khóa đã lưu.
 */
import { type ThamSoArgon2, tinhArgon2 } from './argon2Tinh';

type YeuCau = ThamSoArgon2 & { id: number };

// Worker không có kiểu DedicatedWorkerGlobalScope trong lib DOM của dự án, nên khai báo tối thiểu các phần dùng tới.
const ctx = self as unknown as {
  onmessage: ((e: MessageEvent<YeuCau>) => void) | null;
  postMessage(message: unknown, transfer: Transferable[]): void;
};

ctx.onmessage = async (e: MessageEvent<YeuCau>) => {
  const { id, ...ts } = e.data;
  try {
    const master = await tinhArgon2(ts);
    ctx.postMessage({ id, master: master.buffer }, [master.buffer]);
  } catch (err) {
    ctx.postMessage({ id, loi: err instanceof Error ? err.message : String(err) }, []);
  }
};
