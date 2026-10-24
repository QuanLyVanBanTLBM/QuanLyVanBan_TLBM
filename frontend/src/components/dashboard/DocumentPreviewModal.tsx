import React, { useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from '@i18n/translate';
import { Badge } from '@components/common';
import { DocumentItem, DocumentAttachment } from './ModernDashboardView';

export interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentItem | null;
  docType?: 'incoming' | 'outgoing' | 'resource';
  onNext?: () => void;
  onPrev?: () => void;
  hasNext?: boolean;
  hasPrev?: boolean;
  currentIndex?: number;
  totalDocs?: number;
}

// Kiểm tra định dạng tệp có phải là tài liệu Word (.doc / .docx) hay không
const isDocFile = (att: DocumentAttachment): boolean => {
  const name = (att.name || '').toLowerCase();
  const type = (att.type || '').toLowerCase();
  const format = (att.format || '').toLowerCase();
  return (
    name.endsWith('.doc') ||
    name.endsWith('.docx') ||
    type === 'doc' ||
    type === 'docx' ||
    type === 'word' ||
    format === 'doc' ||
    format === 'docx'
  );
};

// Khởi tạo trang HTML xem trước văn bản số hóa mở trong tab mới
function generateDocumentPreviewHtml(
  doc: DocumentItem,
  meta: Record<string, unknown>,
  att: DocumentAttachment
): string {
  const isExcel =
    att.type === 'excel' ||
    (att.name || '').toLowerCase().endsWith('.xlsx') ||
    (att.name || '').toLowerCase().endsWith('.xls');

  return `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${att.name} - Xem Trước Văn Bản Số Hóa</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: #0b1329;
      color: #0f172a;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .top-toolbar {
      position: sticky;
      top: 0;
      width: 100%;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 100;
      color: #f8fafc;
    }
    .toolbar-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .toolbar-badge {
      background: rgba(59, 130, 246, 0.2);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 3px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 700;
    }
    .toolbar-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      font-family: inherit;
    }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.1);
      color: #f8fafc;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.2); }
    .preview-container {
      width: 100%;
      max-width: 900px;
      margin: 32px auto 60px;
      padding: 0 16px;
    }
    .document-paper {
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05);
      padding: 64px 72px;
      min-height: 1050px;
      position: relative;
    }
    .doc-header-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      padding-bottom: 24px;
      border-bottom: 2px solid #e2e8f0;
    }
    .header-left { text-align: center; }
    .header-left .agency {
      font-size: 13px;
      font-weight: 700;
      color: #1e293b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      line-height: 1.4;
    }
    .header-left .doc-no {
      font-size: 13px;
      font-weight: 700;
      color: #2563eb;
      margin-top: 8px;
    }
    .header-right { text-align: center; }
    .motto-country {
      font-size: 13px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: 0.5px;
    }
    .motto-sub {
      font-size: 13px;
      font-weight: 600;
      color: #334155;
      margin-top: 4px;
    }
    .motto-divider {
      width: 140px;
      height: 1px;
      background: #0f172a;
      margin: 6px auto;
    }
    .doc-date {
      font-size: 13px;
      font-style: italic;
      color: #64748b;
      margin-top: 8px;
    }
    .doc-title-block {
      margin: 40px 0 32px;
      text-align: center;
    }
    .doc-title-main {
      font-size: 19px;
      font-weight: 800;
      color: #0f172a;
      line-height: 1.45;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    .doc-title-desc {
      font-size: 14px;
      font-style: italic;
      color: #475569;
    }
    .doc-body {
      font-size: 15px;
      line-height: 1.8;
      color: #1e293b;
      margin-bottom: 40px;
    }
    .doc-body p {
      margin-bottom: 16px;
      text-align: justify;
    }
    .doc-body .clause-title {
      font-weight: 700;
      color: #0f172a;
    }
    .doc-footer-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 32px;
      margin-top: 48px;
      padding-top: 24px;
      border-top: 1px dashed #cbd5e1;
    }
    .recipients-block {
      font-size: 13px;
      color: #334155;
    }
    .recipients-title {
      font-weight: 700;
      font-style: italic;
      margin-bottom: 6px;
    }
    .recipients-list {
      list-style-type: none;
      line-height: 1.6;
    }
    .signature-block {
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .signer-role {
      font-size: 14px;
      font-weight: 800;
      text-transform: uppercase;
      color: #0f172a;
      margin-bottom: 8px;
    }
    .seal-stamp {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 2px dashed #dc2626;
      border-radius: 12px;
      padding: 10px 18px;
      background: rgba(220, 38, 38, 0.04);
      color: #dc2626;
      margin: 12px 0;
    }
    .seal-stamp-title {
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .seal-stamp-desc {
      font-size: 11px;
      margin-top: 2px;
      font-weight: 600;
    }
    .signer-name {
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
      margin-top: 6px;
    }
    .security-badge {
      margin-top: 36px;
      padding: 12px 16px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: #64748b;
    }
    .excel-table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-size: 13px;
    }
    .excel-table th, .excel-table td {
      border: 1px solid #cbd5e1;
      padding: 10px 12px;
      text-align: left;
    }
    .excel-table th {
      background: #f1f5f9;
      font-weight: 700;
      color: #0f172a;
    }
    @media print {
      body { background: white; padding: 0; }
      .top-toolbar { display: none; }
      .preview-container { margin: 0; max-width: 100%; padding: 0; }
      .document-paper { box-shadow: none; border-radius: 0; padding: 15mm 15mm; min-height: auto; }
    }
  </style>
</head>
<body>
  <div class="top-toolbar">
    <div class="toolbar-title">
      <i class="fa-solid fa-file-pdf" style="color: #ef4444; font-size: 18px;"></i>
      <span>${att.name}</span>
      <span class="toolbar-badge">${att.size || 'Bản số hóa'}</span>
    </div>
    <div class="toolbar-actions">
      <button class="btn btn-secondary" onclick="window.print()" title="In văn bản hoặc xuất PDF">
        <i class="fa-solid fa-print"></i> In / Xuất PDF
      </button>
      <button class="btn btn-primary" onclick="window.close()" title="Đóng cửa sổ xem trước">
        <i class="fa-solid fa-xmark"></i> Đóng
      </button>
    </div>
  </div>

  <div class="preview-container">
    <div class="document-paper">
      <div class="doc-header-grid">
        <div class="header-left">
          <div class="agency">${meta.place || 'CƠ QUAN BAN HÀNH'}</div>
          <div class="doc-no">Số: ${doc.code}</div>
        </div>
        <div class="header-right">
          <div class="motto-country">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
          <div class="motto-sub">Độc lập - Tự do - Hạnh phúc</div>
          <div class="motto-divider"></div>
          <div class="doc-date">Ngày ${doc.date}</div>
        </div>
      </div>

      <div class="doc-title-block">
        <h1 class="doc-title-main">${doc.title}</h1>
        <div class="doc-title-desc">Bản số hóa chính thức trích xuất từ Hệ thống Quản lý Văn bản và Tài liệu Bảo Long</div>
      </div>

      <div class="doc-body">
        <p><strong>Căn cứ:</strong> Luật Quản lý Văn bản và Lưu trữ số 33/2024/QH15;</p>
        <p><strong>Căn cứ:</strong> Quy chế công tác văn thư và bảo vệ bí mật cơ quan;</p>
        <p><strong>Căn cứ:</strong> Tờ trình đề xuất của đơn vị chủ trì và ý kiến phê duyệt của Ban Lãnh đạo;</p>
        
        <p style="margin-top: 20px;"><span class="clause-title">Điều 1.</span> Ban hành kèm theo văn bản này danh mục tài liệu số hóa và nội dung tác nghiệp nghiệp vụ: <em>"${doc.title}"</em>.</p>
        <p><span class="clause-title">Điều 2.</span> Văn bản này có hiệu lực kể từ ngày ký. Các phòng ban, đơn vị trực thuộc và các cá nhân liên quan chịu trách nhiệm thi hành.</p>
        <p><span class="clause-title">Điều 3.</span> Giao Văn thư cơ quan và Bộ phận Công nghệ thông tin theo dõi tiến độ, lưu trữ hồ sơ theo đúng thời hạn quy định.</p>

        ${isExcel ? `
          <div style="margin-top: 24px;">
            <p class="clause-title" style="margin-bottom: 8px;">PHỤ LỤC THỐNG KÊ CHI TIẾT ĐÍNH KÈM:</p>
            <table class="excel-table">
              <thead>
                <tr>
                  <th style="width: 60px;">STT</th>
                  <th>Hạng Mục Nghiệp Vụ</th>
                  <th style="width: 140px;">Đơn Vị Chủ Trì</th>
                  <th style="width: 120px;">Trạng Thái</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>01</td>
                  <td>Tiếp nhận và lập hồ sơ số hóa ban đầu</td>
                  <td>Văn phòng ITC</td>
                  <td><span style="color: #16a34a; font-weight: 600;">Hoàn tất</span></td>
                </tr>
                <tr>
                  <td>02</td>
                  <td>Thẩm định tính toàn vẹn và chữ ký số</td>
                  <td>Ban Giám Hiệu</td>
                  <td><span style="color: #2563eb; font-weight: 600;">Đã xác thực</span></td>
                </tr>
                <tr>
                  <td>03</td>
                  <td>Phân phối và lưu trữ kho hồ sơ điện tử</td>
                  <td>Tổ Lưu trữ</td>
                  <td><span style="color: #16a34a; font-weight: 600;">Đang lưu kho</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        ` : ''}
      </div>

      <div class="doc-footer-grid">
        <div class="recipients-block">
          <div class="recipients-title">Nơi nhận:</div>
          <ul class="recipients-list">
            <li>- Như Điều 2;</li>
            <li>- Ban Giám đốc (để b/c);</li>
            <li>- Các đơn vị liên quan;</li>
            <li>- Lưu: VT, HS.</li>
          </ul>
        </div>
        <div class="signature-block">
          <div class="signer-role">${meta.signerRole || 'LÃNH ĐẠO ĐƠN VỊ'}</div>
          <div class="seal-stamp">
            <i class="fa-solid fa-stamp" style="font-size: 18px; margin-bottom: 4px;"></i>
            <div class="seal-stamp-title">XÁC THỰC KÝ SỐ</div>
            <div class="seal-stamp-desc">Ký bởi: ${meta.signer || 'Ban Lãnh Đạo'}</div>
            <div class="seal-stamp-desc">Thời gian: ${doc.date} 09:00:00</div>
          </div>
          <div class="signer-name">${meta.signer || 'Ban Lãnh Đạo'}</div>
        </div>
      </div>

      <div class="security-badge">
        <span><i class="fa-solid fa-shield-halved" style="color: #16a34a;"></i> Văn bản số hóa đã được kiểm tra tính toàn vẹn và xác thực PKI</span>
        <span>Mã tra cứu: <strong>${doc.code}</strong></span>
      </div>
    </div>
  </div>
</body>
</html>`;
}

