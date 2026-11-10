import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    """Set background color of a table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner margins for a table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    """Set subtle borders for a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_callout(doc, text, title="LƯU Ý QUAN TRỌNG", border_color="1E3A8A", bg_color="F0F4F8"):
    """Create a beautiful callout box with a colored left border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    r_title = p.add_run(f"📌 {title}: ")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(10.5)
    r_title.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    
    r_text = p.add_run(text)
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(10.5)
    r_text.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def build_report():
    doc = Document()
    
    # Page setup - A4 with standard margins
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
    
    # Color palette
    COLOR_PRIMARY = RGBColor(0x1E, 0x3A, 0x8A)     # Deep Navy
    COLOR_SECONDARY = RGBColor(0x02, 0x84, 0xC7)   # Cerulean Blue
    COLOR_DARK = RGBColor(0x0F, 0x17, 0x2A)        # Slate 900
    COLOR_MUTED = RGBColor(0x47, 0x55, 0x69)       # Slate 600
    
    # -------------------------------------------------------------
    # HEADER / BANNER TITLE
    # -------------------------------------------------------------
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_inst.add_run("TRƯỜNG CAO ĐẲNG CÔNG NGHỆ THÔNG TIN TP.HCM (ITC)\nKHOA CÔNG NGHỆ THÔNG TIN — LỚP CD25CT_CLC")
    r_inst.font.name = "Calibri"
    r_inst.font.size = Pt(10)
    r_inst.font.bold = True
    r_inst.font.color.rgb = COLOR_MUTED
    p_inst.paragraph_format.space_after = Pt(8)
    
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("─────────── ★ ───────────")
    r_line.font.color.rgb = COLOR_MUTED
    p_line.paragraph_format.space_after = Pt(16)
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("BÁO CÁO ĐẶC TẢ CHI TIẾT PHÂN HỆ AI CHATBOX\n& TRỢ LÝ RAG THÔNG MINH")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY
    p_title.paragraph_format.space_after = Pt(6)
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU (TLBM) — PHÂN HỆ NHÓM 8")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(13)
    r_sub.font.bold = True
    r_sub.font.color.rgb = COLOR_SECONDARY
    p_sub.paragraph_format.space_after = Pt(20)
    
    # Metadata info table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    
    meta_data = [
        ("Phân hệ phụ trách:", "Module 8 — Trợ lý AI Chatbox & RAG (Branch: 8_ai_chatbox)"),
        ("Giảng viên hướng dẫn:", "NCS.ThS. Trần Phương Duy"),
        ("Thành viên & Vai trò:", "Trần Vũ Giang Anh (Trưởng nhóm), Huỳnh Vương Thanh Nhã & Thành viên nhóm 8"),
        ("Mục tiêu tài liệu:", "Đặc tả toàn diện Chức năng, Nghiệp vụ, Đặc quyền RBAC, Rào cản An toàn & Hạn chế của AI")
    ]
    
    for i, (k, v) in enumerate(meta_data):
        row = meta_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "F8FAFC")
        set_cell_background(c1, "F8FAFC")
        set_cell_margins(c0, 60, 60, 100, 100)
        set_cell_margins(c1, 60, 60, 100, 100)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(k)
        r0.font.name = "Calibri"
        r0.font.size = Pt(10)
        r0.font.bold = True
        r0.font.color.rgb = COLOR_PRIMARY
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(v)
        r1.font.name = "Calibri"
        r1.font.size = Pt(10)
        r1.font.color.rgb = COLOR_DARK
        
    set_table_borders(meta_table, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(14)
    
    # Helper to create styled headings
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.bold = True
        r.font.color.rgb = COLOR_PRIMARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(12.5)
        r.font.bold = True
        r.font.color.rgb = COLOR_SECONDARY
        return p

    def add_body(text, bold_prefix=None, space_after=5):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = "Calibri"
            r_bold.font.size = Pt(11)
            r_bold.font.bold = True
            r_bold.font.color.rgb = COLOR_DARK
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(11)
        r.font.color.rgb = COLOR_DARK
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = "Calibri"
            r_bold.font.size = Pt(11)
            r_bold.font.bold = True
            r_bold.font.color.rgb = COLOR_DARK
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(11)
        r.font.color.rgb = COLOR_DARK
        return p

    # -------------------------------------------------------------
    # 1. TỔNG QUAN HỆ THỐNG & MODULE AI CHATBOX
    # -------------------------------------------------------------
    add_h1("1. TỔNG QUAN PHÂN HỆ AI CHATBOX & TRỢ LÝ RAG")
    
    add_body(
        "Hệ thống Quản lý Văn bản và Tài liệu (TLBM) là nền tảng quản trị công việc và luồng hành chính số nội bộ "
        "dành cho tổ chức, doanh nghiệp và trường học. Trong khuôn khổ kiến trúc tổng thể, Module 8 (Trợ lý AI Chatbox & RAG) "
        "đóng vai trò là trung tâm tri thức hỗ trợ cán bộ nhân viên tra cứu văn bản, quy chế nội bộ, hướng dẫn nghiệp vụ và "
        "hỏi đáp ngữ cảnh tự động."
    )
    
    add_body(
        "Khác với các hệ sinh thái chatbot thông thường trả lời tự do dựa trên tri thức đại chúng của Internet, "
        "Trợ lý AI TLBM được thiết kế tuân thủ nghiêm ngặt nguyên tắc hành chính: Bảo mật phân quyền, chuẩn hóa nguồn dẫn chứng "
        "và tuyệt đối không bịa đặt thông tin (Zero-Hallucination)."
    )

    add_callout(
        doc,
        "Trợ lý AI TLBM chỉ đóng vai trò là Trợ lý Tra cứu & Giải đáp (Read-only Knowledge Assistant), "
        "tuyệt đối không phải là Execution Agent tự động thay mặt con người ký số, duyệt lệnh hay chỉnh sửa CSDL.",
        title="ĐỊNH VỊ VAI TRÒ"
    )

    # -------------------------------------------------------------
    # 2. KIẾN TRÚC KỸ THUẬT & 3 NGUỒN TRI THỨC CỦA AI
    # -------------------------------------------------------------
    add_h1("2. KIẾN TRÚC KỸ THUẬT & CÁC NGUỒN TRI THỨC CỦA AI")
    
    add_body(
        "Hệ thống vận hành theo kiến trúc RAG (Retrieval-Augmented Generation) thông qua framework LlamaIndex kết hợp với "
        "ChromaDB Vector Store và Google Gemini Cloud AI / OpenAI GPT. AI tổng hợp dữ liệu từ 3 nguồn tri thức chính:"
    )
    
    add_bullet(
        "Truy vấn trực tiếp qua tài khoản chỉ đọc an toàn (qlvb_readonly) trên các Database View: ai_vanbanden, ai_vanbandi, ai_tailieu. "
        "Các view này áp dụng cơ chế security_barrier, tự động lọc theo danh tính nhân viên (qlvb.employee_id) và loại trừ 100% văn bản thuộc diện HẠN CHẾ hoặc MẬT.",
        "1. Dữ liệu Văn bản & Hồ sơ CSDL PostgreSQL: "
    )
    
    add_bullet(
        "Bao gồm các văn bản quy định, hướng dẫn nghiệp vụ, biểu mẫu dùng chung được tải lên và lập chỉ mục bằng kỹ thuật "
        "Parent-Child Chunking (Parent chunk 1500 ký tự, Child chunk 300 ký tự). Nhúng vector qua Gemini Embedding/OpenAI text-embedding.",
        "2. Kho tài liệu tri thức nội bộ (Local ChromaDB): "
    )
    
    add_bullet(
        "Tập hợp các thẻ kiến thức chuẩn hóa (business_knowledge.py) tóm tắt quy trình vận hành và ý định thiết kế của 7 phân hệ "
        "(Dashboard, Văn bản đến/đi, Hồ sơ, Biểu mẫu, Trình ký, Giao việc, Quản trị hệ thống & phòng họp).",
        "3. Thẻ đặc tả nghiệp vụ phân hệ 1–7: "
    )

    # Bảng kiến trúc công nghệ
    arch_table = doc.add_table(rows=6, cols=2)
    arch_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    arch_table.autofit = False
    
    headers = [("Thành phần", "Công nghệ / Thư viện sử dụng")]
    rows_data = [
        ("Frontend Client", "React 19, TypeScript, Vite, Vanilla CSS Tokens, Axios Client"),
        ("Backend Web Server", "Python 3.11+, Django 5 / 6, Django REST Framework, SimpleJWT"),
        ("AI & RAG Engine", "LlamaIndex, ChromaDB, Gemini REST Client (gemini-3.8-flash), OpenAI API"),
        ("Vision & OCR Engine", "Gemini Multimodal Vision, RapidOCR (onnxruntime), pdfplumber, pdf2image"),
        ("Cơ sở dữ liệu", "PostgreSQL (với Security Barrier Views ai_* & role qlvb_readonly)"),
    ]
    
    # Header row
    hdr_cells = arch_table.rows[0].cells
    hdr_cells[0].width = Inches(2.2)
    hdr_cells[1].width = Inches(4.3)
    set_cell_background(hdr_cells[0], "1E3A8A")
    set_cell_background(hdr_cells[1], "1E3A8A")
    set_cell_margins(hdr_cells[0], 80, 80, 100, 100)
    set_cell_margins(hdr_cells[1], 80, 80, 100, 100)
    
    p = hdr_cells[0].paragraphs[0]
    r = p.add_run("Thành phần")
    r.font.name, r.font.bold, r.font.color.rgb = "Calibri", True, RGBColor(0xFF, 0xFF, 0xFF)
    p = hdr_cells[1].paragraphs[0]
    r = p.add_run("Công nghệ / Thư viện sử dụng")
    r.font.name, r.font.bold, r.font.color.rgb = "Calibri", True, RGBColor(0xFF, 0xFF, 0xFF)
    
    for idx, (c1, c2) in enumerate(rows_data, start=1):
        row = arch_table.rows[idx]
        cell1, cell2 = row.cells[0], row.cells[1]
        cell1.width = Inches(2.2)
        cell2.width = Inches(4.3)
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        set_cell_background(cell1, bg)
        set_cell_background(cell2, bg)
        set_cell_margins(cell1, 60, 60, 100, 100)
        set_cell_margins(cell2, 60, 60, 100, 100)
        
        p1 = cell1.paragraphs[0]
        r1 = p1.add_run(c1)
        r1.font.name, r1.font.bold, r1.font.size = "Calibri", True, Pt(10)
        r1.font.color.rgb = COLOR_PRIMARY
        
        p2 = cell2.paragraphs[0]
        r2 = p2.add_run(c2)
        r2.font.name, r2.font.size = "Calibri", Pt(10)
        r2.font.color.rgb = COLOR_DARK
        
    set_table_borders(arch_table, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # -------------------------------------------------------------
    # 3. GIAO DIỆN & TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX)
    # -------------------------------------------------------------
    add_h1("3. GIAO DIỆN & TRẢI NGHIỆM NGƯỜI DÙNG (UI/UX)")
    
    add_h2("3.1. Chatbox Nổi Đa Nhiệm (FloatingAIBox.tsx)")
    add_body(
        "Được tích hợp sẵn vào App Shell chính của hệ thống, hiển thị cố định ở góc dưới bên phải màn hình mọi trang làm việc:"
    )
    add_bullet("Nút robot phát sáng với hiệu ứng sóng âm (radar pulse), trạng thái trực tuyến (online badge).", "Nút mở nhanh: ")
    add_bullet("Cửa sổ hội thoại nhỏ gọn nổi trên giao diện, hỗ trợ thu nhỏ thành thanh tiêu đề hoặc mở toàn diện.", "Khung Chat Mini: ")
    add_bullet("Cung cấp sẵn 4 nút gợi ý nhanh về: Tiếp nhận văn bản đến, Quy chế văn bản Mật, Sơ đồ trình ký số, Phân quyền cán bộ.", "Gợi ý nhanh (Quick Replies): ")
    add_bullet("Dễ dàng điều hướng từ câu trả lời của AI sang các trang chức năng (Dashboard, Quản lý văn bản, Cài đặt).", "Liên kết điều hướng: ")

    add_h2("3.2. Trang Trợ Lý AI Chuyên Biệt (AiAssistantPage.tsx)")
    add_body(
        "Trang làm việc chuyên sâu với đầy đủ tính năng cao cấp phục vụ cán bộ tra cứu chuyên nghiệp:"
    )
    add_bullet("Lưu trữ lịch sử chat nhiều phiên, tự động nhóm theo Hôm nay, Hôm qua, 7 ngày trước trong LocalStorage.", "Quản lý phiên hội thoại: ")
    add_bullet("4 card gợi ý chuẩn nhận diện thương hiệu TLBM giúp cán bộ bắt đầu tác vụ tra cứu chỉ với 1 cú click chuột.", "Prompt Templates: ")
    add_bullet("Cho phép cán bộ đặt câu hỏi bằng giọng nói tiếng Việt thông qua chuẩn Web Speech API.", "Nhập liệu bằng giọng nói: ")
    add_bullet("Hiển thị chi tiết tên file, số trang, chunk ID và độ tương đồng. Bấm vào nguồn sẽ mở ngay cửa sổ xem trước.", "Trích dẫn nguồn (Citations): ")
    add_bullet("Hỗ trợ xem trước PDF với bộ dựng Canvas chuyên biệt, xem trước tệp DOCX (phân chia trang tự động) và tệp TXT thuần.", "Xem trước tài liệu (Preview Modal): ")
    add_bullet("Dành riêng cho Quản trị viên (Admin) để tải lên tài liệu mới, xóa tài liệu, xóa Vector DB và yêu cầu AI phân loại lại.", "Quản lý kho tri thức: ")

    # -------------------------------------------------------------
    # 4. CHỨC NĂNG & NGHIỆP VỤ AI CÓ THỂ THỰC HIỆN
    # -------------------------------------------------------------
    add_h1("4. CHI TIẾT CHỨC NĂNG & NGHIỆP VỤ AI CÓ THỂ THỰC HIỆN")
    
    add_h2("4.1. Tra cứu & Giải đáp Dữ liệu Văn bản Hành chính")
    add_bullet(
        "Tìm kiếm theo Số hiệu văn bản, Số thứ tự trong sổ, Năm tiếp nhận, Ngày đến, Trích yếu nội dung, Nơi ban hành, Ngày văn bản, Người ký, Chức vụ người ký, Trạng thái hiệu lực và Ngày hết hiệu lực.",
        "• Văn bản đến (ai_vanbanden): "
    )
    add_bullet(
        "Tìm kiếm theo Số hiệu văn bản đi, Ngày ban hành, Trích yếu, Đơn vị/Nơi ban hành, Người ký, Chức vụ và tình trạng hiệu lực.",
        "• Văn bản đi (ai_vanbandi): "
    )
    add_bullet(
        "Tra cứu theo Ký hiệu tài liệu, Tiêu đề, Ngày đăng, Nơi ban hành, Ghi chú và thời hạn hiệu lực.",
        "• Tài liệu & Biểu mẫu (ai_tailieu): "
    )

    add_h2("4.2. Tư vấn & Giải đáp Quy trình Nghiệp vụ (Phân hệ 1–7)")
    add_body(
        "AI được nạp sẵn quy chuẩn vận hành của toàn bộ hệ thống để hỗ trợ giải đáp thắc mắc quy trình:"
    )
    add_bullet("Giải thích ý nghĩa các khối thống kê (Văn bản đến/đi, Chờ ký, Công việc quá hạn, Lịch họp hôm nay, Sinh nhật).", "Nhánh 1 (Dashboard): ")
    add_bullet("Quy trình 3 bước tiếp nhận văn bản đến (Vào sổ > Quét scan số hóa > Trình bút phê); Quy trình soạn thảo và cấp số văn bản đi.", "Nhánh 2 (Văn bản): ")
    add_bullet("Quy định lập hồ sơ công việc, thời hạn bảo quản tài liệu, nộp lưu trữ lịch sử.", "Nhánh 3 (Hồ sơ): ")
    add_bullet("Hướng dẫn tìm kiếm và tải các biểu mẫu chuẩn DOCX, XLSX, PDF theo phòng ban.", "Nhánh 4 (Biểu mẫu): ")
    add_bullet("Sơ đồ luồng trình ký số điện tử đa cấp, trạng thái luồng (Dự thảo, Đang trình ký, Đã ký, Từ chối, Thu hồi).", "Nhánh 5 (Trình ký): ")
    add_bullet("Quy định giao việc từ văn bản, vai trò phân công (Chủ trì, Chỉ đạo, Phối hợp), cập nhật hạn chót và minh chứng kết quả.", "Nhánh 6 (Công việc): ")
    add_bullet("Quy tắc đặt phòng họp chống trùng lịch thiết bị, cơ cấu tổ chức 2 cấp và ma trận quyền vai trò RBAC.", "Nhánh 7 (Quản trị & Lịch): ")

    add_h2("4.3. Đọc hiểu & Xử lý Tệp Đa phương thức (Multimodal Vision OCR)")
    add_body(
        "AI sở hữu khả năng xử lý tài liệu vượt trội thông qua pipeline trích xuất chuyên sâu:"
    )
    add_bullet("Đọc trọn vẹn văn bản in, văn bản đánh máy và chữ viết tay trong các bản scan hành chính.", "Đọc chữ viết tay & Scan: ")
    add_bullet("Tự động chuyển đổi công thức toán, lý, hóa phức tạp sang định dạng LaTeX chuẩn: $inline$ và $$display$$.", "Bóc tách công thức LaTeX: ")
    add_bullet("Giữ nguyên cấu trúc dòng/cột của các bảng biểu số liệu trong văn bản hành chính.", "Bảo toàn bảng biểu Markdown: ")
    add_bullet("Mô tả khách quan nội dung biểu đồ, sơ đồ luồng quy trình để phục vụ tìm kiếm ngữ nghĩa.", "Hiểu sơ đồ & Biểu đồ: ")
    add_bullet("Tự động đọc nội dung và phân loại tài liệu vào các lĩnh vực học thuật/chuyên môn (Luật, Kinh tế, Tin học, Y học...).", "Tự động phân loại danh mục: ")

    # -------------------------------------------------------------
    # 5. MA TRẬN PHÂN QUYỀN & ĐẶC QUYỀN (RBAC & PRIVILEGES)
    # -------------------------------------------------------------
    add_h1("5. MA TRẬN PHÂN QUYỀN & ĐẶC QUYỀN CỦA AI")
    
    add_body(
        "Hệ thống phân chia ranh giới an ninh thành 3 cấp độ: Quyền truy cập Chatbot, Quyền xem dữ liệu trong CSDL, và Quyền quản trị kho tri thức AI."
    )

    # Bảng phân quyền chi tiết
    rbac_table = doc.add_table(rows=7, cols=4)
    rbac_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rbac_table.autofit = False
    
    rbac_headers = ["Nhóm Người Dùng", "Quyền Chat AI", "Phạm Vi Dữ Liệu Được Hỏi", "Quyền Quản Trị AI"]
    col_widths = [Inches(1.8), Inches(1.2), Inches(2.2), Inches(1.3)]
    
    hdr_cells = rbac_table.rows[0].cells
    for i, title in enumerate(rbac_headers):
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], "1E3A8A")
        set_cell_margins(hdr_cells[i], 80, 80, 80, 80)
        p = hdr_cells[i].paragraphs[0]
        r = p.add_run(title)
        r.font.name, r.font.bold, r.font.size, r.font.color.rgb = "Calibri", True, Pt(9.5), RGBColor(0xFF, 0xFF, 0xFF)
        
    rbac_rows = [
        ("ADMIN (Quản trị hệ thống)", "use_aiassistant (Có)", "Toàn bộ văn bản đến, đi, tài liệu nội bộ", "Toàn quyền (Tải, Xóa, Cài đặt)"),
        ("BGD (Ban Giám đốc)", "use_aiassistant (Có)", "Văn bản đến, đi, tài liệu toàn cơ quan", "Không có quyền quản trị"),
        ("TP (Trưởng phòng)", "use_aiassistant (Có)", "Văn bản đến, đi, tài liệu thuộc phòng ban", "Không có quyền quản trị"),
        ("CV (Chuyên viên)", "use_aiassistant (Có)", "Văn bản phân phối, tài liệu phòng ban", "Không có quyền quản trị"),
        ("VT (Văn thư)", "use_aiassistant (Có)", "Văn bản đến, văn bản đi, tài liệu biểu mẫu", "Không có quyền quản trị"),
        ("Người dùng chưa cấp quyền", "Không có quyền", "Bị chặn ngay tại API (HTTP 403 Forbidden)", "Không có quyền"),
    ]
    
    for idx, row_data in enumerate(rbac_rows, start=1):
        row = rbac_table.rows[idx]
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = col_widths[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, 60, 60, 80, 80)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name, r.font.size = "Calibri", Pt(9.5)
            if c_idx == 0:
                r.font.bold = True
                r.font.color.rgb = COLOR_PRIMARY
            else:
                r.font.color.rgb = COLOR_DARK
                
    set_table_borders(rbac_table, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    add_h2("5.1. Cơ Chế Lọc Quyền Ở Tầng CSDL (Data ACL)")
    add_body(
        "Mã nguồn backend (sql_document_source.py) kiểm tra nghiêm ngặt: Quyền sử dụng chatbot (use_aiassistant) không tự động "
        "cho phép đọc mọi dữ liệu. Khi thực hiện câu hỏi, hệ thống kiểm tra chéo:"
    )
    add_bullet("Người dùng bắt buộc phải có thêm quyền view_vanbanden thì AI mới truy vấn bảng ai_vanbanden.", "Văn bản đến: ")
    add_bullet("Người dùng bắt buộc phải có thêm quyền view_vanbandi thì AI mới truy vấn bảng ai_vanbandi.", "Văn bản đi: ")
    add_bullet("Người dùng phải có quyền view_tailieu và có mã nhân viên hợp lệ. CSDL kích hoạt lệnh: "
               "SET qlvb.employee_id = '<id>' để view ai_tailieu tự động lọc đúng tài liệu thuộc quyền xem.", "Tài liệu nội bộ: ")

    add_h2("5.2. Đặc Quyền Riêng Biệt của Quản Trị Viên (Superuser)")
    add_body(
        "Chỉ có tài khoản Quản trị viên (is_superuser = True) mới có thể gọi các API cấu hình và quản trị kho tri thức:"
    )
    add_bullet("POST /api/upload và POST /api/upload/async (kèm theo dõi tiến trình qua job_id).", "Tải lên tài liệu mới: ")
    add_bullet("DELETE /api/documents/<filename> hoặc xóa trắng toàn bộ ChromaDB qua DELETE /api/documents.", "Xóa tài liệu tri thức: ")
    add_bullet("POST /api/reclassify/<filename> để kích hoạt LLM đọc lại và phân loại lại chủ đề.", "Phân loại lại danh mục: ")
    add_bullet("GET /api/documents/<filename>/preview và /file để xem nội dung raw hoặc tải tệp gốc.", "Xem trước & Tải tệp: ")
    add_bullet("GET / POST /api/settings/ai: Thay đổi nhà cung cấp (Gemini / OpenAI), cập nhật API Key, đổi model LLM và Embeddings.", "Cấu hình tham số AI: ")

    # -------------------------------------------------------------
    # 6. HẠN CHẾ, RÀO CẢN AN TOÀN & NHỮNG ĐIỀU AI KHÔNG THỂ LÀM
    # -------------------------------------------------------------
    add_h1("6. HẠN CHẾ, RÀO CẢN AN TOÀN & ĐIỀU AI KHÔNG THỂ LÀM")
    
    add_body(
        "Để đảm bảo an toàn tối đa cho hệ thống hành chính công, Module 8 thiết lập các chốt chặn an toàn bắt buộc:"
    )

    add_h2("6.1. Nguyên Tắc 'Zero-Hallucination' (Không Suy Diễn, Không Bịa Đặt)")
    add_body(
        "Trong System Prompt của AI, nguyên tắc Căn cứ tuyệt đối được áp dụng cứng:"
    )
    add_bullet("AI chỉ được phép trả lời dựa trên các sự thật, số liệu, số hiệu văn bản có trong [TÀI LIỆU CUNG CẤP].", "Căn cứ tuyệt đối: ")
    add_bullet("Tuyệt đối không dùng kiến thức bên ngoài, không suy luận chủ quan để trả lời thông tin còn thiếu.", "Cấm phỏng đoán: ")
    add_bullet("Nếu câu hỏi nằm ngoài tài liệu, AI bắt buộc phải từ chối đúng theo mẫu: "
               "\"Xin lỗi, thông tin bạn hỏi không có trong tài liệu được cung cấp nên tôi không thể trả lời.\"", "Mẫu từ chối bắt buộc: ")

    add_h2("6.2. Cô Lập CSDL Chỉ Đọc (Read-Only Database Isolation)")
    add_body(
        "Kết nối CSDL của AI được bảo vệ nghiêm ngặt ở cấp độ hệ quản trị cơ sở dữ liệu PostgreSQL:"
    )
    add_bullet("AI chỉ kết nối qua user qlvb_readonly với cờ transaction_read_only = 'on'.", "User chỉ đọc riêng biệt: ")
    add_bullet("Hàm kiểm tra nội bộ _assert_readonly_connection sẽ chặn đứng nếu user có quyền ghi hoặc có quyền superuser.", "Chặn quyền siêu người dùng: ")
    add_bullet("User qlvb_readonly bị thu hồi (REVOKE) toàn bộ quyền đọc trên các bảng gốc, chỉ được SELECT qua các view ai_*.", "Cấm đọc bảng gốc: ")
    add_bullet("AI hoàn toàn KHÔNG THỂ thực hiện bất kỳ lệnh ghi/sửa/xóa (INSERT, UPDATE, DELETE) nào lên dữ liệu cơ quan.", "Bất khả xâm phạm CSDL: ")

    add_h2("6.3. Loại Trừ Tuyệt Đối Văn Bản Mật & Tệp Đính Kèm Nhạy Cảm")
    add_bullet(
        "Tại định nghĩa của các view ai_vanbanden và ai_vanbandi, mệnh đề lọc cứng: WHERE pham_vi = 'NOI_BO' AND hien_thi IS TRUE. "
        "Do đó, 100% các văn bản thuộc phạm vi HẠN CHẾ (HAN_CHE) hoặc VĂN BẢN MẬT bị loại bỏ hoàn toàn khỏi tầm nhìn của AI.",
        "Loại trừ văn bản MẬT: "
    )
    add_bullet(
        "Các cột chứa tệp đính kèm gốc (file_dinh_kem), mật khẩu người dùng, mã PIN ký số, khóa riêng tư (Private Key/Token PKI) "
        "tuyệt đối không bao giờ được cấp quyền truy cập cho AI.",
        "Không cấp tệp đính kèm nhạy cảm: "
    )

    add_h2("6.4. Hạn Chế Tác Vụ: Chỉ Là Trợ Lý Tra Cứu (Không Phải Execution Agent)")
    add_bullet("AI KHÔNG THỂ tự động bấm ký số hay duyệt văn bản thay lãnh đạo.", "Không thể ký số: ")
    add_bullet("AI KHÔNG THỂ tự động sinh số hiệu văn bản đi hay tự động ban hành văn bản ra bên ngoài.", "Không thể ban hành văn bản: ")
    add_bullet("AI KHÔNG THỂ tự ý tạo phòng họp, thay đổi trạng thái công việc hay sửa đổi hồ sơ cán bộ.", "Không thể thay đổi dữ liệu: ")
    add_bullet("Nội dung trong business_knowledge.py chỉ là mô tả nghiệp vụ lý thuyết, AI không thể tự khẳng định số liệu thực tế nếu CSDL không có.", "Không phản ánh trạng thái live: ")

    add_h2("6.5. Bộ Lọc Ngôn Từ & Phòng Chống Tấn Công (Anti-Injection & Guardrails)")
    add_bullet("Hàm is_inappropriate_message tự động phát hiện và chặn các câu hỏi chứa từ ngữ khiếm nhã, chửi bới.", "Lọc từ ngữ thô tục: ")
    add_bullet("Câu hỏi người dùng bị giới hạn tối đa 4.000 ký tự; tệp tải lên tối đa 50 MB.", "Giới hạn độ dài: ")
    add_bullet("Lịch sử hội thoại chỉ duy trì tối đa 4–8 lượt trao đổi gần nhất (CHAT_HISTORY_MAX_TURNS) và 800 ký tự (CHAT_HISTORY_MAX_CHARS) để tránh tràn bộ nhớ token.", "Cửa sổ ngữ cảnh giới hạn: ")
    add_bullet("Prompt được bảo vệ: Văn bản người dùng nhập vào hoặc nội dung tài liệu trích xuất chỉ là dữ liệu tham khảo, không có quyền thay đổi luật an toàn của AI.", "Chống Prompt Injection: ")

    # -------------------------------------------------------------
    # 7. KẾT LUẬN & ĐÁNH GIÁ TỔNG QUAN
    # -------------------------------------------------------------
    add_h1("7. KẾT LUẬN & ĐÁNH GIÁ TỔNG QUAN")
    
    add_body(
        "Module 8 (Trợ lý AI Chatbox & RAG) trong hệ thống TLBM đã hoàn thành đầy đủ các tiêu chuẩn nghiệp vụ "
        "đặt ra theo đề bài đồ án môn học ITC và đáp ứng các tiêu chuẩn bảo mật của một phần mềm quản trị văn bản chuyên nghiệp:"
    )
    
    add_bullet("Kiến trúc RAG hiện đại kết hợp CSDL quan hệ PostgreSQL và Vector Database ChromaDB.", "✓ Về công nghệ: ")
    add_bullet("Đạt chuẩn bảo mật nhiều lớp với Role CSDL chỉ đọc, Security Barrier Views và RBAC nghiêm ngặt.", "✓ Về an toàn dữ liệu: ")
    add_bullet("Loại trừ hoàn toàn hiện tượng 'ảo giác' (Zero-Hallucination), đảm bảo tính chính xác tuyệt đối của văn bản hành chính.", "✓ Về độ tin cậy: ")
    add_bullet("Giao diện Box Chat tiện lợi và Trang làm việc chuyên sâu, hỗ trợ nhập liệu giọng nói và xem trước đa định dạng.", "✓ Về trải nghiệm: ")
    
    add_body(
        "Bản đặc tả này là tài liệu kỹ thuật chính thức làm cơ sở đối chiếu cho việc kiểm thử, bàn giao, đánh giá và "
        "tích hợp phân hệ AI Chatbox vào hệ thống quản lý văn bản chung của toàn trường.",
        space_after=20
    )
    
    # Signature block
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False
    
    c_left, c_right = sig_table.rows[0].cells[0], sig_table.rows[0].cells[1]
    c_left.width = Inches(3.2)
    c_right.width = Inches(3.3)
    
    p_l = c_left.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_l.add_run("GIẢNG VIÊN HƯỚNG DẪN\n(Ký và ghi rõ họ tên)\n\n\n\n\nNCS.ThS. Trần Phương Duy")
    r.font.name, r.font.bold, r.font.size = "Calibri", True, Pt(10)
    
    p_r = c_right.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_r.add_run("TRƯỞNG NHÓM 8 (AI CHATBOX)\n(Ký và ghi rõ họ tên)\n\n\n\n\nTrần Vũ Giang Anh")
    r.font.name, r.font.bold, r.font.size = "Calibri", True, Pt(10)
    
    return doc

if __name__ == "__main__":
    out_dir = Path(r"c:\Users\tnha8\Downloads\Baitaphehe\QuanLyVanBan_TLBM\docs")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = out_dir / "Bao_Cao_Chi_Tiet_AI_Chatbox_TLBM.docx"
    doc = build_report()
    doc.save(str(file_path))
    print(f"✅ Đã tạo thành công file Word tại: {file_path}")
    
    # Also save to root of project for easy user access
    root_file_path = Path(r"c:\Users\tnha8\Downloads\Baitaphehe\QuanLyVanBan_TLBM") / "Bao_Cao_Chi_Tiet_AI_Chatbox_TLBM.docx"
    doc.save(str(root_file_path))
    print(f"✅ Đã sao chép thêm file Word tại thư mục gốc: {root_file_path}")
