import { apiClientBlob, downloadBlob } from '@lib/apiClient';
import { getAbsoluteFileUrl } from '@lib/fileUtils';

export interface AttachmentPreviewTarget {
  name: string;
  size?: number;
  url?: string;
  file?: File;
}

/**
 * Tránh tấn công XSS khi render nội dung văn bản HTML
 */
export function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Trích xuất các đoạn văn bản (paragraphs) từ tệp Word (.docx) bằng native Web Streams API
 * hoàn toàn không cần thư viện ngoài.
 */
export async function extractDocxParagraphs(arrayBuffer: ArrayBuffer): Promise<string[]> {
  const uint8 = new Uint8Array(arrayBuffer);
  const view = new DataView(uint8.buffer, uint8.byteOffset, uint8.byteLength);

  let offset = 0;
  while (offset < uint8.length - 4) {
    // 0x04034b50 là Local file header signature trong định dạng ZIP
    if (view.getUint32(offset, true) === 0x04034b50) {
      const compMethod = view.getUint16(offset + 8, true);
      const compSize = view.getUint32(offset + 18, true);
      const nameLen = view.getUint16(offset + 26, true);
      const extraLen = view.getUint16(offset + 28, true);
      const nameBytes = uint8.subarray(offset + 30, offset + 30 + nameLen);
      const name = new TextDecoder('utf-8').decode(nameBytes);
      const dataStart = offset + 30 + nameLen + extraLen;

      if (name === 'word/document.xml') {
        const compressedData = uint8.subarray(dataStart, dataStart + compSize);
        let xmlStr = '';
        if (compMethod === 0) {
          xmlStr = new TextDecoder('utf-8').decode(compressedData);
        } else if (compMethod === 8) {
          if (typeof DecompressionStream !== 'undefined') {
            const ds = new DecompressionStream('deflate-raw');
            const writer = ds.writable.getWriter();
            writer.write(compressedData);
            void writer.close();
            const response = new Response(ds.readable);
            xmlStr = await response.text();
          }
        }

        if (!xmlStr) return [];

        // Tách các thẻ đoạn văn bản <w:p>
        const paragraphs = xmlStr.match(/<w:p[\s>].*?<\/w:p>/g) || [];
        const lines = paragraphs
          .map((p) => {
            const texts = p.match(/<w:t[\s>].*?<\/w:t>/g) || [];
            return texts.map((t) => t.replace(/<[^>]+>/g, '')).join('');
          })
          .filter((line) => line.trim().length > 0);

        return lines;
      }
      offset = dataStart + compSize;
    } else {
      offset++;
    }
  }
  return [];
}

/**
 * Tạo trang HTML xem trước văn bản Word số hóa (.docx) chuẩn trang in A4
 */
export function generateDocxPreviewHtml(fileName: string, paragraphs: string[]): string {
  const safeTitle = escapeHtml(fileName);
  const bodyContent = paragraphs
    .map((p) => `<p style="margin: 0 0 12px 0; line-height: 1.7; text-align: justify;">${escapeHtml(p)}</p>`)
    .join('');

  return `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${safeTitle} - Xem trước văn bản</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 24px 16px;
      background-color: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .toolbar {
      width: 100%;
      max-width: 820px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 12px 18px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      position: sticky;
      top: 12px;
      z-index: 10;
    }
    .doc-info {
      display: flex;
      align-items: center;
      gap: 10px;
      overflow: hidden;
    }
    .doc-icon {
      font-size: 20px;
      color: #2563eb;
    }
    .doc-name {
      font-size: 14px;
      font-weight: 600;
      color: #0f172a;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 480px;
    }
    .btn-print {
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s ease;
    }
    .btn-print:hover { background: #1d4ed8; }
    .page-container {
      width: 100%;
      max-width: 820px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      padding: 60px 64px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      font-size: 14.5px;
    }
    @media print {
      body { background: #fff; padding: 0; }
      .toolbar { display: none; }
      .page-container { border: none; box-shadow: none; padding: 0; max-width: 100%; }
    }
    @media (max-width: 640px) {
      body { padding: 12px 8px; }
      .page-container { padding: 32px 20px; }
      .doc-name { max-width: 200px; }
    }
  </style>
</head>
<body>
  <div class="toolbar">
    <div class="doc-info">
      <span class="doc-icon">📄</span>
      <span class="doc-name" title="${safeTitle}">${safeTitle}</span>
    </div>
    <button class="btn-print" onclick="window.print()">🖨️ In văn bản</button>
  </div>
  <div class="page-container">
    ${bodyContent}
  </div>
</body>
</html>`;
}

function triggerLocalFileDownload(file: File, name: string) {
  if (typeof document === 'undefined') return;
  const tempUrl = URL.createObjectURL(file);
  const a = document.createElement('a');
  a.href = tempUrl;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(tempUrl), 60000);
}

