/**
 * Tìm các đường nét đứt (khung placeholder vẽ sẵn trong PDF gốc) từ operator list của pdf.js, để viewer che nét
 * đó quanh khung ký. Tệp gốc không bị sửa (mã băm khóa theo tệp gốc); chỉ ảnh hiển thị trên canvas bị che.
 * Tọa độ trả về theo điểm PDF của trang (gốc dưới-trái), là hộp bao của đường sau khi nhân ma trận hiện hành.
 */

export interface HopPdf { x0: number; y0: number; x1: number; y1: number }

export interface HangSo {
  save: number; restore: number; transform: number; setDash: number; constructPath: number;
  /** các lệnh kết thúc đường có tô nét (stroke, closeStroke, fillStroke, ...) */
  lenhToNet: number[];
}

type Ma = [number, number, number, number, number, number];
const DON_VI: Ma = [1, 0, 0, 1, 0, 0];

function nhan(a: Ma, b: Ma): Ma {
  return [
    a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
    a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
    a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5],
  ];
}

export function timNetDut(
  fnArray: ArrayLike<number>, argsArray: ArrayLike<unknown>, k: HangSo, dienTichTrang: number,
): HopPdf[] {
  const kq: HopPdf[] = [];
  const ngan: { m: Ma; dut: boolean }[] = [];
  let m = DON_VI;
  let dut = false;
  for (let i = 0; i < fnArray.length; i += 1) {
    const f = fnArray[i];
    const args = argsArray[i] as unknown[] | null;
    if (f === k.save) ngan.push({ m, dut });
    else if (f === k.restore) {
      const t = ngan.pop();
      if (t) ({ m, dut } = t);
    } else if (f === k.transform && Array.isArray(args) && args.length === 6) {
      m = nhan(args.map(Number) as Ma, m);
    } else if (f === k.setDash && Array.isArray(args)) {
      const mang = Array.from((args[0] as ArrayLike<number>) ?? []);
      dut = mang.length > 0 && mang.some((x) => Number(x) > 0);
    } else if (f === k.constructPath && Array.isArray(args) && dut && k.lenhToNet.includes(Number(args[0]))) {
      const hop = args[2] as ArrayLike<number> | null;
      if (!hop || hop.length < 4) continue;
      const goc = [[hop[0], hop[1]], [hop[2], hop[1]], [hop[2], hop[3]], [hop[0], hop[3]]]
        .map(([x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]);
      const xs = goc.map((p) => p[0]);
      const ys = goc.map((p) => p[1]);
      const h = { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
      // Viền bao phủ gần hết trang không phải khung placeholder: giữ nguyên
      if ((h.x1 - h.x0) * (h.y1 - h.y0) <= dienTichTrang * 0.5) kq.push(h);
    }
  }
  return kq;
}

/** Vùng khung ký theo tỷ lệ % trang (gốc trên-trái) -> hộp theo điểm PDF (gốc dưới-trái). */
export function khungSangHopPdf(
  k: { x: number; y: number; w: number; h: number }, rong: number, cao: number,
): HopPdf {
  const x0 = (k.x / 100) * rong;
  const x1 = x0 + (k.w / 100) * rong;
  const y1 = cao - (k.y / 100) * cao;
  return { x0, x1, y0: y1 - (k.h / 100) * cao, y1 };
}

export function giaoNhau(a: HopPdf, b: HopPdf): boolean {
  return a.x0 <= b.x1 && a.x1 >= b.x0 && a.y0 <= b.y1 && a.y1 >= b.y0;
}
