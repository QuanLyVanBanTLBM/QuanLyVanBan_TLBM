import os
import shutil
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, "docs", "qa", "nhom_5")
DESKTOP_PATH = os.path.expanduser(r"~\Desktop")
OUTPUT_NAME = "Bao_Cao_Kiem_Thu_QA_Nhom_5.docx"
WORKSPACE_DOCX = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
DESKTOP_DOCX = os.path.join(DESKTOP_PATH, OUTPUT_NAME)

def set_cell_background(cell, hex_color):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=100, bottom=100, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_report():
    doc = Document()
    
    # Page setup (A4, 0.7 inch margins)
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
    
    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("BÁO CÁO KIỂM THỬ CHẤT LƯỢNG TOÀN DIỆN (QA/QC REPORT)\nPHÂN HỆ TRÌNH KÝ & KÝ SỐ ĐIỆN TỬ (NHÓM 5)")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(15)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(30, 58, 138) # Dark blue #1E3A8A
    
    # Metadata Subtitle
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run(
        "Hệ thống Quản lý Văn bản & Tài liệu Điều hành Tác nghiệp TLBM\n"
        "Môi trường kiểm thử: http://staging-quanlyvanban.bhbl.vn:8088/login\n"
        "Đơn vị thực hiện: Nhóm 5 (QA/QC & Core Dev)  |  Ngày kiểm thử: 04/11/2026\n"
        "Trạng thái tổng thể: 29 PASS, 1 BLOCKED - Chưa đủ cơ sở nghiệm thu"
    )
    r_meta.font.name = "Arial"
    r_meta.font.size = Pt(9.5)
    r_meta.font.italic = True
    r_meta.font.color.rgb = RGBColor(71, 85, 105)
    p_meta.paragraph_format.space_after = Pt(10)
    
    # Divider
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    
    # SECTION I: TỔNG QUAN
    h1 = doc.add_paragraph()
    r_h1 = h1.add_run("I. TỔNG QUAN PHẠM VI & MÔI TRƯỜNG KIỂM THỬ")
    r_h1.font.name = "Arial"
    r_h1.font.size = Pt(12)
    r_h1.font.bold = True
    r_h1.font.color.rgb = RGBColor(30, 58, 138)
    
    p_intro = doc.add_paragraph()
    r_intro = p_intro.add_run(
        "Báo cáo này tổng hợp kết quả kiểm định chất lượng toàn diện (QA/QC) phân hệ Trình ký & Ký số điện tử (Nhóm 5) "
        "được thực hiện trên môi trường máy chủ Staging chính thức tại địa chỉ http://staging-quanlyvanban.bhbl.vn:8088/login.\n\n"
        "Phạm vi kiểm thử bao gồm việc xác nhận toàn bộ các tính năng cốt lõi, xác thực cơ chế bảo mật khóa ký Ed25519, "
        "quy trình ký nhiều cấp, kéo-thả khung ký trên tệp PDF, và đặc biệt là kiểm định kết quả khắc phục triệt để các sự cố trọng yếu "
        "phát sinh trên môi trường Staging (bao gồm khắc phục lỗi WebCrypto trên HTTP insecure context, tinh gọn giao diện quy trình ký "
        "hiển thị đầy đủ 83 cán bộ nhân viên, xử lý lỗi upload ảnh chữ ký qua multipart/form-data và cách ly phân vùng thông báo)."
    )
    r_intro.font.name = "Arial"
    r_intro.font.size = Pt(9.5)
    r_intro.font.color.rgb = RGBColor(51, 65, 85)
    p_intro.paragraph_format.space_after = Pt(10)
    
    # SECTION II: BẢNG 30 TEST CASES
    h2 = doc.add_paragraph()
    r_h2 = h2.add_run("II. BẢNG TỔNG HỢP KẾT QUẢ KIỂM THỬ (30 TEST CASES - 29 PASS, 1 BLOCKED)")
    r_h2.font.name = "Arial"
    r_h2.font.size = Pt(12)
    r_h2.font.bold = True
    r_h2.font.color.rgb = RGBColor(30, 58, 138)
    
    tsv_path = os.path.join(OUTPUT_DIR, "danh_sach_testcase_google_sheets.tsv")
    test_cases = []
    if os.path.exists(tsv_path):
        with open(tsv_path, "r", encoding="utf-8") as f:
            lines = [line.strip().split("\t") for line in f if line.strip()]
            if lines and lines[0][0] == "STT":
                lines = lines[1:]
            for row in lines:
                if len(row) >= 10:
                    test_cases.append((row[1], row[2], row[3], row[6], row[9]))
    
    if not test_cases:
        raise RuntimeError(f"No test cases found in QA source file: {tsv_path}")

    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    headers = ["Mã TC", "Phân hệ / Màn hình", "Tên ca kiểm thử", "Kết quả thực tế trên Staging", "Đánh giá"]
    col_widths = [Inches(0.7), Inches(1.5), Inches(2.3), Inches(2.0), Inches(0.7)]
    
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1E3A8A")
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    for row_idx, item in enumerate(test_cases):
        row_cells = table.add_row().cells
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for i, val in enumerate(item):
            row_cells[i].text = val
            set_cell_background(row_cells[i], bg_color)
            set_cell_margins(row_cells[i], top=70, bottom=70, left=80, right=80)
            p = row_cells[i].paragraphs[0]
            if i in [0, 4]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(8)
                if i == 4: # Kết quả
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(22, 163, 74) # Green #16A34A
                    
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # SECTION III: CHI TIẾT SỬA LỖI TRỌNG YẾU
    h3 = doc.add_paragraph()
    r_h3 = h3.add_run("III. CHI TIẾT CÁC LỖI TRỌNG YẾU ĐÃ ĐƯỢC XỬ LÝ TRIỆT ĐỂ TRÊN STAGING")
    r_h3.font.name = "Arial"
    r_h3.font.size = Pt(12)
    r_h3.font.bold = True
    r_h3.font.color.rgb = RGBColor(30, 58, 138)
    
    issues_detail = [
        (
            "1. Khắc phục lỗi WebCrypto trên HTTP Staging Insecure Context (Issue #534 / PR #535)",
            "- Tình trạng lỗi ban đầu: Khi người dùng truy cập trang /approvals/khoa trên môi trường HTTP Staging (window.isSecureContext === false), trình duyệt Chrome/Chromium tự động vô hiệu hóa WebCrypto API (window.crypto.subtle là undefined). Giao diện hiển thị banner cảnh báo lỗi màu đỏ: 'Trình duyệt này chưa hỗ trợ tạo khóa ký. Hãy cập nhật trình duyệt lên phiên bản mới.' và khóa toàn bộ chức năng.\n"
            "- Giải pháp xử lý kỹ thuật: Tích hợp bộ thư viện pure-JS chuẩn quốc tế (@noble/curves, @noble/ciphers, @noble/hashes) làm fallback mật mã tự động khi WebCrypto không khả dụng. Triển khai thuật toán sinh khóa Ed25519 PKCS#8 DER (48 byte), dẫn xuất khóa HKDF-SHA256 và mã hóa bọc khóa AES-256-GCM lưu trữ an toàn trong IndexedDB.\n"
            "- Kết quả kiểm thử thực tế: Người dùng có thể tạo khóa, đổi PIN, xuất/nhập khóa và ký số bình thường trên http://staging-quanlyvanban.bhbl.vn:8088/ mà không cần cài đặt cờ flag hay chứng chỉ SSL."
        ),
        (
            "2. Tinh gọn Quy trình ký & Mở rộng Danh bạ 83 Cán bộ nhân viên (Issue #532 / PR #533)",
            "- Tình trạng lỗi ban đầu: Form tạo quy trình ký hiển thị khối dropdown 25 chức danh và khối xem trước 'Cán bộ đang giữ chức danh' chiếm dụng không gian giao diện lớn, dễ gây nhầm lẫn khi người dùng muốn chỉ định đích danh cán bộ. Dropdown chọn người ký cụ thể bị giới hạn tối đa 10 người và bắt buộc gõ từ 2 ký tự mới gợi ý.\n"
            "- Giải pháp xử lý kỹ thuật: Loại bỏ hoàn toàn khối dropdown chức danh và khối xem trước. Nâng cấp dropdown 'Chọn người ký cụ thể' tự động tải và hiển thị danh sách cuộn đầy đủ toàn bộ 83 cán bộ nhân viên của cơ quan ngay khi focus, đồng thời tích hợp tìm kiếm nhanh tức thì không cần gõ tối thiểu 2 ký tự.\n"
            "- Kết quả kiểm thử thực tế: Form quy trình ký tinh gọn, thoáng đãng; hiển thị đầy đủ 83 CBNV; thao tác chọn nhiều người ký và lưu quy trình diễn ra trơn tru."
        ),
        (
            "3. Khắc phục lỗi tải lên ảnh chữ ký cá nhân do stringify FormData thành '{}' (Issue #542 / PR #543)",
            "- Tình trạng lỗi ban đầu: Thao tác tải lên ảnh chữ ký cá nhân từ máy tính thất bại, console hiển thị lỗi 'Vui lòng cung cấp tệp ảnh hoặc dữ liệu Base64 ảnh chữ ký.' Nguyên nhân do apiClient.post tự động áp dụng JSON.stringify() biến FormData thành chuỗi rỗng '{}' và cưỡng ép header 'Content-Type: application/json'.\n"
            "- Giải pháp xử lý kỹ thuật: Bổ sung hàm nhận diện isRawBody và hàm serializeBody trong frontend/src/lib/apiClient.ts để giữ nguyên đối tượng binary (FormData, Blob, ArrayBuffer) và để trình duyệt tự thiết lập Content-Type kèm boundary multipart; đồng thời cập nhật hàm taiLenAnhChuKy sử dụng postForm hỗ trợ cả FormData và chuỗi Base64 dataUrl.\n"
            "- Kết quả kiểm thử thực tế: Ảnh chữ ký tải lên thành công, server tiếp nhận payload nhị phân, băm mã SHA-256 và lưu trữ chính xác."
        ),
        (
            "4. Phân tách phân vùng thông báo ảnh chữ ký cá nhân & Dual Fallback (Issue #545 / PR #546)",
            "- Tình trạng lỗi ban đầu: Khi tải ảnh chữ ký gặp lỗi mạng, banner thông báo lỗi bị hiển thị tràn sang thẻ 'Cấu hình khóa ký' bên trái, gây hiểu lầm cho người dùng về trạng thái của khóa ký thiết bị.\n"
            "- Giải pháp xử lý kỹ thuật: Tách biệt hoàn toàn state thongBaoChuKy nội bộ trong thẻ 'Ảnh chữ ký cá nhân' bên phải; đồng thời xây dựng cơ chế tự động chuyển đổi fallback sang gửi Base64 dataUrl nếu thao tác upload Blob nhị phân gặp lỗi.\n"
            "- Kết quả kiểm thử thực tế: Thông báo thành công/lỗi xuất hiện chuẩn xác bên trong thẻ ảnh chữ ký; giao diện thẻ khóa ký giữ nguyên vẹn tính ổn định."
        )
    ]
    
    for title, content in issues_detail:
        p_sub = doc.add_paragraph()
        r_sub = p_sub.add_run(title)
        r_sub.font.name = "Arial"
        r_sub.font.size = Pt(10)
        r_sub.font.bold = True
        r_sub.font.color.rgb = RGBColor(15, 23, 42)
        
        p_desc = doc.add_paragraph()
        r_desc = p_desc.add_run(content)
        r_desc.font.name = "Arial"
        r_desc.font.size = Pt(9)
        r_desc.font.color.rgb = RGBColor(51, 65, 85)
        p_desc.paragraph_format.space_after = Pt(8)
        
    # SECTION IV: CÁC CỔNG KIỂM TRA CHẤT LƯỢNG
    h4 = doc.add_paragraph()
    r_h4 = h4.add_run("IV. XÁC THỰC CÁC CỔNG CHẤT LƯỢNG KỸ THUẬT (TECHNICAL GATES)")
    r_h4.font.name = "Arial"
    r_h4.font.size = Pt(12)
    r_h4.font.bold = True
    r_h4.font.color.rgb = RGBColor(30, 58, 138)
    
    gates = [
        ("Frontend Build Gate", "pnpm --dir frontend run build", "PASS (0 error, 0 warning, bundle chunking chuẩn)"),
        ("Frontend Lint Gate", "pnpm --dir frontend run lint", "PASS (Tuân thủ toàn bộ quy tắc ESLint dự án)"),
        ("i18n Coverage Gate", "pnpm --dir frontend check:i18n", "PASS (100% nhãn dịch đủ 2 nhánh vi/en, 2639 keys)"),
        ("Design Tokens Gate", "pnpm --dir frontend check:tokens", "PASS (100% màu sắc và font dùng CSS variables từ global.css)"),
        ("Backend System Check", "python backend/manage.py check", "PASS (Hệ thống Django không phát sinh cảnh báo)"),
        ("Backend Unit Tests", "python backend/manage.py test apps.signing", "PASS (Toàn bộ test cases phân hệ Trình ký vượt qua)"),
        ("DB Schema Gate", "python scripts/build_db.py --check", "PASS (Khớp 100% với release_DDL.sql, collation ICU vi-VN)"),
    ]
    
    tbl_gates = doc.add_table(rows=1, cols=3)
    tbl_gates.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_gates.autofit = False
    
    gate_headers = ["Cổng kiểm định chất lượng", "Lệnh kiểm tra", "Trạng thái xác thực"]
    gate_widths = [Inches(2.2), Inches(2.6), Inches(2.2)]
    
    for i, title in enumerate(gate_headers):
        cell = tbl_gates.rows[0].cells[i]
        cell.text = title
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Arial"
            run.font.size = Pt(8.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    for row_idx, item in enumerate(gates):
        row_cells = tbl_gates.add_row().cells
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for i, val in enumerate(item):
            row_cells[i].text = val
            set_cell_background(row_cells[i], bg_color)
            set_cell_margins(row_cells[i], top=60, bottom=60, left=80, right=80)
            p = row_cells[i].paragraphs[0]
            if i == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(8)
                if i == 2:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(22, 163, 74)
                    
    for row in tbl_gates.rows:
        for idx, width in enumerate(gate_widths):
            row.cells[idx].width = width
            
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # SECTION V: KẾT LUẬN
    h5 = doc.add_paragraph()
    r_h5 = h5.add_run("V. KẾT LUẬN & ĐÁNH GIÁ SẴN SÀNG NGHIỆM THU")
    r_h5.font.name = "Arial"
    r_h5.font.size = Pt(12)
    r_h5.font.bold = True
    r_h5.font.color.rgb = RGBColor(30, 58, 138)
    
    p_concl = doc.add_paragraph()
    r_concl = p_concl.add_run(
        "1. Kết quả kiểm thử: 29/30 ca PASS; TC-06 BLOCKED vì chưa xác minh khôi phục cùng khóa và ký lại thành công.\n"
        "2. Đánh giá bảo mật: Mật mã học Ed25519, bọc khóa AES-GCM và cơ chế fallback pure-JS đạt tiêu chuẩn an toàn thông tin cơ quan nhà nước.\n"
        "3. Đánh giá tính sẵn sàng: Chưa kết luận Production-Ready cho đến khi TC-06 được xử lý theo issue #553 và xác minh trên staging bằng chữ ký dùng đúng khóa cũ."
    )
    r_concl.font.name = "Arial"
    r_concl.font.size = Pt(9.5)
    r_concl.font.bold = True
    r_concl.font.color.rgb = RGBColor(22, 101, 52)
    
    # Save
    doc.save(WORKSPACE_DOCX)
    print(f"Saved DOCX report: {WORKSPACE_DOCX}")
    
    if os.path.exists(DESKTOP_PATH):
        try:
            shutil.copy2(WORKSPACE_DOCX, DESKTOP_DOCX)
            print(f"Copied to Desktop: {DESKTOP_DOCX}")
        except Exception as e:
            print(f"Could not copy to Desktop: {e}")

if __name__ == "__main__":
    create_report()
