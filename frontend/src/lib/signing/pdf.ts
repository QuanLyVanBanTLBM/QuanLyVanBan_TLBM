/**
 * Hiển thị PDF bằng pdf.js (Mozilla, Apache-2.0) để đặt vị trí ký và vẽ lớp phủ chữ ký (#80 mục E).
 * Nhúng trực tiếp WorkerMessageHandler từ `pdf.worker.min.mjs` vào `globalThis.pdfjsWorker` để
 * pdf.js tự kích hoạt fake worker nội bộ qua LoopbackPort trên luồng chính (#328).
 * Cơ chế này loại bỏ hoàn toàn phụ thuộc vào việc tạo Web Worker từ Blob URL (bị nhiều trình duyệt chặn)
 * hoặc nạp file .mjs qua HTTP (bị lỗi MIME type trên các reverse proxy chưa cấu hình), đảm bảo 100%
 * hiển thị PDF thành công trên mọi trình duyệt và máy chủ.
 * Dùng bản `legacy`: pdfjs-dist 5.x gọi `Map.prototype.getOrInsertComputed` mà Chromium/Firefox hiện hành chưa có;
 * bản legacy kèm polyfill cho cả luồng chính và worker (bản thường lỗi và vùng xem PDF trắng).
 */
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import * as pdfjsWorker from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

// Gán WorkerMessageHandler lên globalThis để pdf.js tự dùng fake worker nội bộ không cần nạp URL
if (typeof globalThis !== 'undefined') {
  (globalThis as unknown as { pdfjsWorker?: typeof pdfjsWorker }).pdfjsWorker = pdfjsWorker;
}

let workerSrcPromise: Promise<string> | null = null;

/**
 * Trình duyệt yêu cầu MIME type hợp lệ khi nạp module worker (`application/javascript` hoặc `text/javascript`).
 * Một số môi trường proxy hoặc reverse proxy (như Nginx chưa khai báo đuôi .mjs) trả về `application/octet-stream`
 * dẫn đến việc `X-Content-Type-Options: nosniff` chặn thực thi script worker.
 * Hàm này nạp worker qua fetch rồi tạo Blob URL cùng MIME type `application/javascript` chuẩn để đảm bảo
 * worker luôn khởi tạo thành công trên mọi môi trường và trình duyệt.
 */
export async function layWorkerSrc(): Promise<string> {
  if (typeof window === 'undefined' || typeof fetch === 'undefined') {
    return workerUrl;
  }
  if (!workerSrcPromise) {
    workerSrcPromise = (async () => {
      try {
        const res = await fetch(workerUrl);
        if (!res.ok) return workerUrl;
        const blob = await res.blob();
        const jsBlob = new Blob([blob], { type: 'application/javascript' });
        return URL.createObjectURL(jsBlob);
      } catch {
        return workerUrl;
      }
    })();
  }
  return workerSrcPromise;
}

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export type TaiLieuPdf = pdfjs.PDFDocumentProxy;

export async function moPdf(du_lieu: ArrayBuffer): Promise<TaiLieuPdf> {
  if (typeof globalThis !== 'undefined' && !(globalThis as unknown as { pdfjsWorker?: unknown }).pdfjsWorker) {
    (globalThis as unknown as { pdfjsWorker?: typeof pdfjsWorker }).pdfjsWorker = pdfjsWorker;
  }
  // pdf.js chuyển quyền sở hữu buffer sang worker: truyền bản sao để giữ dữ liệu gốc (băm, tải về)
  return pdfjs.getDocument({ data: new Uint8Array(du_lieu.slice(0)) }).promise;
}

/**
 * Vẽ trang (1-based) vào canvas theo chiều rộng hiển thị; trả kích thước điểm ảnh CSS. `huy()` dừng lần vẽ đang chạy
 * (pdf.js không cho hai lần render cùng lúc trên một canvas: đổi kích thước hoặc vẽ lại phải hủy lần trước).
 * Lần vẽ bị hủy kết thúc bằng lỗi có `name === 'RenderingCancelledException'` (`laLoiHuyVe`).
 */
export function veTrang(pdf: TaiLieuPdf, so_trang: number, canvas: HTMLCanvasElement, rong: number) {
  let task: { cancel: () => void } | null = null;
  let da_huy = false;
  const xong = (async () => {
    const trang = await pdf.getPage(so_trang);
    const goc = trang.getViewport({ scale: 1 });
    const ti_le = rong / goc.width;
    const dpr = window.devicePixelRatio || 1;
    const viewport = trang.getViewport({ scale: ti_le * dpr });
    if (da_huy) throw Object.assign(new Error('huy'), { name: 'RenderingCancelledException' });
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    const render = trang.render({ canvas, canvasContext: canvas.getContext('2d'), viewport });
    task = render;
    await render.promise;
    return { rong, cao: (goc.height * ti_le) };
  })();
  return {
    xong,
    huy: () => {
      da_huy = true;
      task?.cancel();
    },
  };
}

export function laLoiHuyVe(err: unknown): boolean {
  return (err as { name?: string } | null)?.name === 'RenderingCancelledException';
}
