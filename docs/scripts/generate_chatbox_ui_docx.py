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

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
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

def add_callout(doc, text, title="ĐIỂM NỔI BẬT GIAO DIỆN", border_color="1E3A8A", bg_color="F0F4F8"):
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
    r_title = p.add_run(f"✨ {title}: ")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(10.5)
    r_title.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    
    r_text = p.add_run(text)
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(10.5)
    r_text.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def build_chatbox_ui_report():
    doc = Document()
    
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
    
    COLOR_PRIMARY = RGBColor(0x1E, 0x3A, 0x8A)     # Deep Navy
    COLOR_SECONDARY = RGBColor(0x02, 0x84, 0xC7)   # Cyan / Blue
    COLOR_DARK = RGBColor(0x0F, 0x17, 0x2A)        # Slate 900
    COLOR_MUTED = RGBColor(0x47, 0x55, 0x69)       # Slate 600
    
    # Header
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
    r_title = p_title.add_run("BÁO CÁO ĐẶC TẢ CHI TIẾT GIAO DIỆN CHATBOX AI\n(NHÁNH 8_AI_CHATBOX)")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(19)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY
    p_title.paragraph_format.space_after = Pt(4)
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU (TLBM) — PHÂN HỆ NHÓM 8")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(12.5)
    r_sub.font.bold = True
    r_sub.font.color.rgb = COLOR_SECONDARY
    p_sub.paragraph_format.space_after = Pt(16)
    
    # Meta table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    
    meta_data = [
        ("Phân hệ & Nhánh nguồn:", "Module 8 — Trợ lý AI Chatbox (Git branch: 8_ai_chatbox)"),
        ("Tác giả commit giao diện:", "tnha4209-cmyk (Huỳnh Vương Thanh Nhã) & Nhóm 8"),
        ("Tệp mã nguồn giao diện chính:", "FloatingAIBox.tsx, AiAssistantPage.tsx, ai-chat.css, AISettingsModal.jsx"),
        ("Mục tiêu tài liệu:", "Đặc tả chuyên sâu toàn bộ Bố cục, Thành phần UI, Hiệu ứng hoạt họa & Tương tác người dùng")
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
        r.font.size = Pt(14)
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
        r.font.size = Pt(12)
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
    # 1. TỔNG QUAN KIẾN TRÚC GIAO DIỆN CHATBOX (NHÁNH 8_AI_CHATBOX)
    # -------------------------------------------------------------
    add_h1("1. TỔNG QUAN KIẾN TRÚC GIAO DIỆN CHATBOX TRÊN NHÁNH 8_AI_CHATBOX")
    
    add_body(
        "Trên nhánh 8_ai_chatbox, giao diện Trợ lý AI được thiết kế và hiện thực hóa dưới 2 hình thái tương tác bổ trợ cho nhau: "
        "(1) Cửa sổ Chatbox nổi đa nhiệm (FloatingAIBox) xuất hiện xuyên suốt trên mọi phân hệ, và "
        "(2) Không gian làm việc Trợ lý AI toàn màn hình chuyên biệt (AiAssistantPage) hỗ trợ đầy đủ tác vụ nghiên cứu chuyên sâu."
    )
    
    add_callout(
        doc,
        "Cả hai hình thái giao diện đều dùng chung hệ thống Design Tokens (Vanilla CSS & Tailwind CSS), "
        "đảm bảo tính nhất quán tuyệt đối về màu sắc, bo góc, bóng đổ và hỗ trợ chuyển đổi mượt mà giữa chế độ Sáng (Light) và Tối (Dark).",
        title="TÍNH ĐỒNG BỘ GIAO DIỆN"
    )

    # -------------------------------------------------------------
    # 2. ĐẶC TẢ CHI TIẾT: CHATBOX NỔI ĐA NHIỆM (FloatingAIBox.tsx)
    # -------------------------------------------------------------
    add_h1("2. ĐẶC TẢ CHI TIẾT: CHATBOX NỔI ĐA NHIỆM (FloatingAIBox.tsx)")
    
    add_h2("2.1. Nút Robot AI Nổi (Floating Trigger Button)")
    add_bullet("Cố định ở góc dưới bên phải màn hình: fixed bottom-[72px] right-6 sm:right-8 z-[9998], cách thanh footer để không đè lên các nút điều hướng chân trang.", "Vị trí cố định: ")
    add_bullet("Kích thước chuẩn 64x64px (w-16 h-16 rounded-full). Viền gradient 3 dải màu: Tím - Xanh chính - Cyan (from-purple-600 via-primary to-cyan-400 p-[2.5px]).", "Kích thước & Màu sắc: ")
    add_bullet("Bên dưới nút có một vòng tròn hào quang xung quanh hiệu ứng sóng âm (animate-ping bg-primary/30) tạo cảm giác AI đang chủ động lắng nghe.", "Hiệu ứng Radar Pulse: ")
    add_bullet("Biểu tượng fa-solid fa-robot đổi màu khi hover, hiệu ứng zoom tương tác hover:scale-110 active:scale-95.", "Tương tác Hover/Active: ")
    add_bullet("Chấm tròn nhỏ góc trên bên phải màu xanh lá cây (bg-emerald-500 border-2 border-surface) biểu thị AI luôn ở trạng thái trực tuyến.", "Trạng thái Online: ")

    add_h2("2.2. Khung Cửa Sổ Hội Thoại Nổi (Floating Window Frame)")
    add_bullet("Chiều rộng 390px (w-[390px] max-w-[calc(100vw-32px)]), chiều cao mở rộng 540px (h-[540px] max-h-[calc(100vh-120px)]).", "Kích thước khung: ")
    add_bullet("Hiệu ứng kính mờ chiều sâu cao cấp (bg-surface-elevated/95 backdrop-blur-xl border border-subtle shadow-2xl rounded-2xl).", "Hiệu ứng Glassmorphism: ")
    add_bullet("Hỗ trợ thu gọn chỉ còn chiều cao thanh tiêu đề 56px (h-14) khi người dùng bấm nút Thu nhỏ.", "Chế độ Thu nhỏ (Minimize): ")
    add_bullet("Hiệu ứng trượt nhẹ từ dưới lên khi mở (animate-in fade-in slide-in-from-bottom-4).", "Hiệu ứng xuất hiện: ")

    add_h2("2.3. Thanh Tiêu Đề Cửa Sổ (Window Header)")
    add_bullet("Avatar robot bo góc 12px nền gradient tím/xanh kèm chấm xanh trực tuyến nhỏ.", "Avatar nhận diện: ")
    add_bullet("Dòng chữ đậm 'Trợ Lý AI TLBM' đi kèm badge công nghệ 'GPT-4o' nền tím nhạt font monospace (bg-purple-subtle text-purple).", "Nhãn & Badge Model: ")
    add_bullet("Dòng phụ đề nhỏ 10px màu text-muted: 'Trợ lý hỗ trợ quy trình & nghiệp vụ'.", "Mô tả vai trò: ")
    add_bullet("Bao gồm 4 nút chức năng nhỏ gọn 28x28px:", "Cụm 4 nút điều khiển: ")
    add_bullet("  • Nút Làm mới (fa-rotate-left): Xóa lịch sử tạm thời, khôi phục tin nhắn mở đầu.", "")
    add_bullet("  • Nút Phóng to toàn màn hình (fa-expand): Lấy cảm hứng từ nút toàn màn hình của YouTube, đóng hộp chat mini và chuyển hướng mượt mà sang trang AiAssistantPage.", "")
    add_bullet("  • Nút Thu nhỏ/Mở rộng (fa-window-minimize / fa-window-maximize): Giấu thân chat, chỉ giữ thanh tiêu đề.", "")
    add_bullet("  • Nút Đóng (fa-xmark): Thu cửa sổ trở lại nút tròn Robot nổi góc dưới.", "")

    add_h2("2.4. Khu Vực Tin Nhắn & Thẻ Gợi Ý Nhanh (Messages & Quick Replies)")
    add_bullet("Tin nhắn Người dùng căn phải (justify-end, nền primary, chữ trắng, bo tròn 16px với góc trên phải nhọn rounded-tr-sm).", "Bong bóng tin nhắn: ")
    add_bullet("Tin nhắn AI căn trái (justify-start, avatar icon não bộ fa-brain nền primary-subtle, bong bóng nền surface viền border-subtle).", "")
    add_bullet("Dưới tin nhắn AI chào mừng có sẵn 4 nút bấm gợi ý (Quick Replies) với icon tia sét vàng (fa-bolt-lightning text-warning): "
               "Quy trình tiếp nhận văn bản đến, Quy chế xử lý văn bản Tuyệt Mật, Sơ đồ trình ký số điện tử, Phân quyền vai trò cán bộ nhân viên.", "Gợi ý nhanh (Quick Replies): ")
    add_bullet("Khi AI đang sinh câu trả lời, hiển thị hiệu ứng 3 chấm tròn nảy liên tục (animate-bounce với độ trễ 0s, 0.2s, 0.4s).", "Hiệu ứng Typing Indicator: ")

    add_h2("2.5. Thanh Nhập Liệu Chân Hộp Thoại (Floating Bottom Input)")
    add_bullet("Ô nhập input bo góc 12px viền mảnh, placeholder: 'Hỏi trợ lý AI về văn bản, quy trình...'.", "Ô nhập liệu: ")
    add_bullet("Nút mở rộng toàn màn hình thứ 2 (fa-expand) đặt ngay cạnh ô gõ phím.", "Nút mở rộng: ")
    add_bullet("Nút Gửi hình máy bay giấy (fa-paper-plane) màu primary, tự động vô hiệu hóa mờ đi khi chưa nhập ký tự.", "Nút gửi: ")

    # -------------------------------------------------------------
    # 3. ĐẶC TẢ CHI TIẾT: TRANG TRỢ LÝ TOÀN MÀN HÌNH (AiAssistantPage.tsx)
    # -------------------------------------------------------------
    add_h1("3. ĐẶC TẢ CHI TIẾT: TRANG TRỢ LÝ AI CHUYÊN BIỆT (AiAssistantPage.tsx)")
    
    add_body(
        "Trang AiAssistantPage là không gian làm việc chuyên sâu với kiến trúc 2 cột linh hoạt: Sidebar quản trị bên trái "
        "và Khung trò chuyện trung tâm bên phải."
    )

    add_h2("3.1. Cột Sidebar Đa Năng (AiAssistant Sidebar - 290px)")
    add_bullet("Nút 'Đoạn chat mới' (+): Thiết kế chữ đậm nền xanh primary, hiệu ứng đổ bóng viền sáng (box-shadow glow), bấm vào sẽ tạo phiên mới tức thì.", "Nút Đoạn Chat Mới: ")
    add_bullet("Nút mũi tên đôi (fa-angles-left / right) cho phép thu hẹp sidebar từ 290px về 68px (chỉ hiển thị icon) giúp mở rộng tối đa vùng đọc văn bản.", "Thu gọn/Mở rộng Sidebar: ")
    add_bullet("Thanh chuyển đổi tab viên thuốc (Pill Switcher) gồm: Tab 'Hội thoại' (dành cho mọi cán bộ) và Tab 'Kho tài liệu' (dành riêng cho Admin).", "Tab Switcher: ")
    add_bullet("Ô tìm kiếm phiên chat theo từ khóa trong tiêu đề hoặc trích đoạn nội dung.", "Tìm kiếm phiên: ")
    add_bullet("Danh sách các phiên chat phân nhóm theo thời gian (Hôm nay, Hôm qua, 7 ngày trước), hiển thị tiêu đề, dòng tóm tắt và nút thùng rác xóa phiên.", "Danh sách phiên chat: ")
    add_bullet("Vùng Kéo - Thả tệp (Dropzone) hỗ trợ PDF, DOCX, TXT kèm thanh theo dõi tiến độ tải lên (Progress bar).", "Kéo thả tài liệu (Admin): ")
    add_bullet("Danh mục tài liệu gom nhóm theo chủ đề (Thư mục màu vàng), đếm số file, nút mắt thần xem trước, nút đũa phép phân loại lại AI, và nút xóa toàn bộ kho.", "Quản lý kho tài liệu: ")
    add_bullet("Dưới cùng sidebar có huy hiệu đếm tổng số tài liệu đã đồng bộ kèm chấm xanh nhấp nháy (Live Pulse Dot).", "Huy hiệu trạng thái: ")

    add_h2("3.2. Thanh Header Trên Cùng Của Khung Chat (Top Stage Header)")
    add_bullet("Nút mở sidebar (fa-bars) tự động xuất hiện khi sidebar đang ở trạng thái đóng.", "Nút mở nhanh: ")
    add_bullet("Logo robot AI, tiêu đề 'Trợ Lý AI Tra Cứu Quy Trình & Văn Bản', huy hiệu công nghệ 'LlamaIndex · ChromaDB'.", "Bộ nhận diện AI: ")
    add_bullet("Hộp chọn thả xuống (Select Box) cho phép người dùng chọn lọc câu trả lời theo đúng một lĩnh vực tài liệu chuyên môn.", "Bộ lọc chủ đề (Category): ")
    add_bullet("Hiển thị Provider đang hoạt động (GEMINI / OPENAI) và tên Model cụ thể (gemini-3.8-flash) kèm chấm xanh online.", "Live Model Badge: ")
    add_bullet("Nút 'Cài đặt AI' (bánh răng - mở AISettingsModal), Nút 'Xuất' (tải toàn bộ nội dung chat ra tệp Markdown .md), Nút 'Làm mới' (reset phiên).", "Cụm nút công cụ: ")

    add_h2("3.3. Lưới 4 Thẻ Gợi Ý Tra Cứu Chuẩn Thương Hiệu (Prompt Templates Grid)")
    add_body(
        "Khi mở một phiên hội thoại mới chưa có tin nhắn, màn hình hiển thị trung tâm một lưới 4 thẻ mẫu đẹp mắt:"
    )

    prompt_tbl = doc.add_table(rows=5, cols=3)
    prompt_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    prompt_tbl.autofit = False
    
    col_w = [Inches(1.8), Inches(1.5), Inches(3.2)]
    hdr_c = prompt_tbl.rows[0].cells
    for i, title in enumerate(["Tiêu Đề Thẻ", "Màu Sắc & Icon", "Câu Lệnh Gửi Đi (Query)"]):
        hdr_c[i].width = col_w[i]
        set_cell_background(hdr_c[i], "1E3A8A")
        set_cell_margins(hdr_c[i], 70, 70, 80, 80)
        p = hdr_c[i].paragraphs[0]
        r = p.add_run(title)
        r.font.name, r.font.bold, r.font.size, r.font.color.rgb = "Calibri", True, Pt(9.5), RGBColor(0xFF, 0xFF, 0xFF)
        
    p_rows = [
        ("Tiếp nhận Văn bản Đến", "Primary Blue / fa-inbox", "Hướng dẫn quy trình tiếp nhận và xử lý văn bản đến trong ngày?"),
        ("Xử lý Văn bản Mật", "Danger Red / fa-shield-halved", "Quy định bảo mật và quy trình chuyển giao văn bản tuyệt mật?"),
        ("Quy trình Trình Ký Số", "Warning Amber / fa-file-signature", "Làm thế nào để tạo luồng trình ký số điện tử trên hệ thống?"),
        ("Cơ cấu & Phân quyền", "Success Green / fa-sitemap", "Hệ thống phân quyền cán bộ nhân viên hoạt động như thế nào?"),
    ]
    
    for idx, r_data in enumerate(p_rows, start=1):
        row = prompt_tbl.rows[idx]
        bg = "F8FAFC" if idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(r_data):
            cell = row.cells[c_idx]
            cell.width = col_w[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, 50, 50, 80, 80)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name, r.font.size = "Calibri", Pt(9.5)
            if c_idx == 0:
                r.font.bold = True
                r.font.color.rgb = COLOR_PRIMARY
            else:
                r.font.color.rgb = COLOR_DARK
                
    set_table_borders(prompt_tbl, "CBD5E1", "6")
    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    add_h2("3.4. Cấu Trúc Bong Bóng Tin Nhắn & Hộp Trích Dẫn (Message & Citations)")
    add_bullet("Avatar chữ cái đầu của tên cán bộ (ví dụ: 'H' - Huỳnh Vương Thanh Nhã) vs Icon não bộ AI (fa-brain).", "Avatar cá nhân hóa: ")
    add_bullet("Hỗ trợ hiển thị Markdown đa cấp: Tiêu đề H4 màu primary, danh sách gạch đầu dòng, khối code monospace, chữ in đậm.", "Markdown Đa Cấp: ")
    add_bullet("CitationsBox nằm ngay dưới câu trả lời của AI. Bao gồm các viên thuốc trích dẫn (Citation Pills) có icon tệp tương ứng "
               "(fa-file-pdf, fa-file-lines, fa-shield-halved cho văn bản mật, fa-diagram-project cho thẻ đặc tả spec). "
               "Nhấp vào sẽ mở Modal xem trước hoặc điều hướng trực tiếp sang module liên quan.", "Hộp Trích Dẫn Minh Bạch: ")
    add_bullet("Cung cấp sẵn các nút câu hỏi nối tiếp: 'Tóm tắt các điểm quan trọng', 'Trích xuất số liệu liên quan', 'Văn bản quy định căn cứ'.", "Follow-up Prompts: ")
    add_bullet("Bộ công cụ nằm dưới cùng mỗi phản hồi AI gồm 4 tính năng: Nút Sao chép (Copy to Clipboard), Nút Đánh giá Hữu ích (Thumbs up), "
               "Nút Cần cải thiện (Thumbs down), và Nút Đọc to bằng giọng nói tiếng Việt (TTS SpeechSynthesis).", "Thanh Công Cụ Toolbar: ")
    add_bullet("Khi AI đang xử lý, hiển thị khối thông báo Thinking Card với spinner xoay tròn và thông điệp: "
               "'Trợ lý AI đang tra cứu cơ sở dữ liệu văn bản TLBM và tổng hợp câu trả lời...'", "Thinking Card: ")

    add_h2("3.5. Thanh Nhập Liệu Đa Phương Thức Ở Đáy (Bottom Multimodal Input Bar)")
    add_bullet("Khi có tệp được chọn, một thẻ nhỏ hiển thị tên tệp và nút gỡ bỏ (x) xuất hiện nổi lên trên thanh nhập liệu.", "Thẻ Xem Trước Tệp Đính Kèm: ")
    add_bullet("Icon kẹp giấy (fa-paperclip) cho phép Admin chọn tải tài liệu định dạng .pdf, .doc, .docx, .txt.", "Nút Đính Kèm Tệp: ")
    add_bullet("Khung Textarea tự động co giãn dòng, nhấn Enter để gửi, Shift+Enter để xuống dòng.", "Khung Gõ Tin Nhắn: ")
    add_bullet("Nút micro (fa-microphone) kích hoạt nhận diện giọng nói tiếng Việt trực tiếp qua Web Speech API. "
               "Khi đang lắng nghe, nút chuyển sang màu đỏ và phát hiệu ứng sóng âm nhấp nháy (.voice-btn.listening).", "Nhập Liệu Giọng Nói: ")
    add_bullet("Nút tròn màu xanh primary (fa-paper-plane) để gửi tin nhắn.", "Nút Gửi Tin Nhắn: ")
    add_bullet("Dòng chữ nhỏ dưới cùng nhắc nhở cán bộ kiểm tra đối chiếu văn bản gốc đối với các thông tin pháp lý quan trọng.", "Dòng Lưu Ý Pháp Lý: ")

    # -------------------------------------------------------------
    # 4. ĐẶC TẢ CÁC MODAL TƯƠNG TÁC BỔ TRỢ
    # -------------------------------------------------------------
    add_h1("4. ĐẶC TẢ CHI TIẾT CÁC CỬA SỔ MODAL BỔ TRỢ")
    
    add_h2("4.1. Modal Xem Trước Tài Liệu Trực Quan (DocumentPreviewModal)")
    add_bullet("Lớp phủ tối mờ có hiệu ứng làm mờ nền (backdrop-blur-sm). Nhấn phím Escape hoặc nhấn ra ngoài để đóng modal.", "Backdrop & Thoát: ")
    add_bullet("Kích thước cực lớn (rộng tới 1100px cho PDF, 900px cho văn bản thường), chiếm 85vh màn hình.", "Kích thước Panel: ")
    add_bullet("Hiển thị tên tệp đầy đủ, badge loại file (PDF/DOCX/TXT), tổng số phần/trang, nút sao chép toàn văn, nút mở tab mới và nút đóng X.", "Header Xem Trước: ")
    add_bullet("Với tệp PDF, nhúng trực tiếp bộ dựng iframe PDF/canvas chuyên nghiệp với đầy đủ thanh công cụ zoom, in ấn và tìm kiếm.", "Trình xem PDF: ")
    add_bullet("Với tệp DOCX/TXT, cung cấp 2 tab chuyển đổi: Tab 'Toàn bộ văn bản' và Tab 'Theo từng phần' (phân đoạn thông minh).", "Trình xem Word/Text: ")

    add_h2("4.2. Modal Cài Đặt Tham Số AI Nâng Cao (AISettingsModal.jsx)")
    add_bullet("Modal dành riêng cho Quản trị viên hệ thống để kiểm soát toàn bộ cơ chế vận hành của AI:", "Đối tượng áp dụng: ")
    add_bullet("Cho phép chuyển đổi linh hoạt giữa Google Gemini Cloud AI và OpenAI GPT.", "Lựa chọn Provider: ")
    add_bullet("Ô nhập API Key bảo mật có tính năng ẩn/hiện con mắt, tự động che mờ khóa khi hiển thị.", "Nhập & Kiểm tra API Key: ")
    add_bullet("Cho phép chỉ định các phiên bản mô hình: gemini-3.8-flash, gpt-4o-mini, v.v.", "Cấu hình Model LLM: ")
    add_bullet("Khi lưu cấu hình, hệ thống tự động gọi API kiểm tra tính hợp lệ của key ngay lập tức và trả về thông báo trạng thái màu xanh/đỏ.", "Xác thực kết nối tức thì: ")

    # -------------------------------------------------------------
    # 5. KẾT LUẬN & ĐÁNH GIÁ THIẾT KẾ GIAO DIỆN CHATBOX
    # -------------------------------------------------------------
    add_h1("5. KẾT LUẬN & ĐÁNH GIÁ THIẾT KẾ GIAO DIỆN CHATBOX")
    
    add_body(
        "Giao diện phân hệ AI Chatbox trên nhánh 8_ai_chatbox đại diện cho bước đột phá về trải nghiệm người dùng trong hệ thống TLBM:"
    )
    add_bullet("Sự kết hợp hoàn hảo giữa Chatbox nổi đa nhiệm (tiện dụng, không ngắt quãng công việc) và Trang trợ lý toàn màn hình (chuyên sâu, đầy đủ công cụ tra cứu).", "✓ Đa dạng hình thái: ")
    add_bullet("Áp dụng triệt để ngôn ngữ thiết kế hiện đại (Glassmorphism, hiệu ứng sóng âm, viền phát sáng, bo góc mềm mại).", "✓ Tính thẩm mỹ cao: ")
    add_bullet("Hỗ trợ trọn vẹn cả gõ phím, tải tệp kéo thả, và ra lệnh bằng giọng nói tiếng Việt.", "✓ Tương tác đa phương thức: ")
    add_bullet("Tích hợp xem trước tài liệu và trích dẫn liên kết trực tiếp, bảo đảm tính minh bạch cao nhất của văn bản hành chính.", "✓ Trải nghiệm nghiệp vụ: ")
    
    doc.add_paragraph().paragraph_format.space_after = Pt(16)
    
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
    r = p_r.add_run("NGƯỜI THỰC HIỆN (NHÁNH 8_AI_CHATBOX)\n(Ký và ghi rõ họ tên)\n\n\n\n\nHuỳnh Vương Thanh Nhã")
    r.font.name, r.font.bold, r.font.size = "Calibri", True, Pt(10)
    
    return doc

if __name__ == "__main__":
    out_dir = Path(r"c:\Users\tnha8\Downloads\Baitaphehe\QuanLyVanBan_TLBM\docs")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = out_dir / "Bao_Cao_Giao_Dien_AI_Chatbox_TLBM.docx"
    doc = build_chatbox_ui_report()
    doc.save(str(file_path))
    print(f"✅ Đã tạo thành công file Word tại: {file_path}")
    
    root_file_path = Path(r"c:\Users\tnha8\Downloads\Baitaphehe\QuanLyVanBan_TLBM") / "Bao_Cao_Giao_Dien_AI_Chatbox_TLBM.docx"
    doc.save(str(root_file_path))
    print(f"✅ Đã sao chép thêm file Word tại thư mục gốc: {root_file_path}")
