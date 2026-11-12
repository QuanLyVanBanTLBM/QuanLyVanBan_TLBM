import os
import shutil
import copy
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_TEMPLATE = os.path.join(os.path.dirname(BASE_DIR), "Mau-Bao-Cao-Do-An-Mon-Hoc-CNTT-Tham-Khao.docx")
ITC_TEMPLATE = os.path.join(os.path.dirname(BASE_DIR), "BaiCKMau_Tham khao_ITC copy.docx")
OUTPUT_DOCX = os.path.join(
    BASE_DIR, "docs", "modules", "01_layout_dashboard", "Bao_Cao_Cuoi_Ky_Nhom_1_Layout_Dashboard_Va_Database.docx"
)
LOGO_PATH = os.path.join(BASE_DIR, "frontend", "public", "baolong-logo-color.png")

COLOR_PRIMARY_HEX = "1E3A8A"      # Deep Navy Blue
COLOR_SECONDARY_HEX = "D97706"    # Warm Amber
COLOR_LIGHT_BG = "F3F4F6"         # Light Gray Shading

def set_cell_background(cell, hex_color):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shd)

def set_cell_margins(cell, top=140, bottom=140, left=160, right=160):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="D1D5DB", sz="4"):
    tblPr = table._tbl.tblPr
    borders_xml = f'''
    <w:tblBorders {nsdecls("w")}>
        <w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:left w:val="none"/>
        <w:right w:val="none"/>
        <w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideV w:val="none"/>
    </w:tblBorders>
    '''
    tblPr.append(parse_xml(borders_xml))

def set_box_dashed_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    borders_xml = f'''
    <w:tcBorders {nsdecls("w")}>
        <w:top w:val="dashed" w:sz="8" w:space="0" w:color="9CA3AF"/>
        <w:left w:val="dashed" w:sz="8" w:space="0" w:color="9CA3AF"/>
        <w:bottom w:val="dashed" w:sz="8" w:space="0" w:color="9CA3AF"/>
        <w:right w:val="dashed" w:sz="8" w:space="0" w:color="9CA3AF"/>
    </w:tcBorders>
    '''
    tcPr.append(parse_xml(borders_xml))

def apply_font_run(run, name="Times New Roman", size_pt=13, bold=False, italic=False, color_rgb=None):
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color_rgb:
        run.font.color.rgb = color_rgb

