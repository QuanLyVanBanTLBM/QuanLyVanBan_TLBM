/**
 * Hiển thị PDF bằng pdf.js (Mozilla, Apache-2.0) để đặt vị trí ký và vẽ lớp phủ chữ ký (#80 mục E).
 * Worker đóng gói cùng ứng dụng qua Vite (không tải script bên thứ ba lúc chạy).
 */
import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export type TaiLieuPdf = pdfjs.PDFDocumentProxy;

export async function moPdf(du_lieu: ArrayBuffer): Promise<TaiLieuPdf> {
  // pdf.js chuyển quyền sở hữu buffer sang worker: truyền bản sao để giữ dữ liệu gốc (băm, tải về)
  return pdfjs.getDocument({ data: new Uint8Array(du_lieu.slice(0)) }).promise;
}

/** Vẽ trang (1-based) vào canvas theo chiều rộng hiển thị; trả kích thước điểm ảnh CSS. */
export async function veTrang(pdf: TaiLieuPdf, so_trang: number, canvas: HTMLCanvasElement, rong: number) {
  const trang = await pdf.getPage(so_trang);
  const goc = trang.getViewport({ scale: 1 });
  const ti_le = rong / goc.width;
  const dpr = window.devicePixelRatio || 1;
  const viewport = trang.getViewport({ scale: ti_le * dpr });
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await trang.render({ canvas, canvasContext: canvas.getContext('2d'), viewport }).promise;
  return { rong, cao: (goc.height * ti_le) };
}