export default function DocumentPreviewModal({
  isOpen,
  onClose,
  document,
  docType = 'incoming',
  onNext,
  onPrev,
  hasNext = false,
  hasPrev = false,
  currentIndex = 0,
  totalDocs = 1,
}: DocumentPreviewModalProps) {
  const { t } = useTranslation();

  // Keyboard navigation: Escape to close, Left/Right arrow to switch doc
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight' && hasNext && onNext) {
        onNext();
      } else if (e.key === 'ArrowLeft' && hasPrev && onPrev) {
        onPrev();
      }
    },
    [isOpen, onClose, hasNext, onNext, hasPrev, onPrev]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Helper derivation for rich fields matching Group 2 specifications
  const docMeta = useMemo(() => {
    if (!document) return null;

    // Numerical index or fallback from code
    const numericPart = document.code.match(/\d+/)?.[0] || '8';
    const arrivalNo = document.arrivalNumber ?? `#${numericPart}`;
    const year = document.bookYear ?? (document.date ? document.date.split('/')[2] || '2026' : '2026');
    const arrivalDate = document.arrivalDate ?? document.date;

    // Issuing place and authority
    let place = document.issuingPlace || document.sender;
    let signer = document.signer;
    let signerRole = document.signerRole;

    if (!place) {
      if (document.code.includes('HĐND') || document.code.includes('NQ')) {
        place = 'Hội đồng Nhân dân TP. Hồ Chí Minh';
        signer = signer || 'Nguyễn Thị Lệ';
        signerRole = signerRole || 'Chủ tịch HĐND';
      } else if (document.code.includes('STC') || document.code.includes('TB-STC')) {
        place = 'Sở Tài chính TP. Hồ Chí Minh';
        signer = signer || 'Lê Duy Minh';
        signerRole = signerRole || 'Giám đốc Sở';
      } else if (document.code.includes('SGDĐT') || document.code.includes('KH')) {
        place = 'Sở Giáo dục và Đào tạo TP. Hồ Chí Minh';
        signer = signer || 'Nguyễn Văn Hiếu';
        signerRole = signerRole || 'Giám đốc Sở';
      } else if (document.code.includes('BTTTT')) {
        place = 'Bộ Thông tin và Truyền thông';
        signer = signer || 'Nguyễn Mạnh Hùng';
        signerRole = signerRole || 'Bộ trưởng';
      } else if (document.code.includes('UBND')) {
        place = 'Ủy ban Nhân dân TP. Hồ Chí Minh';
        signer = signer || 'Phan Văn Mãi';
        signerRole = signerRole || 'Chủ tịch UBND';
      } else {
        place = docType === 'outgoing' ? 'Tổng Công ty CP Bảo hiểm Bảo Long' : 'Cơ quan ban hành nhà nước';
        signer = signer || 'Trần Văn Nam';
        signerRole = signerRole || 'Phó Tổng Giám đốc';
      }
    }

    // Validity determination
    let validity = document.validityStatus;
    let validityLabel = document.validityStatusLabel;
    let replacedBy = document.replacedBy;

    if (!validity) {
      if (document.code.includes('56/NQ-HĐND') || document.code.includes('42/TB-UBND')) {
        validity = 'expired';
        validityLabel = t('documentPreview.validStatusExpired');
        replacedBy = replacedBy || '15/CV-BGDĐT';
      } else if (document.code.includes('102/KH-SGDĐT') || document.code.includes('125')) {
        validity = 'partial';
        validityLabel = t('documentPreview.validStatusPartial');
      } else {
        validity = 'valid';
        validityLabel = t('documentPreview.validStatusActive');
      }
    }



    // Danh sách 5 tệp demo chuẩn lấy từ thư mục File_test
    const DEMO_TEST_FILES: DocumentAttachment[] = [
      {
        name: '0. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026.pdf',
        size: '612 KB',
        date: document.date,
        type: 'pdf',
        url: '/demo_files/0. TB Chieu sinh Tieng Anh dau ra Dot 4 - 2026.pdf',
      },
      {
        name: 'BaiTap_Buoi06_506250495.docx',
        size: '98 KB',
        date: document.date,
        type: 'word',
        url: '/demo_files/BaiTap_Buoi06_506250495.docx',
      },
      {
        name: 'THỜI _KHÓA _BIỂU.xlsx',
        size: '12 KB',
        date: document.date,
        type: 'excel',
        url: '/demo_files/TH%E1%BB%9CI%20_KH%C3%93A%20_BI%E1%BB%82U.xlsx',
      },
      {
        name: 'anhtest.jpg',
        size: '1.4 MB',
        date: document.date,
        type: 'image',
        url: '/demo_files/anhtest.jpg',
      },
      {
        name: 'test.png',
        size: '394 KB',
        date: document.date,
        type: 'image',
        url: '/demo_files/test.png',
      },
    ];

    // Bảng chỉ định tệp demo cụ thể cho từng mục văn bản chính (mỗi mục đúng 1 file)
    const SPECIFIC_DOC_FILE_MAP: Record<string, number> = {
      '128/QĐ-UBND': 0, // 0. TB Chieu sinh... (PDF - Mở tab mới xem trước)
      '45/CV-STTTT': 1,  // BaiTap_Buoi06... (Word - Tự động tải về)
      '09/BC-TTr': 2,    // THỜI _KHÓA _BIỂU.xlsx (Excel - Mở tab mới)
      '88/TB-VP': 3,     // anhtest.jpg (Ảnh JPG - Mở tab mới)
      '12/KH-SNV': 4,    // test.png (Ảnh PNG - Mở tab mới)
      '52/TTr-ITC': 1,   // BaiTap_Buoi06... (Word - Tự động tải về)
      '104/GM-VP': 0,    // 0. TB Chieu sinh... (PDF - Mở tab mới)
      '77/TB-BGD': 2,    // THỜI _KHÓA _BIỂU.xlsx (Excel - Mở tab mới)
      '33/CV-CNTT': 3,   // anhtest.jpg (Ảnh JPG - Mở tab mới)
      '15/QĐ-ITC': 4,    // test.png (Ảnh PNG - Mở tab mới)
      '56/NQ-HĐND': 0,   // 0. TB Chieu sinh... (PDF - Test case modal)
    };

    // Mỗi một mục văn bản CHỈ CÓ ĐÚNG 1 tệp đính kèm duy nhất
    let attachments: DocumentAttachment[];
    if (document.attachments && document.attachments.length > 0) {
      attachments = [document.attachments[0]];
    } else {
      const mappedIdx = SPECIFIC_DOC_FILE_MAP[document.code];
      if (mappedIdx !== undefined) {
        attachments = [DEMO_TEST_FILES[mappedIdx]];
      } else {
        const codeNum = parseInt(document.code.match(/\d+/)?.[0] || '0', 10);
        const idx = Math.abs(codeNum) % DEMO_TEST_FILES.length;
        attachments = [DEMO_TEST_FILES[idx]];
      }
    }

    return {
      arrivalNo,
      year,
      arrivalDate,
      place,
      signer,
      signerRole,
      validity,
      validityLabel,
      replacedBy,
      note: document.note || (validity === 'expired' ? `Đã được thay thế bởi văn bản ${replacedBy}` : undefined),
      attachments,
      creator: document.creator || 'Trí Kiệt Lê',
      createdAt: document.createdAt || `${document.date} 08:30:00`,
      updatedAt: document.updatedAt || `${document.date} 09:15:00`,
    };
  }, [document, docType, t]);

  if (!isOpen || !document || !docMeta) return null;

  // Tải về bản thông tin tóm tắt định dạng text
  const handleDownload = () => {
    const content = `=====================================================
${t('documentPreview.companyName')}
${t('documentPreview.nationalRepublic')}
${t('documentPreview.nationalMotto')}
=====================================================
${t('documentPreview.docNumberLabel')} ${document.code}
${t('documentPreview.locationDate')} ${document.date}
TRÍCH YẾU: ${document.title}

CƠ QUAN BAN HÀNH: ${docMeta.place}
NGƯỜI KÝ: ${docMeta.signer} (${docMeta.signerRole})
TRẠNG THÁI HIỆU LỰC: ${docMeta.validityLabel}

${t('documentPreview.article1')} ${document.title}
${t('documentPreview.article2')}

${t('documentPreview.recipients')}
- ${t('documentPreview.recipientsBgd')}
- ${t('documentPreview.recipientsDepts')}
- ${t('documentPreview.recipientsArchive')}

${docMeta.signerRole}
[${t('documentPreview.digitalSignature')}]
${docMeta.signer}
${t('documentPreview.signDate')} ${document.date}
=====================================================`;

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement('a');
    link.href = url;
    link.download = `${document.code.replace(/[/\\?%*:|"<>]/g, '_')}.txt`;
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 1. Tự động tải về khi người dùng ấn vào tệp định dạng Word (.doc / .docx)
  const downloadDocFile = (att: DocumentAttachment) => {
    if (att.url) {
      const link = window.document.createElement('a');
      link.href = att.url;
      link.download = att.name;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      return;
    }

    const wordContent = `=====================================================
${t('documentPreview.companyName')}
${t('documentPreview.nationalRepublic')}
${t('documentPreview.nationalMotto')}
=====================================================
TÀI LIỆU VĂN BẢN ĐÍNH KÈM (MICROSOFT WORD)
Tên tệp: ${att.name}
Mã / Số hiệu văn bản: ${document.code}
Ngày văn bản: ${document.date}
Cơ quan ban hành: ${docMeta.place}
Người ký: ${docMeta.signer} (${docMeta.signerRole})
Trạng thái hiệu lực: ${docMeta.validityLabel}

TRÍCH YẾU NỘI DUNG:
${document.title}

NỘI DUNG VĂN BẢN / DỰ THẢO:
${t('documentPreview.article1')} ${document.title}
${t('documentPreview.article2')}

NƠI NHẬN:
- ${t('documentPreview.recipientsBgd')}
- ${t('documentPreview.recipientsDepts')}
- ${t('documentPreview.recipientsArchive')}

${docMeta.signerRole}
[Chữ ký điện tử số hóa xác thực]
${docMeta.signer}
Ngày ký: ${document.date}
=====================================================`;

    const isOldDoc = att.name.toLowerCase().endsWith('.doc');
    const mimeType = isOldDoc
      ? 'application/msword'
      : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

    const blob = new Blob([wordContent], { type: `${mimeType};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement('a');
    link.href = url;
    link.download = att.name;
    window.document.body.appendChild(link);
    link.click();
    window.document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 2. Tự động mở cửa sổ mới trên web để xem trước đối với các định dạng khác (PDF, PNG, Excel...)
  const previewFileInNewWindow = (att: DocumentAttachment) => {
    if (att.url) {
      window.open(att.url, '_blank', 'noopener,noreferrer');
      return;
    }

    const previewHtml = generateDocumentPreviewHtml(document, docMeta, att);
    const blob = new Blob([previewHtml], { type: 'text/html;charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);
    const newWindow = window.open(blobUrl, '_blank');
    if (!newWindow) {
      window.open(blobUrl, '_self');
    }
  };

  // Bộ điều hướng hành vi tệp đính kèm theo quy chuẩn
  const handleAttachmentAction = (att: DocumentAttachment) => {
    if (isDocFile(att)) {
      downloadDocFile(att);
    } else {
      previewFileInNewWindow(att);
    }
  };

  const handleOpenFile = (att: DocumentAttachment) => {
    handleAttachmentAction(att);
  };

  const modalTitle =
    docType === 'incoming'
      ? t('documentPreview.modalTitleIncoming')
      : docType === 'outgoing'
      ? t('documentPreview.modalTitleOutgoing')
      : t('documentPreview.modalTitleResource');

  const modalContent = (
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-5 overflow-y-auto animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-detail-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col bg-surface rounded-2xl sm:rounded-3xl shadow-2xl border border-border-subtle overflow-hidden my-auto animate-in zoom-in-95 duration-200">
        {/* 1. Header */}
        <div className="p-5 sm:p-6 pb-4 border-b border-border-subtle bg-surface flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <i className="fa-regular fa-file-lines text-lg sm:text-xl" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2
                  id="document-detail-modal-title"
                  className="text-base sm:text-lg font-bold text-main leading-tight truncate"
                >
                  {modalTitle}
                </h2>
                <Badge variant={docType === 'outgoing' ? 'success' : docType === 'resource' ? 'info' : 'primary'}>
                  {document.code}
                </Badge>
              </div>
              <p className="text-xs text-secondary mt-0.5 truncate">
                {t('documentPreview.modalSubtitle')}
              </p>
            </div>
          </div>

          {/* Action buttons on header */}
          <div className="flex items-center gap-1.5 shrink-0">
            {totalDocs > 1 && (
              <div className="flex items-center bg-surface-hover rounded-xl p-0.5 border border-border-subtle">
                <button
                  type="button"
                  onClick={onPrev}
                  disabled={!hasPrev}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
                  title={t('documentPreview.prevDoc')}
                  aria-label={t('documentPreview.prevDoc')}
                >
                  <i className="fa-solid fa-chevron-left text-xs" />
                </button>
                <span className="text-xs font-semibold text-secondary px-1.5">
                  {currentIndex + 1}/{totalDocs}
                </span>
                <button
                  type="button"
                  onClick={onNext}
                  disabled={!hasNext}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
                  title={t('documentPreview.nextDoc')}
                  aria-label={t('documentPreview.nextDoc')}
                >
                  <i className="fa-solid fa-chevron-right text-xs" />
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={onClose}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-muted hover:text-main hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all cursor-pointer"
              title={t('documentPreview.close')}
              aria-label={t('documentPreview.close')}
            >
              <i className="fa-solid fa-xmark text-lg" />
            </button>
          </div>
        </div>

        {/* 2. Modal Body Content: THÔNG TIN CHI TIẾT */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-4 max-h-[calc(88vh-140px)]">
          {/* Banner Cảnh báo Trạng thái Hết hiệu lực / Đã thay thế */}
          {docMeta.validity === 'expired' && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
                <i className="fa-solid fa-triangle-exclamation text-base" />
              </div>
              <div className="text-sm">
                <div className="font-bold text-amber-800 dark:text-amber-300 uppercase tracking-wide text-xs">
                  {t('documentPreview.expiredWarningTitle')}
                </div>
                <div className="text-amber-700 dark:text-amber-400 mt-0.5">
                  {t('documentPreview.expiredWarningDesc')}{' '}
                  <span className="font-bold text-amber-900 dark:text-amber-200 underline decoration-amber-400">
                    {docMeta.replacedBy}
                  </span>.
                </div>
              </div>
            </div>
          )}

          {/* Khối TRÍCH YẾU NỘI DUNG */}
          <div>
            <div className="text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
              {t('documentPreview.summaryTitle')}
            </div>
            <div className="bg-surface-subtle border border-border-subtle rounded-2xl p-4 sm:p-5 text-main font-semibold text-base sm:text-lg leading-relaxed shadow-xs">
              {document.title}
            </div>
          </div>

          {/* Khối 2 Cột Thông Số Nghiệp Vụ */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Cột 1: Thông số đến / Thông số đi / Biểu mẫu */}
            <div className="border border-border-subtle rounded-2xl p-4 sm:p-5 bg-surface shadow-xs flex flex-col justify-between">
              <div className="text-xs font-bold text-primary tracking-wider uppercase flex items-center gap-2 pb-2.5 mb-3 border-b border-border-subtle">
                <i className="fa-solid fa-hashtag text-xs" />
                <span>
                  {docType === 'incoming'
                    ? t('documentPreview.incomingParamsTitle')
                    : docType === 'outgoing'
                    ? t('documentPreview.outgoingParamsTitle')
                    : t('documentPreview.resourceParamsTitle')}
                </span>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center text-secondary">
                  <span>
                    {docType === 'incoming'
                      ? t('documentPreview.incomingNumber')
                      : docType === 'outgoing'
                      ? t('documentPreview.outgoingNumber')
                      : t('documentPreview.resourceCodeLabel')}
                  </span>
                  <span className="font-bold text-main">{docMeta.arrivalNo}</span>
                </div>

                <div className="flex justify-between items-center text-secondary">
                  <span>{t('documentPreview.bookYear')}</span>
                  <span className="font-semibold text-main">{docMeta.year}</span>
                </div>

                <div className="flex justify-between items-center text-secondary">
                  <span>
                    {docType === 'incoming'
                      ? t('documentPreview.arrivalDate')
                      : t('documentPreview.issueDate')}
                  </span>
                  <span className="font-semibold text-main">{docMeta.arrivalDate}</span>
                </div>

                <div className="flex justify-between items-center text-secondary">
                  <span>{t('documentPreview.documentDate')}</span>
                  <span className="font-semibold text-main">{document.date}</span>
                </div>
              </div>
            </div>

            {/* Cột 2: Cơ quan ban hành & Hiệu lực */}
            <div className="border border-border-subtle rounded-2xl p-4 sm:p-5 bg-surface shadow-xs flex flex-col justify-between">
              <div className="text-xs font-bold text-primary tracking-wider uppercase flex items-center gap-2 pb-2.5 mb-3 border-b border-border-subtle">
                <i className="fa-solid fa-landmark text-xs" />
                <span>
                  {docType === 'resource'
                    ? t('documentPreview.managementUnit')
                    : t('documentPreview.authorityAndValidity')}
                </span>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center text-secondary">
                  <span>
                    {docType === 'outgoing'
                      ? t('documentPreview.draftingUnit')
                      : t('documentPreview.issuingAgency')}
                  </span>
                  <span
                    className="font-medium text-main text-right max-w-[210px] truncate"
                    title={docMeta.place}
                  >
                    {docMeta.place}
                  </span>
                </div>

                <div className="flex justify-between items-center text-secondary">
                  <span>{t('documentPreview.signerAndRole')}</span>
                  <span
                    className="font-medium text-main text-right max-w-[210px] truncate"
                    title={`${docMeta.signer} (${docMeta.signerRole})`}
                  >
                    {docMeta.signer} ({docMeta.signerRole})
                  </span>
                </div>

                <div className="flex justify-between items-center text-secondary">
                  <span>{t('documentPreview.validityStatus')}</span>
                  <Badge
                    variant={
                      docMeta.validity === 'valid'
                        ? 'success'
                        : docMeta.validity === 'expired'
                        ? 'warning'
                        : 'info'
                    }
                    className="font-semibold"
                  >
                    {docMeta.validityLabel}
                  </Badge>
                </div>

                {docMeta.replacedBy && (
                  <div className="flex justify-between items-center text-secondary">
                    <span>{t('documentPreview.replacedBy')}</span>
                    <span className="font-bold text-amber-600 dark:text-amber-400">
                      {docMeta.replacedBy}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Dòng Ghi chú (nếu có) */}
          {docMeta.note && (
            <div className="p-3.5 bg-surface-subtle border border-border-subtle rounded-xl text-sm flex items-start gap-2.5">
              <i className="fa-regular fa-note-sticky text-muted mt-0.5 shrink-0" />
              <div className="text-secondary">
                <span className="font-bold text-main">{t('documentPreview.notesLabel')} </span>
                <span>{docMeta.note}</span>
              </div>
            </div>
          )}

          {/* Khối 📎 TỆP ĐÍNH KÈM (N) */}
          <div>
            <div className="text-xs font-bold text-primary tracking-wider uppercase flex items-center gap-2 mb-2.5">
              <i className="fa-solid fa-paperclip text-xs" />
              <span>
                {t('documentPreview.attachmentsTitle')} ({docMeta.attachments.length})
              </span>
            </div>

            <div className={docMeta.attachments.length === 1 ? 'grid grid-cols-1' : 'grid grid-cols-1 sm:grid-cols-2 gap-3'}>
              {docMeta.attachments.map((att, idx) => {
                const isDoc = isDocFile(att);
                return (
                  <div
                    key={idx}
                    onClick={() => handleOpenFile(att)}
                    className="p-3.5 rounded-2xl border border-border-subtle bg-surface hover:bg-surface-subtle transition-all flex items-center justify-between gap-3 group shadow-xs cursor-pointer"
                    title={isDoc ? `Tải về tệp ${att.name}` : `Mở xem trước ${att.name} trong cửa sổ mới`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 text-xl border ${
                          att.type === 'excel' || att.name.endsWith('.xlsx')
                            ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                            : isDoc
                            ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                            : att.type === 'image' || att.name.match(/\.(jpg|jpeg|png|webp|gif)$/i)
                            ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                            : 'bg-red-500/10 text-red-500 border-red-500/20'
                        }`}
                      >
                        {att.type === 'excel' || att.name.endsWith('.xlsx') ? (
                          <i className="fa-solid fa-file-excel" />
                        ) : isDoc ? (
                          <i className="fa-solid fa-file-word" />
                        ) : att.type === 'image' || att.name.match(/\.(jpg|jpeg|png|webp|gif)$/i) ? (
                          <i className="fa-solid fa-file-image" />
                        ) : (
                          <i className="fa-solid fa-file-pdf" />
                        )}
                      </div>

                      <div className="min-w-0">
                        <div
                          className="text-sm font-bold text-main truncate group-hover:text-primary transition-colors flex items-center gap-1.5"
                          title={att.name}
                        >
                          <span className="truncate">{att.name}</span>
                          {!isDoc && (
                            <i className="fa-solid fa-arrow-up-right-from-square text-[11px] text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                          )}
                        </div>
                        <div className="text-xs text-muted mt-0.5">
                          {att.size || '1.8 MB'} • {att.date || document.date}
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenFile(att);
                      }}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 shrink-0 shadow-xs cursor-pointer ${
                        isDoc
                          ? 'bg-surface border-border-subtle text-main hover:bg-primary hover:text-white hover:border-primary'
                          : 'bg-primary-subtle border-primary/30 text-primary hover:bg-primary hover:text-white hover:border-primary'
                      }`}
                      title={isDoc ? `Tải về tệp ${att.name}` : `Mở xem trước ${att.name} trong tab mới`}
                    >
                      <i className={`text-xs ${isDoc ? 'fa-solid fa-download' : 'fa-solid fa-arrow-up-right-from-square'}`} />
                      <span>{isDoc ? t('documentPreview.downloadFile') : t('documentPreview.previewFile')}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 3. Footer Modal */}
        <div className="p-4 sm:px-6 bg-surface-subtle border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-secondary">
          <div className="truncate">
            <span>{t('documentPreview.createdBy')} </span>
            <span className="font-bold text-main">{docMeta.creator}</span>
            <span className="text-muted"> lúc {docMeta.createdAt}</span>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-4">
            <span className="text-muted hidden md:inline">
              {t('documentPreview.updatedAt')} {docMeta.updatedAt}
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownload}
                className="px-4 py-2 rounded-xl bg-surface hover:bg-surface-hover border border-border-subtle text-main font-semibold text-sm transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
                title={t('documentPreview.download')}
              >
                <i className="fa-solid fa-download text-xs" />
                <span>{t('documentPreview.download')}</span>
              </button>

              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-surface-hover hover:bg-border-subtle text-main font-bold text-sm transition-colors cursor-pointer"
              >
                {t('documentPreview.closeBtn')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return typeof window !== 'undefined' && window.document?.body
    ? createPortal(modalContent, window.document.body)
    : modalContent;
}
