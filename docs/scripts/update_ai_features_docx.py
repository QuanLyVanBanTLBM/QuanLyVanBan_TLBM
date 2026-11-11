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
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=80, bottom=80, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
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

def add_callout(doc, text, title="ĐIỂM NỐT KỸ THUẬT QUAN TRỌNG", border_color="1E3A8A", bg_color="F8FAFC"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
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
    p.paragraph_format.space_after = Pt(2)
    r_title = p.add_run(f"📌 {title}: ")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(10)
    r_title.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    
    r_text = p.add_run(text)
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(10)
    r_text.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def build_ai_features_report():
    doc = Document()
    
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
        
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
    p_inst.paragraph_format.space_after = Pt(6)
    
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("─────────── ★ ───────────")
    r_line.font.color.rgb = COLOR_MUTED
    p_line.paragraph_format.space_after = Pt(12)
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("BÁO CÁO ĐẶC TẢ CHI TIẾT TÍNH NĂNG & NĂNG LỰC AI\nTRỢ LÝ THÔNG MINH TLBM (NHÁNH 8_AI_CHATBOX)")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(18)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY
    p_title.paragraph_format.space_after = Pt(4)
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU (TLBM) — MODULE 8")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(12)
    r_sub.font.bold = True
    r_sub.font.color.rgb = COLOR_SECONDARY
    p_sub.paragraph_format.space_after = Pt(16)
    
    # Metadata info table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    
    meta_data = [
        ("Phân hệ phụ trách:", "Module 8 — Trợ lý AI Chatbox & RAG (Branch: 8_ai_chatbox)"),
        ("Giảng viên hướng dẫn:", "NCS.ThS. Trần Phương Duy"),
        ("Thành viên thực hiện:", "Trần Vũ Giang Anh (Trưởng nhóm), Huỳnh Vương Thanh Nhã & Thành viên Nhóm 8"),
        ("Trọng tâm tài liệu:", "Đặc tả chuyên sâu toàn bộ Tính năng Xử lý, Giải thuật RAG, Năng lực AI & Tham số kỹ thuật")
    ]
    
    for i, (k, v) in enumerate(meta_data):
        row = meta_table.rows[i]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "F8FAFC")
        set_cell_background(c1, "F8FAFC")
        set_cell_margins(c0, 50, 50, 90, 90)
        set_cell_margins(c1, 50, 50, 90, 90)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(k)
        r0.font.name = "Calibri"
        r0.font.size = Pt(9.5)
        r0.font.bold = True
        r0.font.color.rgb = COLOR_PRIMARY
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(v)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = COLOR_DARK
        
    set_table_borders(meta_table, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(13.5)
        r.font.bold = True
        r.font.color.rgb = COLOR_PRIMARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(11.5)
        r.font.bold = True
        r.font.color.rgb = COLOR_SECONDARY
        return p

    def add_body(text, bold_prefix=None, space_after=4):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = "Calibri"
            r_bold.font.size = Pt(10.5)
            r_bold.font.bold = True
            r_bold.font.color.rgb = COLOR_DARK
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(10.5)
        r.font.color.rgb = COLOR_DARK
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.name = "Calibri"
            r_bold.font.size = Pt(10.5)
            r_bold.font.bold = True
            r_bold.font.color.rgb = COLOR_DARK
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(10.5)
        r.font.color.rgb = COLOR_DARK
        return p

    # -------------------------------------------------------------
    # 1. TỔNG QUAN NĂNG LỰC & KIẾN TRÚC TRỢ LÝ AI
    # -------------------------------------------------------------
    add_h1("1. TỔNG QUAN NĂNG LỰC & KIẾN TRÚC CỐT LÕI CỦA AI")
    add_body(
        "Trợ lý AI trong hệ thống TLBM (nhánh 8_ai_chatbox) được xây dựng trên kiến trúc RAG "
        "(Retrieval-Augmented Generation) kết hợp với các mô hình ngôn ngữ lớn tiên tiến (LLM) "
        "như Google Gemini và OpenAI GPT. Hệ thống được tinh chỉnh để phục vụ chuyên biệt cho môi trường "
        "hành chính văn phòng: độ chuẩn xác cao, bảo mật nhiều tầng và hoàn toàn loại trừ hiện tượng bịa đặt thông tin."
    )
    
    add_callout(
        doc,
        "AI hoạt động theo mô hình 'Read-only Knowledge Assistant' — chỉ tiếp nhận, truy xuất, suy luận và giải đáp "
        "dựa trên các nguồn dữ liệu được phép, không tự ý thay đổi dữ liệu hoặc thay mặt con người thực hiện các tác vụ phê duyệt/ký số.",
        title="ĐỊNH VỊ NĂNG LỰC"
    )

    # -------------------------------------------------------------
    # 2. TÍNH NĂNG 1: TRA CỨU & HỎI ĐÁP NGỮ CẢNH THÔNG MINH (RAG)
    # -------------------------------------------------------------
    add_h1("2. TÍNH NĂNG 1: TRA CỨU & HỎI ĐÁP NGỮ CẢNH THÔNG MINH (RAG)")
    add_body(
        "Khác với tìm kiếm từ khóa truyền thống chỉ khớp chính xác từng chữ, AI kết hợp tìm kiếm ngữ nghĩa "
        "(Semantic Search) với siêu dữ liệu CSDL để trả lời bằng ngôn ngữ tự nhiên:"
    )
    add_bullet(
        "AI tiếp nhận câu hỏi bằng ngôn ngữ tự nhiên, phân tích ngữ nghĩa và trích xuất đồng thời từ 3 nguồn: "
        "(1) CSDL PostgreSQL qua các view chỉ đọc an toàn, (2) Kho tri thức vector ChromaDB, và (3) Thẻ đặc tả nghiệp vụ 7 phân hệ.",
        "• Truy vấn đa nguồn đồng thời: "
    )
    add_bullet(
        "Tìm kiếm tài liệu bằng độ tương đồng vector Cosine kết hợp với các bộ lọc phân quyền và lọc chủ đề chuyên môn.",
        "• Truy xuất lai (Hybrid Retrieval): "
    )
    add_bullet(
        "Trích xuất chính xác Số hiệu văn bản, Số thứ tự trong sổ, Năm tiếp nhận, Ngày đến/ban hành, Trích yếu, "
        "Cơ quan ban hành, Người ký, Chức vụ người ký, Trạng thái hiệu lực và Ngày hết hiệu lực.",
        "• Bóc tách siêu dữ liệu hành chính: "
    )

    # -------------------------------------------------------------
    # 3. TÍNH NĂNG 2: PHÂN ĐOẠN TRI THỨC ĐA CẤP (PARENT-CHILD CHUNKING)
    # -------------------------------------------------------------
    add_h1("3. TÍNH NĂNG 2: PHÂN ĐOẠN TRI THỨC ĐA CẤP (PARENT-CHILD CHUNKING)")
    add_body(
        "Để khắc phục hạn chế cắt vụn văn bản làm mất mạch ý nghĩa, Module 8 áp dụng giải thuật phân đoạn phân cấp:"
    )
    add_bullet(
        "Kích thước 300 ký tự (Overlap: 50 ký tự). Đoạn nhỏ này được chuyển thành vector nhúng vào ChromaDB "
        "để tối ưu hóa điểm tương đồng, giúp việc tìm kiếm từ khóa và ý định câu hỏi đạt độ chính xác cao nhất.",
        "• Phân đoạn con (Child Chunks): "
    )
    add_bullet(
        "Kích thước 1.500 ký tự (Overlap: 300 ký tự). Khi tìm thấy Child Chunk phù hợp, hệ thống tự động truy vết ngược "
        "lấy toàn bộ Parent Chunk chứa nó để nạp vào Prompt cho LLM. Điều này giúp AI đọc trọn vẹn điều khoản xung quanh, "
        "không bị hiểu sai ngữ cảnh do câu bị cắt ngang.",
        "• Phân đoạn cha (Parent Chunks): "
    )

    # -------------------------------------------------------------
    # 4. TÍNH NĂNG 3: NHẬN DIỆN NGỮ CẢNH HỘI THOẠI NỐI TIẾP (QUERY REFORMULATION)
    # -------------------------------------------------------------
    add_h1("4. TÍNH NĂNG 3: NHẬN DIỆN NGỮ CẢNH HỘI THOẠI NỐI TIẾP")
    add_body(
        "AI sở hữu thuật toán phân tích chuỗi hội thoại đa lượt, hỗ trợ đắc lực khi người dùng hỏi các câu tiếp nối ngắn gọn:"
    )
    add_bullet(
        "Hàm is_follow_up_question tự động phát hiện các đại từ chỉ định và liên từ nối tiếp như: 'nó', 'đó', 'vậy thì sao', "
        "'giải thích thêm', 'chi tiết hơn', 'tại sao', 'làm thế nào'.",
        "• Nhận diện câu hỏi nối tiếp: "
    )
    add_bullet(
        "Hàm build_retrieval_query tự động tổng hợp câu hỏi hiện tại với tóm tắt câu hỏi/câu trả lời gần nhất để tái cấu trúc "
        "lại câu truy vấn vector hoàn chỉnh, đảm bảo AI tìm kiếm đúng đối tượng văn bản đang được bàn luận.",
        "• Tái tạo truy vấn (Query Reformulation): "
    )
    add_bullet(
        "Hệ thống duy trì một cửa sổ ngữ cảnh gồm 4–8 lượt trao đổi gần nhất (tối đa 800 ký tự) để vừa ghi nhớ mạch trao đổi "
        "vừa không làm tràn hạn ngạch token của mô hình.",
        "• Cửa sổ trượt lịch sử (Sliding Window): "
    )

    # -------------------------------------------------------------
    # 5. TÍNH NĂNG 4: THỊ GIÁC MÁY TÍNH & VISION OCR ĐA PHƯƠNG THỨC
    # -------------------------------------------------------------
    add_h1("5. TÍNH NĂNG 4: THỊ GIÁC MÁY TÍNH & OCR ĐA PHƯƠNG THỨC")
    add_body(
        "Xử lý các bản quét (scan), tệp ảnh chụp công văn và tài liệu kỹ thuật có cấu trúc phức tạp:"
    )
    add_bullet(
        "Trích xuất nguyên vẹn văn bản tiếng Việt có dấu, chữ viết tay ghi chú trong bản scan hành chính và văn bản in chất lượng vừa/kém.",
        "• Nhận dạng chữ in & viết tay: "
    )
    add_bullet(
        "Tự động phát hiện và chuyển đổi công thức toán, lý, hóa sang mã LaTeX chuẩn ($formula$ cho inline, $$formula$$ cho display).",
        "• Bóc tách công thức LaTeX chuẩn: "
    )
    add_bullet(
        "Bảo toàn cấu trúc dòng và cột của các bảng biểu thống kê trong văn bản số hóa, chuyển đổi thành bảng Markdown chuẩn.",
        "• Bảo toàn bảng biểu số liệu: "
    )
    add_bullet(
        "Phân tích khách quan sơ đồ tổ chức, lưu đồ quy trình ký duyệt và biểu đồ hình học để chuyển thành văn bản ngữ nghĩa.",
        "• Đọc hiểu sơ đồ & biểu đồ: "
    )
    add_bullet(
        "Ưu tiên đọc text số qua pdfplumber; nếu text ngắn hoặc chứa nhiều ký tự lỗi/công thức toán, AI tự kích hoạt RapidOCR "
        "và Gemini Multimodal Vision (DPI 150, JPEG quality 90%) để xử lý nâng cao.",
        "• Cơ chế Pipeline lai (Hybrid OCR): "
    )

    # -------------------------------------------------------------
    # 6. TÍNH NĂNG 5: TỰ ĐỘNG ĐỌC HIỂU & PHÂN LOẠI DANH MỤC TÀI LIỆU
    # -------------------------------------------------------------
    add_h1("6. TÍNH NĂNG 5: TỰ ĐỘNG ĐỌC HIỂU & PHÂN LOẠI DANH MỤC TÀI LIỆU")
    add_body(
        "Khi một tệp tài liệu mới được tải lên hệ thống, AI tự động đảm nhận vai trò phân loại nghiệp vụ:"
    )
    add_bullet(
        "AI đọc quét 5.000 ký tự đầu tiên của tài liệu để nắm bắt chủ đề cốt lõi thay vì chỉ đọc tiêu đề bề mặt.",
        "• Đọc hiểu nội dung sâu: "
    )
    add_bullet(
        "Tự động gán tài liệu vào đúng Lĩnh vực học thuật / Nghiệp vụ chuyên môn: Văn học, Toán học, Tin học, Pháp luật, "
        "Kinh tế, Y học, Kỹ thuật, Nghệ thuật, Triết học...",
        "• Phân loại theo lĩnh vực chuyên môn: "
    )
    add_bullet(
        "Lọc bỏ các tiền tố dư thừa, rút gọn nhãn danh mục còn 1–3 từ chuẩn hóa và lưu trực tiếp vào trường Category "
        "của cơ sở dữ liệu vector để hỗ trợ người dùng lọc tài liệu khi đặt câu hỏi.",
        "• Chuẩn hóa nhãn tự động: "
    )

    # -------------------------------------------------------------
    # 7. TÍNH NĂNG 6: TRA CỨU TRI THỨC NGHIỆP VỤ 7 PHÂN HỆ
    # -------------------------------------------------------------
    add_h1("7. TÍNH NĂNG 6: TRA CỨU TRI THỨC NGHIỆP VỤ 7 PHÂN HỆ TLBM")
    add_body(
        "AI được nạp sẵn tập tri thức nghiệp vụ tĩnh tóm tắt quy trình của toàn bộ 7 phân hệ trong hệ sinh thái TLBM:"
    )
    add_bullet("Giải thích các khối thống kê, theo dõi cảnh báo hạn xử lý văn bản, lịch họp hôm nay và thông báo sinh nhật.", "• Phân hệ 1 (Dashboard & Điều hành): ")
    add_bullet("Hướng dẫn quy trình 3 bước tiếp nhận văn bản đến (Vào sổ > Quét scan số hóa > Trình bút phê); soạn thảo và cấp số văn bản đi; quy chế quản lý văn bản mật.", "• Phân hệ 2 (Quản lý Văn bản): ")
    add_bullet("Quy định lập hồ sơ công việc, danh mục loại văn bản, thời hạn bảo quản hồ sơ và thủ tục nộp lưu trữ lịch sử.", "• Phân hệ 3 (Hồ sơ & Lưu trữ): ")
    add_bullet("Hướng dẫn tra cứu và tải về các biểu mẫu chuẩn DOCX, XLSX, PDF theo từng phòng ban, lĩnh vực.", "• Phân hệ 4 (Biểu mẫu Dùng chung): ")
    add_bullet("Giải thích sơ đồ luồng trình ký số điện tử đa cấp, các trạng thái luồng (Dự thảo, Đang trình ký, Đã ký, Từ chối, Thu hồi).", "• Phân hệ 5 (Trình ký Số): ")
    add_bullet("Hướng dẫn quy trình giao việc từ văn bản, phân định vai trò (Chủ trì, Chỉ đạo, Phối hợp), cập nhật tiến độ và minh chứng hoàn thành.", "• Phân hệ 6 (Giao việc & Tiến độ): ")
    add_bullet("Giải thích cơ cấu tổ chức 2 cấp, quy tắc đặt phòng họp chống trùng lịch thiết bị, và ma trận phân quyền RBAC.", "• Phân hệ 7 (Quản trị & Phòng họp): ")

    # -------------------------------------------------------------
    # 8. TÍNH NĂNG 7: KIỂM SOÁT ẢO GIÁC (ZERO-HALLUCINATION) & DẪN CHỨNG
    # -------------------------------------------------------------
    add_h1("8. TÍNH NĂNG 7: KIỂM SOÁT ẢO GIÁC (ZERO-HALLUCINATION) & DẪN CHỨNG")
    add_body(
        "Nhằm đảm bảo an toàn tuyệt đối cho công tác hành chính công, AI tuân thủ nghiêm ngặt nguyên tắc kiểm soát ảo giác:"
    )
    add_bullet(
        "System Prompt quy định cứng: AI CHỈ ĐƯỢC PHÉP TRẢ LỜI DỰA TRÊN [TÀI LIỆU CUNG CẤP]. Tuyệt đối không phỏng đoán, "
        "không suy diễn logic ngoài phạm vi tài liệu và không bổ sung kiến thức tự do từ Internet.",
        "• Nguyên tắc 'Căn cứ tuyệt đối' (Grounding): "
    )
    add_bullet(
        "Khi câu hỏi nằm ngoài phạm vi tài liệu, hàm is_no_answer() bắt buộc AI phải từ chối theo mẫu chuẩn: "
        "'Xin lỗi, thông tin bạn hỏi không có trong tài liệu được cung cấp nên tôi không thể trả lời.'",
        "• Mẫu từ chối chuẩn hóa: "
    )
    add_bullet(
        "Mọi câu trả lời của AI đều đi kèm danh sách nguồn trích dẫn cụ thể (Tên văn bản, số trang, chunk ID, điểm số tương quan).",
        "• Dẫn chứng minh bạch: "
    )

    # -------------------------------------------------------------
    # 9. TÍNH NĂNG 8: XỬ LÝ TỆP ĐA ĐỊNH DẠNG & LẬP CHỈ MỤC
    # -------------------------------------------------------------
    add_h1("9. TÍNH NĂNG 8: XỬ LÝ TẬP TIN ĐA ĐỊNH DẠNG & LẬP CHỈ MỤC")
    add_body(
        "Bộ nạp dữ liệu của AI hỗ trợ xử lý hầu hết các định dạng tệp tin văn phòng và dữ liệu số thông dụng:"
    )
    add_bullet("PDF (.pdf), Microsoft Word (.docx), Văn bản thuần (.txt), Markdown (.md, .markdown).", "• Tài liệu văn bản: ")
    add_bullet("Bảng tính CSV (.csv), Bản trình chiếu PowerPoint (.pptx - bóc tách văn bản từng slide).", "• Bảng tính & Trình chiếu: ")
    add_bullet("JSON (.json - làm phẳng cây dữ liệu thành text tìm kiếm), XML (.xml), HTML/HTM (lọc bỏ thẻ mã nguồn).", "• Dữ liệu cấu trúc: ")
    add_bullet("PNG, JPG, JPEG, WEBP, BMP, TIFF, GIF (xử lý qua pipeline OCR chuyên biệt).", "• Tệp hình ảnh: ")

    # -------------------------------------------------------------
    # 10. TÍNH NĂNG 9: CƠ CHẾ ĐA MÔ HÌNH & TỰ ĐỘNG FALLBACK DỰ PHÒNG
    # -------------------------------------------------------------
    add_h1("10. TÍNH NĂNG 9: CƠ CHẾ ĐA MÔ HÌNH & TỰ ĐỘNG FALLBACK DỰ PHÒNG")
    add_bullet("Google Gemini (mặc định: gemini-3.8-flash cho LLM và Vision OCR, models/gemini-embedding-001 cho nhúng vector).", "• Nhà cung cấp chính: ")
    add_bullet("OpenAI GPT (hỗ trợ cấu hình: gpt-4o-mini cho LLM, text-embedding-3-small cho nhúng vector).", "• Nhà cung cấp phụ: ")
    add_bullet(
        "Khi API gọi mô hình AI gặp lỗi (mất mạng, hết quota), hệ thống kích hoạt cơ chế Fallback: trích xuất và hiển thị trực tiếp "
        "các đoạn văn bản nguồn liên quan nhất (LLM_FALLBACK_ANSWER) để cán bộ tự tra cứu thay vì báo lỗi hệ thống.",
        "• Cơ chế Fallback thông minh: "
    )

    # -------------------------------------------------------------
    # 11. TÍNH NĂNG 10: BỘ LỌC AN TOÀN & PHÒNG CHỐNG TẤN CÔNG (GUARDRAILS)
    # -------------------------------------------------------------
    add_h1("11. TÍNH NĂNG 10: BỘ LỌC AN TOÀN & PHÒNG CHỐNG TẤN CÔNG")
    add_bullet(
        "Hàm is_inappropriate_message quét và chặn tự động các từ ngữ khiếm nhã, thô tục trong cả tiếng Việt và tiếng Anh, "
        "nhắc nhở người dùng giữ thái độ lịch sự.",
        "• Bộ lọc ngôn từ xúc phạm: "
    )
    add_bullet(
        "System Prompt quy định dữ liệu người dùng và tài liệu trích xuất chỉ là dữ liệu tham khảo, tuyệt đối không có quyền "
        "thay đổi quy tắc hoạt động của AI.",
        "• Chống Prompt Injection: "
    )
    add_bullet("Giới hạn độ dài câu hỏi tối đa 4.000 ký tự; dung lượng tệp tải lên tối đa 50 MB.", "• Giới hạn kích thước bảo vệ: ")

    # -------------------------------------------------------------
    # 12. BẢNG THAM SỐ THIẾT LẬP KỸ THUẬT CỦA AI
    # -------------------------------------------------------------
    add_h1("12. BẢNG TỔNG HỢP THAM SỐ KỸ THUẬT CỦA AI CHATBOX")
    
    param_table = doc.add_table(rows=11, cols=3)
    param_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    param_table.autofit = False
    
    col_w = [Inches(2.0), Inches(1.8), Inches(2.7)]
    hdr_c = param_table.rows[0].cells
    for i, title in enumerate(["Tham Số Kỹ Thuật", "Giá Trị Mặc Định", "Ý Nghĩa Chức Năng"]):
        hdr_c[i].width = col_w[i]
        set_cell_background(hdr_c[i], "1E3A8A")
        set_cell_margins(hdr_c[i], 70, 70, 80, 80)
        p = hdr_c[i].paragraphs[0]
        r = p.add_run(title)
        r.font.name, r.font.bold, r.font.size, r.font.color.rgb = "Calibri", True, Pt(9.5), RGBColor(0xFF, 0xFF, 0xFF)
        
    p_rows = [
        ("LLM_MODEL", "gemini-3.8-flash", "Mô hình ngôn ngữ chính dùng suy luận và trả lời"),
        ("EMBED_MODEL", "gemini-embedding-001", "Mô hình nhúng vector ngữ nghĩa vào ChromaDB"),
        ("VISION_MODEL", "gemini-3.8-flash", "Mô hình thị giác máy tính đọc văn bản scan & LaTeX"),
        ("PARENT_CHUNK_SIZE", "1500 ký tự (Overlap: 300)", "Kích thước đoạn văn bản cha nạp vào Prompt"),
        ("CHILD_CHUNK_SIZE", "300 ký tự (Overlap: 50)", "Kích thước đoạn văn bản con dùng tính vector"),
        ("SIMILARITY_TOP_K", "6", "Số lượng đoạn văn bản tương đồng tối đa được truy xuất"),
        ("MAX_VISIBLE_SOURCES", "4", "Số lượng nguồn tài liệu hiển thị trích dẫn cho người dùng"),
        ("SOURCE_SCORE_THRESHOLD", "0.15", "Ngưỡng điểm tương đồng tối thiểu để chấp nhận tài liệu"),
        ("CHAT_HISTORY_MAX_TURNS", "4 lượt hội thoại", "Độ dài bộ nhớ đệm lưu trữ ngữ cảnh tiếp nối"),
        ("CHAT_HISTORY_MAX_CHARS", "800 ký tự", "Giới hạn độ dài ký tự của lịch sử nạp vào Prompt"),
    ]
    
    for idx, r_data in enumerate(p_rows, start=1):
        row = param_table.rows[idx]
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(r_data):
            cell = row.cells[c_idx]
            cell.width = col_w[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, 50, 50, 80, 80)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name, r.font.size = "Calibri", Pt(9)
            if c_idx == 0:
                r.font.bold = True
                r.font.color.rgb = COLOR_PRIMARY
            else:
                r.font.color.rgb = COLOR_DARK
                
    set_table_borders(param_table, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

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
    
    # Update both the primary detailed report and create root copies
    file_path = out_dir / "Bao_Cao_Chi_Tiet_AI_Chatbox_TLBM.docx"
    doc = build_ai_features_report()
    doc.save(str(file_path))
    print(f"✅ Đã cập nhật file Word tại: {file_path}")
    
    root_file_path = Path(r"c:\Users\tnha8\Downloads\Baitaphehe\QuanLyVanBan_TLBM") / "Bao_Cao_Chi_Tiet_AI_Chatbox_TLBM.docx"
    doc.save(str(root_file_path))
    print(f"✅ Đã cập nhật file Word tại thư mục gốc: {root_file_path}")
