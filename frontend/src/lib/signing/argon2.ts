/**
 * Điều phối Argon2id cho khóa ký: đẩy phép tính sang một Web Worker dùng chung để luồng giao diện không đứng
 * trong 0,3–0,5 s mỗi lần mở khóa ký. Nếu không tạo được Worker (môi trường test, CSP chặn) thì tính trên luồng
 * hiện tại; kết quả giống hệt nhau vì cùng một hàm `tinhArgon2`.
 */
import { type ThamSoArgon2, tinhArgon2 } from './argon2Tinh';

type Bytes = Uint8Array<ArrayBuffer>;
type PhanHoi = { id: number; master?: ArrayBuffer; loi?: string };

interface ChoKetQua {
  resolve: (b: Bytes) => void;
  reject: (e: Error) => void;
}

let worker: Worker | null = null;
let idCuoi = 0;
const dangCho = new Map<number, ChoKetQua>();

function laySoWorker(): Worker {
  if (worker) return worker;
  const w = new Worker(new URL('./argon2.worker.ts', import.meta.url), { type: 'module' });
  w.onmessage = (e: MessageEvent<PhanHoi>) => {
    const cho = dangCho.get(e.data.id);
    if (!cho) return;
    dangCho.delete(e.data.id);
    if (e.data.master) cho.resolve(new Uint8Array(e.data.master));
    else cho.reject(new Error(e.data.loi ?? 'argon2_loi'));
  };
  // Worker lỗi (không tải được mô-đun, lỗi nạp WASM): từ chối các yêu cầu đang chờ và tạo lại ở lần gọi sau.
  w.onerror = () => {
    for (const cho of dangCho.values()) cho.reject(new Error('argon2_worker_loi'));
    dangCho.clear();
    w.terminate();
    worker = null;
  };
  worker = w;
  return w;
}

/** Dẫn xuất master (32 byte) từ PIN và tham số KDF; không đổi thuật toán hay tham số so với `tinhArgon2`. */
export function dinhArgon2(ts: ThamSoArgon2): Promise<Bytes> {
  if (typeof Worker === 'undefined') return tinhArgon2(ts);
  let w: Worker;
  try {
    w = laySoWorker();
  } catch {
    return tinhArgon2(ts);
  }
  const id = ++idCuoi;
  return new Promise<Bytes>((resolve, reject) => {
    dangCho.set(id, { resolve, reject });
    w.postMessage({ id, ...ts });
  });
}