/**
 * Mở xem trước tệp đính kèm trực tiếp trong tab trình duyệt mới (an toàn, không lỗi modal lồng nhau)
 */
export async function previewAttachmentInNewTab(target: AttachmentPreviewTarget): Promise<void> {
  if (typeof window === 'undefined') return;

  const ext = (target.name.split('.').pop() || '').toLowerCase();
  const isPdf = ext === 'pdf';
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp'].includes(ext);
  const isDocx = ext === 'docx';
  const isText = ['txt', 'log', 'json', 'xml', 'md'].includes(ext);
  const isBrowserDirect = isPdf || isImage || isText;

  // Mở trước tab mới để tránh popup blocker của trình duyệt
  let newTab: Window | null = null;
  if (isBrowserDirect || isDocx) {
    try {
      newTab = window.open('about:blank', '_blank');
      if (newTab && newTab.document) {
        newTab.document.title = `Đang nạp: ${target.name}...`;
      }
    } catch {
      newTab = null;
    }
  }

  try {
    // 1. Trường hợp tệp mới tải lên từ máy client
    if (target.file) {
      if (isBrowserDirect) {
        const blobUrl = URL.createObjectURL(target.file);
        if (newTab && !newTab.closed) {
          newTab.location.href = blobUrl;
        } else {
          window.open(blobUrl, '_blank');
        }
        setTimeout(() => URL.revokeObjectURL(blobUrl), 120000);
        return;
      }

      if (isDocx) {
        const arrayBuffer = await target.file.arrayBuffer();
        const paragraphs = await extractDocxParagraphs(arrayBuffer);
        if (paragraphs.length > 0) {
          const html = generateDocxPreviewHtml(target.name, paragraphs);
          const htmlBlob = new Blob([html], { type: 'text/html;charset=utf-8' });
          const htmlUrl = URL.createObjectURL(htmlBlob);
          if (newTab && !newTab.closed) {
            newTab.location.href = htmlUrl;
          } else {
            window.open(htmlUrl, '_blank');
          }
          setTimeout(() => URL.revokeObjectURL(htmlUrl), 120000);
          return;
        }
      }

      // Fallback cho file local khác: tải về máy
      if (newTab && !newTab.closed) newTab.close();
      triggerLocalFileDownload(target.file, target.name);
      return;
    }

    // 2. Trường hợp tệp hiện có trên máy chủ
    if (target.url) {
      if (isBrowserDirect) {
        try {
          const rawBlob = await apiClientBlob(target.url);
          let mimeType = rawBlob.type;
          if (isPdf) mimeType = 'application/pdf';
          else if (ext === 'png') mimeType = 'image/png';
          else if (ext === 'jpg' || ext === 'jpeg') mimeType = 'image/jpeg';
          else if (ext === 'webp') mimeType = 'image/webp';
          else if (ext === 'gif') mimeType = 'image/gif';
          else if (ext === 'svg') mimeType = 'image/svg+xml';
          else if (isText) mimeType = 'text/plain;charset=utf-8';

          const typedBlob = mimeType ? new Blob([rawBlob], { type: mimeType }) : rawBlob;
          const blobUrl = window.URL.createObjectURL(typedBlob);
          if (newTab && !newTab.closed) {
            newTab.location.href = blobUrl;
          } else {
            window.open(blobUrl, '_blank');
          }
          setTimeout(() => window.URL.revokeObjectURL(blobUrl), 120000);
          return;
        } catch {
          // Fallback dùng link trực tiếp của file
          const directUrl = getAbsoluteFileUrl(target.url);
          if (directUrl) {
            if (newTab && !newTab.closed) {
              newTab.location.href = directUrl;
            } else {
              window.open(directUrl, '_blank');
            }
            return;
          }
        }
      }

      if (isDocx) {
        try {
          const rawBlob = await apiClientBlob(target.url);
          const arrayBuffer = await rawBlob.arrayBuffer();
          const paragraphs = await extractDocxParagraphs(arrayBuffer);
          if (paragraphs.length > 0) {
            const html = generateDocxPreviewHtml(target.name, paragraphs);
            const htmlBlob = new Blob([html], { type: 'text/html;charset=utf-8' });
            const htmlUrl = URL.createObjectURL(htmlBlob);
            if (newTab && !newTab.closed) {
              newTab.location.href = htmlUrl;
            } else {
              window.open(htmlUrl, '_blank');
            }
            setTimeout(() => URL.revokeObjectURL(htmlUrl), 120000);
            return;
          }
        } catch {
          // Bỏ qua lỗi và chuyển sang tải về
        }
      }

      // Định dạng khác hoặc tải về:
      if (newTab && !newTab.closed) newTab.close();
      await downloadBlob(target.url, target.name);
      return;
    }
  } catch (err) {
    if (newTab && !newTab.closed) newTab.close();
    console.error('Lỗi khi mở xem trước tệp trong tab mới:', err);
    throw err;
  }
}