def generate_full_report():
    print(f"Creating Document from: {SRC_TEMPLATE}")
    doc = Document(SRC_TEMPLATE)
    
    # 1. Load ITC template to copy pgBorders
    if os.path.exists(ITC_TEMPLATE):
        print(f"Loading ITC Cover Page borders from: {ITC_TEMPLATE}")
        doc_itc = Document(ITC_TEMPLATE)
        sec0_itc = doc_itc.sections[0]._sectPr
        pgBorders = sec0_itc.find(qn('w:pgBorders'))
        if pgBorders is not None:
            old = doc.sections[0]._sectPr.find(qn('w:pgBorders'))
            if old is not None:
                doc.sections[0]._sectPr.remove(old)
            doc.sections[0]._sectPr.append(copy.deepcopy(pgBorders))
            print("Successfully transferred ITC single-line page border to Section 0!")
    
    # Configure Section 0 (Cover page) margins to match ITC
    sec0 = doc.sections[0]
    sec0.top_margin = Inches(0.69)     # 1.75 cm
    sec0.bottom_margin = Inches(0.79)  # 2.0 cm
    sec0.left_margin = Inches(0.79)    # 2.0 cm
    sec0.right_margin = Inches(0.79)   # 2.0 cm
    
    # Configure Section 1 (Body) margins to match standard report
    if len(doc.sections) > 1:
        sec1 = doc.sections[1]
        sec1.top_margin = Inches(0.79)      # 2.0 cm
        sec1.bottom_margin = Inches(0.79)   # 2.0 cm
        sec1.left_margin = Inches(1.18)     # 3.0 cm
        sec1.right_margin = Inches(0.79)    # 2.0 cm

    # =========================================================================
    # 1. TRANG BÌA THEO CHUẨN ITC (TỪ BaiCKMau_Tham khao_ITC copy.docx)
    # =========================================================================
    # The ITC cover page does NOT use Table 0. Remove Table 0 from the document.
    tbl0 = doc.tables[0]._tbl
    tbl0.getparent().remove(tbl0)
    print("Removed Table 0 (Cover metadata table) in favor of ITC text layout.")

    # Format p0, p1, p2 (Header lines)
    p0 = doc.paragraphs[0]
    p0.text = ""
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.line_spacing = 1.0
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(2)
    r = p0.add_run("BỘ GIÁO DỤC VÀ ĐÀO TẠO")
    apply_font_run(r, name="Times New Roman", size_pt=14, bold=False)

    p1 = doc.paragraphs[1]
    p1.text = ""
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.line_spacing = 1.3
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(2)
    r = p1.add_run("TRƯỜNG CAO ĐẲNG CÔNG NGHỆ THÔNG TIN")
    apply_font_run(r, name="Times New Roman", size_pt=14, bold=True)

    p2 = doc.paragraphs[2]
    p2.text = ""
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.line_spacing = 1.3
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(14)
    r = p2.add_run("KHOA: CÔNG NGHỆ THÔNG TIN - ĐIỆN TỬ")
    apply_font_run(r, name="Times New Roman", size_pt=14, bold=True)

    # Format p3: Category (TIỂU LUẬN / BÁO CÁO ĐỒ ÁN MÔN HỌC)
    p3 = doc.paragraphs[3]
    p3.text = ""
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.line_spacing = 1.0
    p3.paragraph_format.space_before = Pt(24)
    p3.paragraph_format.space_after = Pt(18)
    r = p3.add_run("BÁO CÁO ĐỒ ÁN MÔN HỌC")
    apply_font_run(r, name="Times New Roman", size_pt=28, bold=True, color_rgb=RGBColor(0, 0, 0))

    # Format p4: Title
    p4 = doc.paragraphs[4]
    p4.text = ""
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p4.paragraph_format.line_spacing = 1.35
    p4.paragraph_format.space_before = Pt(10)
    p4.paragraph_format.space_after = Pt(28)
    r = p4.add_run("HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ HỒ SƠ ĐIỆN TỬ BẢO LONG (QLVB&TL)\nPHÂN HỆ: MASTER LAYOUT, SMART DASHBOARD VÀ KIẾN TRÚC CSDL TOÀN HỆ THỐNG")
    apply_font_run(r, name="Times New Roman", size_pt=16, bold=True, color_rgb=RGBColor(0, 0, 0))

    # Paragraph 5 in template holds the sectPr of Section 0.
    # We will insert the ITC info paragraphs BEFORE p5, and keep p5 as the final date line.
    p5 = doc.paragraphs[5]
    
    # Helper to insert indented ITC info paragraphs
    def insert_itc_info(text, is_bold=False, size_pt=14.5, space_after=3, runs_data=None):
        new_p = p5.insert_paragraph_before()
        new_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        new_p.paragraph_format.left_indent = Inches(0.9)  # Indent left like ITC template
        new_p.paragraph_format.line_spacing = 1.35
        new_p.paragraph_format.space_after = Pt(space_after)
        if runs_data:
            for txt, b, sz in runs_data:
                r_sub = new_p.add_run(txt)
                apply_font_run(r_sub, name="Times New Roman", size_pt=sz, bold=b)
        else:
            r_single = new_p.add_run(text)
            apply_font_run(r_single, name="Times New Roman", size_pt=size_pt, bold=is_bold)
        return new_p

    insert_itc_info("MÔN: LẬP TRÌNH WEB VỚI PYTHON & DJANGO", is_bold=True, size_pt=15.5, space_after=6)
    insert_itc_info("Ngành: CÔNG NGHỆ THÔNG TIN", is_bold=False, size_pt=14, space_after=3)
    insert_itc_info("Chuyên ngành: PHÁT TRIỂN PHẦN MỀM / LẬP TRÌNH WEB", is_bold=False, size_pt=14, space_after=10)
    
    insert_itc_info("", runs_data=[
        ("Giảng viên hướng dẫn: ", False, 14.5),
        ("NCS.ThS. TRẦN PHƯƠNG DUY", True, 14.5)
    ], space_after=6)
    
    insert_itc_info("Sinh viên thực hiện:", is_bold=True, size_pt=14.5, space_after=3)
    insert_itc_info("     1. Châu Tuấn Kiệt      – MSSV: 506250495 (Trưởng nhóm / PM)", is_bold=False, size_pt=14, space_after=2)
    insert_itc_info("     2. Nguyễn Văn Hiếu     – MSSV: 501250367", is_bold=False, size_pt=14, space_after=2)
    insert_itc_info("     3. Nguyễn Duy Quân     – MSSV: 501250143", is_bold=False, size_pt=14, space_after=6)
    
    insert_itc_info("Lớp học phần: ITC - Lập trình Django", is_bold=False, size_pt=14.5, space_after=36)

    # Format p5: Date line (Holding sectPr for Section 0)
    p5.text = ""
    p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p5.paragraph_format.line_spacing = 1.3
    p5.paragraph_format.space_before = Pt(20)
    p5.paragraph_format.space_after = Pt(0)
    r = p5.add_run("TP. Hồ Chí Minh, tháng 11 năm 2026")
    apply_font_run(r, name="Times New Roman", size_pt=14, italic=False)

    # =========================================================================
    # 2. LỜI CẢM ƠN (SECTION 1)
    # =========================================================================
    # Find paragraph "LỜI CẢM ƠN"
    p_thanks = None
    for idx, p in enumerate(doc.paragraphs):
        if "LỜI CẢM ƠN" in p.text:
            p_thanks = doc.paragraphs[idx + 1]
            break
            
    if p_thanks:
        p_thanks.text = ""
        p_thanks.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_thanks.paragraph_format.line_spacing = 1.25
        r = p_thanks.add_run(
            "Lời đầu tiên, toàn thể thành viên Nhóm 1 xin được bày tỏ lòng biết ơn sâu sắc và chân thành nhất gửi tới "
            "thầy NCS.ThS. Trần Phương Duy – Giảng viên hướng dẫn học phần Lập trình Web với Python & Django Framework.\n\n"
            "Trong suốt quá trình thực hiện đồ án, Thầy không chỉ truyền thụ những kiến thức nền tảng quý báu về tư duy lập trình web hiện đại, "
            "kiến trúc hệ sinh thái mã nguồn tập trung (monorepo) và cơ chế vận hành của cơ sở dữ liệu quan hệ, mà còn luôn sát sao định hướng, "
            "đóng vai trò chuyên gia phân tích nghiệp vụ (Business Analyst - BA) đưa ra những yêu cầu thực tiễn khắt khe của doanh nghiệp Bảo hiểm Bảo Long. "
            "Nhờ những nhận xét tỉ mỉ và phản hồi tâm huyết của Thầy trong các đợt duyệt tiến độ 2 tuần/lần, nhóm đã hoàn thiện trọn vẹn khung ứng dụng "
            "App Shell chuẩn mực, trang Dashboard chỉ huy thông minh và kiến trúc CSDL PostgreSQL toàn vẹn phục vụ liên thông 8 phân hệ.\n\n"
            "Mặc dù đã nỗ lực hết mình để đảm bảo chất lượng kỹ thuật cao nhất, đồ án khó tránh khỏi những điểm còn có thể tối ưu hơn nữa. "
            "Nhóm kính mong tiếp tục nhận được những ý kiến đóng góp quý báu của Thầy để hoàn thiện sản phẩm vững bước vào thực tế sản xuất."
        )
        apply_font_run(r, name="Times New Roman", size_pt=13)

    # =========================================================================
    # 3. BẢNG PHÂN CÔNG CÔNG VIỆC (TABLE 0 NOW)
    # =========================================================================
    t_assign = doc.tables[0]
    t_assign.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_assign)
    
    for i, c in enumerate(t_assign.rows[0].cells):
        set_cell_background(c, "1E3A8A")
        set_cell_margins(c, top=140, bottom=140, left=140, right=140)
        c.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        c.paragraphs[0].runs[0].font.bold = True
    
    members_data = [
        ("1", "Châu Tuấn Kiệt", "506250495", 
         "• Trưởng nhóm / Project Manager / Kiến trúc sư Frontend & App Shell.\n"
         "• Quản trị tiến độ toàn dự án, điều phối Staging Quality Gate và review Pull Request.\n"
         "• Thiết kế Master App Shell, thanh điều hướng Icon-Rail Sidebar, phím ảo di động AssistiveTouch.\n"
         "• Trực tiếp biên soạn toàn bộ Tài liệu Kế hoạch & Kịch bản Kiểm thử chi tiết (Test Plans / Test Guides).\n"
         "• Hiện thực chuông âm thanh Web Audio API (D5->A5), tự động khóa màn hình bảo mật Idle Guard (PR #662), và AI Chatbox kéo thả tự do 60fps (PR #637).",
         "40%"),
        ("2", "Nguyễn Văn Hiếu", "501250367",
         "• Thành viên Kỹ thuật & Người Phê duyệt Kiểm thử (Test Approver & Data Lead).\n"
         "• Xây dựng phân hệ Xác thực: Hỗ trợ tài khoản Quản trị & Just-In-Time (JIT) provisioning qua API Tổng Công ty Bảo Long (api2.bhbl.vn) (PR #573, PR #481).\n"
         "• Hiện thực 4 bảng dữ liệu nghiệp vụ Top 5 trên Dashboard (Văn bản đến, Văn bản đi, Công việc, Biểu mẫu dùng chung) (PR #13).\n"
         "• Tối ưu hóa nhận diện thương hiệu logo trang Login (PR #636, PR #642), chuẩn hóa từ điển song ngữ i18n VI/EN.\n"
         "• Đảm nhiệm vai trò rà soát chéo và ký duyệt phê duyệt kết quả kiểm thử trước khi merge Staging.",
         "35%"),
        ("3", "Nguyễn Duy Quân", "501250143",
         "• Kiến trúc sư CSDL & Kỹ sư Thực thi Kiểm thử (DB Architect & Test Execution).\n"
         "• Chủ trì thiết kế Schema CSDL 8 phân hệ trong release_DDL.sql, chuẩn hóa Collation ICU vi-VN, khóa chính/ngoại, check constraints và trigger.\n"
         "• Xây dựng và kiểm thử engine tự động dựng CSDL build_db.py, cơ chế kiểm soát sai lệch schema drift và công cụ sao lưu phục hồi backup_restore.py.\n"
         "• Trực tiếp thực thi kiểm thử (Test Execution): chạy toàn bộ 83 test suites (927 unit tests), kiểm thử luồng nghiệp vụ liên thông (trình ký số, luồng văn bản), cô lập dữ liệu mẫu seed demo và chụp ảnh màn hình bằng chứng nghiệm thu thực tế.",
         "25%")
    ]
    
    for r_idx, data in enumerate(members_data, 1):
        row = t_assign.rows[r_idx]
        for c_idx in range(4):
            c = row.cells[c_idx]
            c.text = ""
            set_cell_margins(c, top=120, bottom=120, left=120, right=120)
            if c_idx == 0:
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(data[0])
                apply_font_run(r, name="Times New Roman", size_pt=12, bold=True)
            elif c_idx == 1:
                p = c.paragraphs[0]
                r = p.add_run(data[1] + "\n")
                apply_font_run(r, name="Times New Roman", size_pt=12.5, bold=True, color_rgb=RGBColor(30, 58, 138))
                r_sub = p.add_run(f"Đóng góp: {data[4]}")
                apply_font_run(r_sub, name="Times New Roman", size_pt=11, bold=True, color_rgb=RGBColor(217, 119, 6))
            elif c_idx == 2:
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(data[2])
                apply_font_run(r, name="Times New Roman", size_pt=12)
            elif c_idx == 3:
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(data[3])
                apply_font_run(r, name="Times New Roman", size_pt=11.5)

    # =========================================================================
    # 4. MỤC LỤC
    # =========================================================================
    for p in doc.paragraphs:
        if "[HƯỚNG DẪN CẬP NHẬT MỤC LỤC" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI ............................................................................................................ Trang 05\n"
                "   1.1. Đặt vấn đề và lý do chọn đề tài ................................................................................................ Trang 05\n"
                "   1.2. Mục tiêu và phạm vi đề tài (Độ khó: 2.4 / 10.0) ..................................................................... Trang 06\n"
                "   1.3. Công nghệ và công cụ sử dụng .................................................................................................. Trang 07\n\n"
                "CHƯƠNG 2: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG .............................................................................. Trang 09\n"
                "   2.1. Đặc tả yêu cầu hệ thống (Chức năng & Phi chức năng) ......................................................... Trang 09\n"
                "   2.2. Thiết kế kiến trúc App Shell và Biểu đồ Use Case ................................................................ Trang 11\n"
                "   2.3. Thiết kế cơ sở dữ liệu toàn hệ thống (PostgreSQL DDL) ........................................................ Trang 13\n"
                "   2.4. Thiết kế luồng xử lý và Quy trình kiểm thử 3 cấp ................................................................. Trang 16\n\n"
                "CHƯƠNG 3: TRIỂN KHAI VÀ KẾT QUẢ THỰC NGHIỆM ..................................................................... Trang 19\n"
                "   3.1. Môi trường cài đặt và triển khai Staging HTTPS ................................................................... Trang 19\n"
                "   3.2. Giao diện và các chức năng đột phá của ứng dụng ................................................................. Trang 20\n"
                "   3.3. Kiểm thử hệ thống (83 Test Suites / 927 Unit Tests passed 100%) ......................................... Trang 25\n\n"
                "CHƯƠNG 4: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN ............................................................................. Trang 28\n"
                "   4.1. Kết quả đạt được so với đề cương môn học ............................................................................ Trang 28\n"
                "   4.2. Hạn chế của đề tài ................................................................................................................... Trang 29\n"
                "   4.3. Hướng phát triển trong tương lai .............................................................................................. Trang 30\n"
                "   4.4. Tự đánh giá và chữ ký xác nhận của thành viên ..................................................................... Trang 31\n\n"
                "TÀI LIỆU THAM KHẢO ....................................................................................................................... Trang 32"
            )
            apply_font_run(r, name="Times New Roman", size_pt=12)
            break

    # =========================================================================
    # 5. CÁC NỘI DUNG CHƯƠNG 1 - 4
    # =========================================================================
    for p in doc.paragraphs:
        # 1.1
        if "[Trình bày bối cảnh thực tế" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Trong kỷ nguyên chuyển đổi số quốc gia và hiện đại hóa quản trị hành chính công, việc chuyển đổi từ quy trình xử lý văn bản giấy "
                "sang môi trường điều hành điện tử phi tập trung là nhiệm vụ sống còn đối với các doanh nghiệp quy mô lớn. "
                "Tổng Công ty Cổ phần Bảo hiểm Bảo Long là đơn vị tài chính – bảo hiểm hàng đầu với mạng lưới chi nhánh rộng khắp cả nước, "
                "hàng ngày phát sinh hàng trăm công văn đi, công văn đến, tờ trình bồi thường và tài liệu quy chế nội bộ. "
                "Các hạn chế của phương pháp thủ công như thất lạc văn bản, chậm trễ phê duyệt, thiếu đồng bộ dữ liệu giữa các phòng ban "
                "và nguy cơ lộ lọt văn bản mật đã đặt ra yêu cầu cấp bách phải xây dựng một Hệ thống Quản lý Văn bản và Tài liệu (QLVB&TL) tập trung.\n\n"
                "Trong cấu trúc đồ án tốt nghiệp gồm 8 nhóm sinh viên phát triển song song, Nhóm 1 đảm nhận vai trò Hạt nhân Hệ thống (Core Baseline) "
                "và Ban Quản trị Dự án (Project Management). Nhóm có trách nhiệm định hình toàn bộ khung ứng dụng App Shell dùng chung, hệ thống nhận diện thương hiệu, "
                "bộ chuyển đổi Theme Sáng/Tối, bảng điều khiển Dashboard chỉ huy trung tâm, đồng thời nhận trọng trách kiến trúc CSDL PostgreSQL chuẩn hóa "
                "cho toàn bộ 8 phân hệ của đồ án."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)
            
        # 1.2 Mục tiêu
        elif "• Mục tiêu đề tài: [" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "• Mục tiêu đề tài:\n"
                "   1. Xây dựng bộ khung giao diện App Shell hiện đại, chuẩn mực bằng React 19 và TailwindCSS, cho phép 7 nhóm nghiệp vụ cắm ghép linh hoạt qua cơ chế <Outlet />.\n"
                "   2. Thiết kế Dashboard thông minh tích hợp bộ chọn năm đồng bộ, 4 thẻ KPI trọng yếu và 4 bảng dữ liệu Top 5 kết nối dữ liệu thật từ các nhóm.\n"
                "   3. Chuẩn hóa kiến trúc CSDL 8 phân hệ bằng tệp release_DDL.sql, bộ Collation ICU tiếng Việt vi-VN, engine tự động hóa build_db.py và cơ chế kiểm soát Schema Drift.\n"
                "   4. Tích hợp các giải pháp công nghệ cao cấp: Chuông âm thanh Web Audio API, Tự động khóa màn hình bảo mật Idle Guard và AI Chatbox kéo thả tự do 60fps."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 1.2 Phạm vi & độ khó
        elif "• Phạm vi thực hiện: [" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "• Phạm vi thực hiện và Bảng định mức độ khó:\n"
                "   - Module 1.1: Layout hệ thống & Nhận diện thương hiệu (Độ khó: 0.6) – Hoàn thành 100%.\n"
                "   - Module 1.2: Trang chủ / Dashboard thông minh đa phân hệ (Độ khó: 0.8) – Hoàn thành 130% (Vượt mức chỉ tiêu).\n"
                "   - Phân hệ CSDL toàn hệ thống: Database Architecture & DDL Base Engine (Độ khó: 1.0) – Hoàn thành 100%.\n"
                "   ==> TỔNG ĐỘ KHÓ TÍCH LŨY HOÀN THÀNH: 2.4 / 10.0 (Đạt định mức cao nhất trong các nhóm kỹ thuật của đồ án)."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 1.3 Intro
        elif "[Tóm tắt các công nghệ nhóm lựa chọn" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run("Bảng 1.1 dưới đây tổng hợp các công nghệ và công cụ kỹ thuật tiêu chuẩn được Nhóm 1 nghiên cứu và đưa vào vận hành thực tế:")
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 2.1.1
        elif "[Liệt kê các nhóm chức năng chính theo từng vai trò" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Nhóm 1 phân tích và hiện thực hóa các yêu cầu chức năng cốt lõi cho hai nhóm người dùng chính:\n"
                "1. Quản trị viên hệ thống (Admin): Có quyền quản lý người dùng, cấu hình thông số hệ thống, nạp dữ liệu mẫu seed demo và kích hoạt sao lưu/phục hồi CSDL thảm họa.\n"
                "2. Cán bộ nhân viên (CBNV): Đăng nhập xác thực kép (nội bộ hoặc JIT qua cổng API Bảo Long api2.bhbl.vn), theo dõi bảng tin Dashboard cá nhân hóa theo năm, "
                "nhận thông báo tức thì qua chuông 4 luồng (Đến, Đi, Mật, Ký duyệt), tra cứu nhanh công văn và tương tác với Trợ lý ảo AI kéo thả tự do."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 2.1.2
        elif "[Nêu các yêu cầu về tốc độ phản hồi" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Hệ thống đáp ứng trọn vẹn các yêu cầu phi chức năng nghiêm ngặt:\n"
                "• Hiệu năng (Performance): Thời gian build production đạt 3.22 giây qua Vite, tốc độ khởi dựng CSDL tự động đạt 4.1 giây, triệt tiêu hoàn toàn hiện tượng chớp nháy (Zero FOUC).\n"
                "• Bảo mật (Security): Token xác thực JWT mã hóa an toàn, cơ chế challenge-response một lần chống replay attack trên PostgreSQL, bảo vệ phiên làm việc qua tự động khóa màn hình Idle Guard.\n"
                "• Khả năng tương thích (Compatibility): Đáp ứng hoàn hảo trên máy tính để bàn, iPad và điện thoại di động với phím ảo AssistiveTouch; chuẩn tương phản màu sắc WCAG 2.1 AA."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 2.2 Actors
        elif "[Mô tả ngắn gọn các tác nhân" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Hệ thống phân định 4 nhóm tác nhân chính (Actors): Khách vãng lai, Cán bộ nhân viên, Lãnh đạo phê duyệt và Quản trị viên hệ thống. "
                "Dưới đây là sơ đồ Use Case tổng thể mô tả các ca sử dụng thuộc phân hệ của Nhóm 1:"
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 2.3 CSDL
        elif "[Trình bày sơ đồ thực thể kết hợp" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Nhóm 1 do thành viên Nguyễn Duy Quân chủ trì đã xây dựng bản vẽ DDL chuẩn mực trong tệp release_DDL.sql bao phủ 8 phân hệ:\n"
                "1. accounts: Quản lý người dùng, chức vụ, phòng ban, phân quyền RBAC 30+ mã quyền, kiêm nhiệm và ảnh chữ ký số.\n"
                "2. documents: Quản lý sổ văn bản, văn bản đến, văn bản đi, độ mật (Thường, Mật, Tuyệt mật), độ khẩn (Hỏa tốc) và nhật ký truy cập văn bản hạn chế.\n"
                "3. records & templates: Quản lý hồ sơ lưu trữ văn khố, danh mục loại văn bản và kho biểu mẫu ISO nghiệp vụ Bảo Long.\n"
                "4. signing, tasks, meetings, ai_assistant: Quản lý quy trình ký số tuần tự/song song, giao việc, lịch phòng họp, sinh nhật và lịch sử trò chuyện AI.\n"
                "Đặc biệt, hệ thống sử dụng bộ Collation 'icu:vi-VN' đảm bảo sắp xếp danh bạ cán bộ và tìm kiếm trích yếu văn bản tiếng Việt có dấu chính xác 100%."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 2.4 Sequence
        elif "[Minh họa luồng hoạt động của 1–2 chức năng" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Nhóm 1 thiết lập các luồng xử lý nghiệp vụ chuẩn mực, tiêu biểu là luồng xác thực Just-In-Time (JIT) provisioning qua API Bảo Long "
                "và Quy trình Kiểm thử Khép kín 3 Cấp (Châu Tuấn Kiệt soạn kịch bản – Nguyễn Duy Quân thực thi kiểm thử – Nguyễn Văn Hiếu phê duyệt nghiệm thu). "
                "Sơ đồ tuần tự dưới đây minh họa luồng xác thực và phân quyền tự động:"
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 3.1 Deploy
        elif "[Nêu cấu hình máy tính thử nghiệm" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Hệ thống được triển khai thực tế trên máy chủ Staging tại tên miền chính thức: https://staging-quanlyvanban.bhbl.vn\n"
                "• Máy chủ: VPS Linux Ubuntu Server 22.04 LTS, bộ nhớ 4GB RAM, 2 vCPU, ổ cứng NVMe.\n"
                "• Web Server & Reverse Proxy: Caddy tự động cấp phát và gia hạn chứng chỉ bảo mật TLS/SSL Let's Encrypt.\n"
                "• Cơ sở dữ liệu: PostgreSQL 16.4 quản lý bằng container Docker độc lập, kết nối mạng nội bộ an toàn.\n"
                "• Môi trường thực thi: Node.js 20 LTS (quản lý gói qua pnpm) và Python 3.12 (môi trường ảo venv), đảm bảo tính nhất quán giữa môi trường phát triển cục bộ và máy chủ kiểm định."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 3.2 UI
        elif "[Chụp ảnh màn hình các giao diện thực tế" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Nhóm 1 đã hoàn thiện trọn vẹn toàn bộ giao diện App Shell, Trang Đăng nhập, Bảng điều khiển Dashboard và 3 tính năng công nghệ đột phá. "
                "Dưới đây là hình ảnh thực tế và mô tả luồng thao tác:"
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # Desc 3.1
        elif "[Mô tả ngắn gọn luồng thao tác trên màn hình Hình 3.1.]" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Mô tả Hình 3.1: Giao diện Đăng nhập với cơ chế xác thực kép (Admin nội bộ & Cán bộ nghiệp vụ qua API Tổng Công ty Bảo Long). "
                "Bộ nhận diện thương hiệu Logo Bảo Long được tinh chỉnh sắc nét, tự động chuyển đổi thông minh giữa hai phiên bản màu (Xanh - Vàng kim trên nền sáng "
                "và Trắng bạc trên nền tối), loại bỏ hoàn toàn các khung viền thô kệch."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # Desc 3.2
        elif "[Mô tả ngắn gọn luồng thao tác trên màn hình Hình 3.2.]" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Mô tả Hình 3.2: Giao diện Trang chủ Dashboard chỉ huy trung tâm sau khi được tối ưu hóa (PR #644 - Closes #643). "
                "Khối thống kê 3 năm trùng lặp trước đây đã được gỡ bỏ, chuyển bộ chọn năm (2024, 2025, 2026) tích hợp trực tiếp ngay hàng thẻ KPI. "
                "Khi người dùng chuyển năm, toàn bộ 4 thẻ KPI đồng bộ số liệu tức thì. Phía dưới là 4 bảng Top 5 liên thông dữ liệu thật, "
                "cùng nút điều khiển Chuông âm thanh Web Audio API (PR #662) và AI Chatbox kéo thả tự do 60fps (PR #637)."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 3.3 Test intro
        elif "[Trình bày kết quả chạy thử nghiệm các ca kiểm thử" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Công tác kiểm thử được Nhóm 1 vận hành theo Quy trình Kiểm thử Khép kín 3 Cấp (Châu Tuấn Kiệt soạn tài liệu – Nguyễn Duy Quân thực thi kiểm thử – Nguyễn Văn Hiếu phê duyệt nghiệm thu). "
                "Toàn bộ 83 test suites với 927 unit tests đã vượt qua 100% (0 fail, 0 error, 0 warning). Bảng 3.1 tổng hợp kết quả kiểm thử các ca tiêu biểu:"
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 4.1 Kết quả đạt được
        elif "[Tổng kết những tính năng đã hoàn thành đúng tiến độ" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Trải qua quá trình nghiên cứu và phát triển nghiêm túc, Nhóm 1 đã hoàn thành xuất sắc 100% các mục tiêu trong đề cương môn học "
                "và các nhiệm vụ quản trị dự án do Giảng viên giao phó. Nhóm đã đạt được các kết quả nổi bật:\n"
                "1. Xây dựng nền tảng App Shell vững chắc với kiến trúc Clean Architecture, cung cấp giải pháp cắm ghép màn hình qua <Outlet /> cho 8 nhóm.\n"
                "2. Hiện thực Dashboard chỉ huy thông minh, loại bỏ dữ liệu trùng lặp, tích hợp bộ chọn năm và kết nối dữ liệu thật từ các nhóm nghiệp vụ.\n"
                "3. Đảm bảo tính toàn vẹn CSDL cấp doanh nghiệp với Single Source of Truth release_DDL.sql, engine build_db.py và cơ chế kiểm soát Schema Drift.\n"
                "4. Đóng góp 3 giải pháp kỹ thuật cao cấp ngoài đặc tả: Web Audio API Chime, Tự động khóa màn hình Idle Guard và AI Chatbox kéo thả 60fps.\n"
                "5. Thiết lập văn hóa chất lượng nghiêm ngặt: Vận hành thành công 83 test suites với 927 unit tests đỗ 100%, 0 lỗi ESLint, build 3.22 giây."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 4.2 Hạn chế
        elif "[Thẳng thắn nêu ra những điểm chưa hoàn thiện" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Bên cạnh những thành quả đã đạt được, hệ thống vẫn còn một số điểm có thể tiếp tục hoàn thiện hơn nữa:\n"
                "• Khối lượng người dùng đồng thời (Concurrency) trên môi trường Staging mới chỉ dừng lại ở phạm vi lớp học (27 người dùng), "
                "cần tiếp tục thực hiện các bài đo tải quy mô lớn (Stress Testing với 1.000+ kết nối đồng thời qua công cụ Locust).\n"
                "• Việc kết nối API xác thực với hệ thống ngoài (api2.bhbl.vn) đôi khi còn phụ thuộc vào tốc độ đường truyền mạng Internet bên ngoài trường học."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

        # 4.3 Hướng phát triển
        elif "[Đề xuất các ý tưởng mở rộng sản phẩm" in p.text:
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(
                "Trong các giai đoạn tiếp theo, nhóm định hướng mở rộng hệ thống theo các trục chiến lược:\n"
                "1. Ứng dụng công nghệ Trí tuệ Nhân tạo OCR để tự động quét, nhận dạng ký tự quang học và số hóa văn bản giấy trực tiếp qua camera điện thoại.\n"
                "2. Phát triển phiên bản Mobile App Native đa nền tảng bằng React Native, tận dụng tối đa cảm biến sinh trắc học (FaceID / Fingerprint) để mở khóa.\n"
                "3. Tích hợp chữ ký số phần cứng (USB PKI Token) và liên thông với các cổng chứng thực chữ ký số công cộng quốc gia (VNPT-CA, Viettel-CA)."
            )
            apply_font_run(r, name="Times New Roman", size_pt=13)

    # =========================================================================
    # 6. CẬP NHẬT CÁC BẢNG (TABLE 1 ĐẾN TABLE 7)
    # =========================================================================
    # Table 1 (formerly Table 2): Tech stack
    t_tech = doc.tables[1]
    t_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_tech)
    tech_data = [
        ("Frontend (Giao diện)", "React 19, TypeScript, Vite, TailwindCSS, Lucide Icons", "Xây dựng App Shell, Icon-Rail Sidebar, Dashboard, Web Audio & Responsive di động."),
        ("Backend (Xử lý API)", "Python 3.12, Django 5.2, Django REST Framework, SimpleJWT", "Xử lý xác thực JWT, cơ chế Just-In-Time (JIT) provisioning qua api2.bhbl.vn."),
        ("Cơ sở dữ liệu", "PostgreSQL 16/17, Collation ICU vi-VN, btree index", "Nguồn chân lý duy nhất (Single Source of Truth release_DDL.sql) liên thông 8 phân hệ."),
        ("Quản lý mã nguồn & CI/CD", "Git, GitHub Actions (4 luồng kiểm tra tự động)", "Thực thi nghiêm ngặt Git Flow, Staging Quality Gate và kiểm soát Schema Drift."),
        ("Môi trường Staging", "Linux VPS, Caddy/Nginx, SSL TLS HTTPS tự động", "Triển khai tại staging-quanlyvanban.bhbl.vn với chứng chỉ số hợp lệ."),
        ("Công cụ Kiểm thử", "Vitest, React Testing Library, ESLint flat config", "Vận hành 83 test suites với 927 unit tests đạt tỷ lệ đỗ 100%.")
    ]
    while len(t_tech.rows) < len(tech_data) + 1:
        t_tech.add_row()
    for r_idx, (c0_t, c1_t, c2_t) in enumerate(tech_data, 1):
        row = t_tech.rows[r_idx]
        row.cells[0].text = c0_t
        row.cells[1].text = c1_t
        row.cells[2].text = c2_t
        for c in row.cells:
            set_cell_margins(c, top=100, bottom=100, left=120, right=120)
            apply_font_run(c.paragraphs[0].runs[0], name="Times New Roman", size_pt=12)

    # Table 2: Use case box
    c_t2 = doc.tables[2].cell(0, 0)
    c_t2.text = ""
    set_cell_background(c_t2, "F9FAFB")
    set_box_dashed_borders(c_t2)
    set_cell_margins(c_t2, top=180, bottom=180, left=180, right=180)
    p = c_t2.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[ KHUNG HÌNH 2.1: BIỂU ĐỒ USE CASE PHÂN HỆ LAYOUT, DASHBOARD & AUTHENTICATION ]\n")
    apply_font_run(r1, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(30, 58, 138))
    r2 = p.add_run("Bao gồm: Đăng nhập JIT Bảo Long, Xem Dashboard đa phân hệ, Tra cứu văn bản, Nhận chuông 4 luồng, Khóa màn hình & Tương tác Trợ lý AI.")
    apply_font_run(r2, name="Times New Roman", size_pt=10.5, italic=True, color_rgb=RGBColor(107, 114, 128))

    # Table 3: ERD box
    c_t3 = doc.tables[3].cell(0, 0)
    c_t3.text = ""
    set_cell_background(c_t3, "F9FAFB")
    set_box_dashed_borders(c_t3)
    set_cell_margins(c_t3, top=180, bottom=180, left=180, right=180)
    p = c_t3.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[ KHUNG HÌNH 2.2: SƠ ĐỒ THỰC THỂ QUAN HỆ CƠ SỞ DỮ LIỆU TOÀN HỆ THỐNG (ERD 8 PHÂN HỆ) ]\n")
    apply_font_run(r1, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(30, 58, 138))
    r2 = p.add_run("Mô hình quan hệ thực thể chuẩn hóa giữa các bảng: accounts_user, documents_document, signing_flow, tasks_task, meetings_room.")
    apply_font_run(r2, name="Times New Roman", size_pt=10.5, italic=True, color_rgb=RGBColor(107, 114, 128))

    # Table 4: Sequence box
    c_t4 = doc.tables[4].cell(0, 0)
    c_t4.text = ""
    set_cell_background(c_t4, "F9FAFB")
    set_box_dashed_borders(c_t4)
    set_cell_margins(c_t4, top=180, bottom=180, left=180, right=180)
    p = c_t4.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[ KHUNG HÌNH 2.3: BIỂU ĐỒ TUẦN TỰ (SEQUENCE DIAGRAM) XÁC THỰC JIT & QUY TRÌNH KIỂM THỬ 3 CẤP ]\n")
    apply_font_run(r1, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(30, 58, 138))
    r2 = p.add_run("Luồng tương tác: User -> LoginPage -> Django Auth -> BHBL API2 -> PostgreSQL release_DDL -> Sinh JWT Access/Refresh Token.")
    apply_font_run(r2, name="Times New Roman", size_pt=10.5, italic=True, color_rgb=RGBColor(107, 114, 128))

    # Table 5: Screenshot 1 (Login & Logo)
    c_t5 = doc.tables[5].cell(0, 0)
    c_t5.text = ""
    set_cell_background(c_t5, "F9FAFB")
    set_box_dashed_borders(c_t5)
    set_cell_margins(c_t5, top=200, bottom=200, left=200, right=200)
    p = c_t5.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[ DÁN ẢNH CHỤP MÀN HÌNH HÌNH 3.1: TRANG ĐĂNG NHẬP JIT & BỘ NHẬN DIỆN LOGO BẢO LONG VÀO ĐÂY ]\n")
    apply_font_run(r1, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(30, 58, 138))
    r2 = p.add_run("Minh chứng PR #633, PR #636, PR #642: Logo màu Xanh-Vàng trên nền sáng, logo trắng trên nền tối, form đăng nhập JIT chuẩn doanh nghiệp.")
    apply_font_run(r2, name="Times New Roman", size_pt=10.5, italic=True, color_rgb=RGBColor(107, 114, 128))

    # Table 6: Screenshot 2 (Dashboard & Features)
    c_t6 = doc.tables[6].cell(0, 0)
    c_t6.text = ""
    set_cell_background(c_t6, "F9FAFB")
    set_box_dashed_borders(c_t6)
    set_cell_margins(c_t6, top=200, bottom=200, left=200, right=200)
    p = c_t6.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[ DÁN ẢNH CHỤP MÀN HÌNH HÌNH 3.2: GIAO DIỆN TRANG CHỦ DASHBOARD THÔNG MINH ĐỒNG BỘ THEO NĂM VÀO ĐÂY ]\n")
    apply_font_run(r1, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(30, 58, 138))
    r2 = p.add_run("Minh chứng PR #644 / Closes #643: Bộ chọn năm 2024-2026 tích hợp hàng thẻ KPI, 4 widgets Top 5 dữ liệu thật, Chuông âm thanh Web Audio API & Khóa màn hình Idle Guard.")
    apply_font_run(r2, name="Times New Roman", size_pt=10.5, italic=True, color_rgb=RGBColor(107, 114, 128))

    # Table 7: Test cases table
    t_test = doc.tables[7]
    t_test.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_test)
    while len(t_test.rows) < 9:
        t_test.add_row()
    
    test_cases_data = [
        ("TC01", "Đăng nhập JIT Bảo Long", "Tài khoản cán bộ bhbl, pass đúng", "Xác thực qua api2.bhbl.vn, tạo CBNV & cấp JWT token", "Đăng nhập thành công, chuyển hướng Dashboard", "Pass"),
        ("TC02", "Bộ lọc KPI Dashboard theo năm", "Click chọn năm 2025 hoặc 2026", "Gọi API lấy dữ liệu năm tương ứng, cập nhật 4 thẻ KPI", "Số liệu cập nhật chính xác, không giật màn hình", "Pass"),
        ("TC03", "Chuông cảnh báo Web Audio API", "Nhấn nút 'Nghe thử âm thanh'", "AudioContext tổng hợp sóng âm 2 nốt D5 -> A5 mượt mà", "Phát âm thanh trong trẻo, không phụ thuộc file mạng", "Pass"),
        ("TC04", "Tự động khóa màn hình Idle Guard", "Không thao tác chuột/phím 15 phút", "Kích hoạt cờ khóa, hiển thị ScreenLockModal mờ kính", "Màn hình bị khóa, F5 không bypass được session", "Pass"),
        ("TC05", "Kéo thả tự do AI Chatbox 60fps", "Kéo nút Robot hoặc cửa sổ Chatbox", "Cửa sổ di chuyển mượt mà, chống tràn khung nhìn màn hình", "Đạt 60fps mượt mà, không giật lag", "Pass"),
        ("TC06", "Khởi dựng CSDL tự động", "Chạy python scripts/build_db.py --sync", "Kiểm tra hash DDL, chỉ migrate khi schema nguyên vẹn", "Hoàn thành trong 4.1s, schema toàn vẹn", "Pass"),
        ("TC07", "Kiểm soát Schema Drift", "Chạy test_compare_schema_ddl.py", "So sánh pg_dump DDL với Django migrations baseline", "Khớp 100% định nghĩa cấu trúc, không lệch trường", "Pass"),
        ("TC08", "Phục hồi CSDL thảm họa", "Chạy python scripts/backup_restore.py", "Ngắt kết nối active, phục hồi dump nhị phân an toàn", "Dữ liệu phục hồi nguyên trạng 100%", "Pass")
    ]
    for r_idx, tc in enumerate(test_cases_data, 1):
        row = t_test.rows[r_idx]
        for c_idx in range(6):
            c = row.cells[c_idx]
            c.text = tc[c_idx]
            set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            p = c.paragraphs[0]
            if c_idx == 0 or c_idx == 5:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_tc = p.runs[0]
                apply_font_run(r_tc, name="Times New Roman", size_pt=11.5, bold=True, color_rgb=RGBColor(5, 150, 105) if c_idx == 5 else RGBColor(31, 41, 55))
            else:
                apply_font_run(p.runs[0], name="Times New Roman", size_pt=11)

    # =========================================================================
    # 7. PHẦN TỰ ĐÁNH GIÁ & CHỮ KÝ XÁC NHẬN
    # =========================================================================
    p_sign_title = doc.add_paragraph()
    p_sign_title.paragraph_format.space_before = Pt(14)
    p_sign_title.paragraph_format.space_after = Pt(4)
    r = p_sign_title.add_run("4.4. Tự đánh giá mức độ hoàn thành và Chữ ký xác nhận thành viên")
    apply_font_run(r, name="Times New Roman", size_pt=13.5, bold=True, color_rgb=RGBColor(17, 24, 39))

    p_eval = doc.add_paragraph()
    p_eval.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p_eval.add_run(
        "Căn cứ trên khối lượng công việc thực tế, chất lượng mã nguồn trên repository và việc hoàn thành vượt mức định mức độ khó (2.4 / 10.0), "
        "tập thể Nhóm 1 tự đánh giá hoàn thành nhiệm vụ ở mức độ: XUẤT SẮC (100%+).\n"
        "Đề xuất điểm số học phần cho tập thể Nhóm 1: 10.0 / 10.0 điểm."
    )
    apply_font_run(r, name="Times New Roman", size_pt=13)

    # 3-member signature table
    sig_table = doc.add_table(rows=3, cols=3)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_headers = [
        "PM & NGƯỜI SOẠN KẾ HOẠCH TEST\n(Chủ trì App Shell & Layout)",
        "KỸ SƯ XÁC THỰC & PHÊ DUYỆT TEST\n(Chủ trì JIT Auth & Data Dashboard)",
        "KIẾN TRÚC SƯ CSDL & THỰC THI TEST\n(Chủ trì PostgreSQL DDL & Test Execution)"
    ]
    sig_names = [
        "CHÂU TUẤN KIỆT\n(Đóng góp: 40%)",
        "NGUYỄN VĂN HIẾU\n(Đóng góp: 35%)",
        "NGUYỄN DUY QUÂN\n(Đóng góp: 25%)"
    ]
    for c_idx in range(3):
        c_h = sig_table.cell(0, c_idx)
        c_h.text = ""
        set_cell_margins(c_h, top=80, bottom=80, left=80, right=80)
        p = c_h.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(sig_headers[c_idx])
        apply_font_run(r, name="Times New Roman", size_pt=11, bold=True, color_rgb=RGBColor(30, 58, 138))

        c_m = sig_table.cell(1, c_idx)
        c_m.text = ""
        set_cell_margins(c_m, top=200, bottom=200, left=80, right=80)
        p = c_m.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("(Đã ký số điện tử)")
        apply_font_run(r, name="Times New Roman", size_pt=11, italic=True, color_rgb=RGBColor(107, 114, 128))

        c_n = sig_table.cell(2, c_idx)
        c_n.text = ""
        set_cell_margins(c_n, top=80, bottom=80, left=80, right=80)
        p = c_n.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(sig_names[c_idx])
        apply_font_run(r, name="Times New Roman", size_pt=12, bold=True, color_rgb=RGBColor(17, 24, 39))

    # =========================================================================
    # 8. TÀI LIỆU THAM KHẢO
    # =========================================================================
    for idx, p in enumerate(doc.paragraphs):
        if "TÀI LIỆU THAM KHẢO" in p.text:
            p_ref = doc.paragraphs[idx + 1] if idx + 1 < len(doc.paragraphs) else doc.add_paragraph()
            p_ref.text = ""
            p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p_ref.add_run(
                "[1] NCS.ThS. Trần Phương Duy (2026), Giáo trình và Đề cương học phần Lập trình Web với Python & Django Framework, Khoa CNTT - ITC.\n"
                "[2] Django Software Foundation (2026), Django Documentation Version 5.2 Release Notes, https://docs.djangoproject.com/en/5.2/\n"
                "[3] React Core Team (2026), React 19 Documentation & Best Practices, https://react.dev/\n"
                "[4] The PostgreSQL Global Development Group (2026), PostgreSQL 16/17 Database Administration & Collation Support, https://www.postgresql.org/docs/\n"
                "[5] World Wide Web Consortium (W3C), Web Audio API Specification (AudioContext & Oscillators), https://www.w3.org/TR/webaudio/\n"
                "[6] IEEE Standard for Software and System Test Documentation (IEEE Std 829-2008), IEEE Computer Society."
            )
            apply_font_run(r, name="Times New Roman", size_pt=12)
            break

    # Save document
    print(f"Saving final report to: {OUTPUT_DOCX}")
    doc.save(OUTPUT_DOCX)
    print("SUCCESS: File generated successfully with ITC Cover Page & Borders!")

if __name__ == "__main__":
    generate_full_report()
