import os
import shutil
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

ROOT_DIR = r"d:\QuanLyVanBan_TLBM"
QA_DIR = os.path.join(ROOT_DIR, "docs", "qa", "nhom_8")
DESKTOP_PATH = os.path.expanduser(r"~\Desktop")
OUTPUT_DOCX_NAME = "Bao_Cao_Kiem_Thu_Bug_Nhom_8.docx"
DESKTOP_DOCX = os.path.join(DESKTOP_PATH, OUTPUT_DOCX_NAME)
WORKSPACE_DOCX = os.path.join(QA_DIR, OUTPUT_DOCX_NAME)

def set_cell_background(cell, hex_color):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_word_report():
    doc = Document()
    
    # Page setup - Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
    
    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("BÁO CÁO KIỂM THỬ SỰ CỐ & LỖI (BUG REPORT)\nPHÂN HỆ NHÓM 8: TRỢ LÝ AI & CHATBOX")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)
    
    # Metadata Paragraph
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_meta = p_meta.add_run("Dự án: Hệ thống Quản trị Văn bản & Điều hành Tác nghiệp TLBM\n"
                              "Đơn vị kiểm thử: Nhóm 5 (Senior QA/QC)  |  Ngày thực hiện: 24/10/2026\n"
                              "Môi trường: Frontend Vite (5173), Backend Django REST (8001), PostgreSQL 16")
    run_meta.font.name = "Arial"
    run_meta.font.size = Pt(10)
    run_meta.font.italic = True
    run_meta.font.color.rgb = RGBColor(100, 116, 139)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Section 1: Summary Table
    h1 = doc.add_paragraph()
    r_h1 = h1.add_run("I. BẢNG TỔNG HỢP DANH SÁCH 15 BUG (KHỚP GOOGLE SHEETS)")
    r_h1.font.name = "Arial"
    r_h1.font.size = Pt(13)
    r_h1.font.bold = True
    r_h1.font.color.rgb = RGBColor(30, 58, 138)
    
    bugs_data = [
        ("1", "Trợ lý AI", "Lỗi API chat bị chặn 403 do thiếu CSDL chỉ đọc", "High", "bug_01_chat_error_403.png"),
        ("2", "Trợ lý AI", "Cấu hình tên mô hình Gemini ảo không tồn tại (gemini-3.8-flash)", "High", "bug_02_model_gemini_fake.png"),
        ("3", "Trợ lý AI", "Giao diện chọn tiếng Anh (EN) nhưng lời chào vẫn 100% tiếng Việt", "Medium", "bug_03_i18n_greeting_vietnamese.png"),
        ("4", "Trợ lý AI", "Chip câu hỏi gợi ý sai quy chuẩn kỹ thuật ký số (Token PKI)", "Medium", "bug_04_chip_token_pki_wrong_spec.png"),
        ("5", "Trợ lý AI", "Lỗi dính chữ trong Cài đặt AI (Google GeminiKhuyên dùng)", "Medium", "bug_05_settings_glued_gemini.png"),
        ("6", "Trợ lý AI", "Lỗi dính chữ tên provider và model OpenAI (OpenAIGPT-4o)", "Medium", "bug_06_settings_glued_openai.png"),
        ("7", "Trợ lý AI", "Dropdown Cài đặt AI chứa model ảo gemini-3.8-flash", "High", "bug_07_settings_dropdown_fake_gemini_38.png"),
        ("8", "Trợ lý AI", "Lỗi tràn viền và cắt cụt text ô Mô hình Vector Embedding", "Medium", "bug_08_settings_embedding_text_overflow.png"),
        ("9", "Trợ lý AI", "Header modal Cài đặt AI dùng màu tím cứng vi phạm Design Tokens", "Medium", "bug_09_settings_header_color_token_violation.png"),
        ("10", "Trợ lý AI", "Kho tài liệu hiển thị cây thư mục mẫu giả định (folder1, item1.docx)", "Medium", "bug_10_kho_tai_lieu_mock_data_tree.png"),
        ("11", "Trợ lý AI", "Nút Xóa toàn bộ kho tài liệu nguy hiểm, thiếu bảo vệ xác nhận", "High", "bug_11_kho_tai_lieu_dangerous_delete_all.png"),
        ("12", "Trợ lý AI", "Biểu tượng AI tròn xanh nằm đè lên thanh Menu điều hướng bên trái", "Medium", "bug_12_floating_robot_overlap_navbar.png"),
        ("13", "Trang chủ / Widget AI", "Floating AI Box dùng dữ liệu mock (setTimeout), ngắt kết nối backend", "High", "bug_13_floating_ai_mock_timeout_response.png"),
        ("14", "Trang chủ / Widget AI", "Xung đột mô hình giữa Trang chính (Gemini) và Widget nổi (GPT-4o)", "Medium", "bug_14_floating_ai_badge_gpt4o_inconsistent.png"),
        ("15", "Trang chủ / Widget AI", "Floating AI Box không parse Markdown, in thô dấu sao (**)", "Medium", "bug_15_floating_ai_raw_markdown_asterisks.png"),
    ]
    
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    headers = ["STT", "Trang / Module", "Tên sự cố (Name)", "Mức độ", "Hình ảnh bằng chứng"]
    col_widths = [Inches(0.5), Inches(1.5), Inches(2.8), Inches(0.9), Inches(1.3)]
    
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1E3A8A")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Arial"
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            
    for row_idx, item in enumerate(bugs_data):
        row_cells = table.add_row().cells
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for i, val in enumerate(item):
            row_cells[i].text = val
            set_cell_background(row_cells[i], bg_color)
            set_cell_margins(row_cells[i], top=100, bottom=100, left=100, right=100)
            p = row_cells[i].paragraphs[0]
            if i in [0, 3]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(9)
                if i == 3: # Priority
                    run.font.bold = True
                    if val == "High":
                        run.font.color.rgb = RGBColor(220, 38, 38)
                    else:
                        run.font.color.rgb = RGBColor(217, 119, 6)
                        
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    doc.add_page_break()

    # Section 2: Detailed Bug Descriptions with Images
    h2 = doc.add_paragraph()
    r_h2 = h2.add_run("II. CHI TIẾT 15 BUG & HÌNH ẢNH MINH CHỨNG (CHỈ MŨI TÊN ĐỎ LIGHTSHOT)")
    r_h2.font.name = "Arial"
    r_h2.font.size = Pt(13)
    r_h2.font.bold = True
    r_h2.font.color.rgb = RGBColor(30, 58, 138)

    detailed_bugs = [
        {
            "id": "1",
            "name": "Lỗi API chat bị chặn 403 do thiếu CSDL chỉ đọc",
            "page": "Trợ lý AI (/ai-assistant)",
            "priority": "High (Nghiêm trọng)",
            "desc": "Khi người dùng gửi câu hỏi tra cứu quy trình/văn bản, endpoint backend /api/ai/chat phản hồi mã trạng thái HTTP 403 do thiếu biến môi trường DB_READONLY_USER; giao diện frontend in trực tiếp chuỗi lỗi JSON thô ('Thiếu cấu hình kết nối CSDL chỉ đọc cho AI.') vào bong bóng tin nhắn thay vì hiển thị thông báo lỗi thân thiện.",
            "impact": "Người dùng không thể tương tác hỏi đáp với Trợ lý AI; lộ chi tiết cấu hình cơ sở dữ liệu nội bộ trên giao diện.",
            "fix": "Bổ sung cấu hình người dùng CSDL chỉ đọc trong .env và xử lý bắt exception tại frontend để hiển thị toast thông báo chuẩn mực.",
            "img": "bug_01_chat_error_403.png"
        },
        {
            "id": "2",
            "name": "Cấu hình tên mô hình Gemini ảo không tồn tại (gemini-3.8-flash)",
            "page": "Trợ lý AI (Header badge & Config)",
            "priority": "High (Nghiêm trọng)",
            "desc": "Mã nguồn frontend và backend đang gán giá trị mặc định cho mô hình Google Gemini là 'gemini-3.8-flash'. Đây là tên mô hình hoàn toàn không tồn tại trong danh mục chính thức của Google Gemini API (các mô hình chuẩn: gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro).",
            "impact": "Gây lỗi 404 Model Not Found khi hệ thống thực hiện gọi yêu cầu suy luận thực tế tới Google AI Studio.",
            "fix": "Chuẩn hóa tên model mặc định trong backend/apps/ai/ và AiAssistantPage.tsx về gemini-1.5-flash hoặc gemini-2.0-flash.",
            "img": "bug_02_model_gemini_fake.png"
        },
        {
            "id": "3",
            "name": "Giao diện chọn tiếng Anh (EN) nhưng lời chào vẫn 100% tiếng Việt",
            "page": "Trợ lý AI (/ai-assistant)",
            "priority": "Medium (Trung bình)",
            "desc": "Khi người dùng chọn cờ chuyển đổi ngôn ngữ sang tiếng Anh (EN), tiêu đề lời chào ('Xin chào Quý Cán bộ!') và nội dung giới thiệu ('Tôi là Trợ Lý AI TLBM...') vẫn giữ nguyên 100% tiếng Việt, vi phạm trụ cột quốc tế hóa i18n của hệ thống.",
            "impact": "Trải nghiệm người dùng quốc tế bị gián đoạn; vi phạm tiêu chuẩn kỹ thuật đa ngôn ngữ bắt buộc của dự án.",
            "fix": "Sử dụng hook translation t('ai.welcome_title') và t('ai.welcome_desc') với đầy đủ bộ từ điển tại vi.json và en.json.",
            "img": "bug_03_i18n_greeting_vietnamese.png"
        },
        {
            "id": "4",
            "name": "Chip câu hỏi gợi ý sai quy chuẩn kỹ thuật ký số (Token PKI)",
            "page": "Trợ lý AI (/ai-assistant)",
            "priority": "Medium (Trung bình)",
            "desc": "Khối câu hỏi mẫu hiển thị thẻ 'Hướng dẫn ký số điện tử token PKI?'. Tuy nhiên, toàn bộ kiến trúc ký số của hệ thống TLBM sử dụng chữ ký điện tử nội bộ chuẩn Ed25519 (Khóa ký & PIN, 2FA OTP), không sử dụng USB Token PKI của nhà mạng bên ngoài.",
            "impact": "Gây hiểu lầm nghiêm trọng về quy trình ký duyệt nội bộ và cơ chế bảo mật của ứng dụng.",
            "fix": "Sửa nhãn chip câu hỏi mẫu thành: 'Hướng dẫn ký số điện tử nội bộ (Khóa ký & PIN)?'.",
            "img": "bug_04_chip_token_pki_wrong_spec.png"
        },
        {
            "id": "5",
            "name": "Lỗi dính chữ trong Cài đặt AI (Google GeminiKhuyên dùng)",
            "page": "Modal Cài đặt AI (AISettingsModal.jsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Tại mục chọn Nhà cung cấp AI (Provider), nhãn văn bản 'Google Gemini' và huy hiệu xanh 'Khuyên dùng' bị dính chặt vào nhau tạo thành chuỗi 'Google GeminiKhuyên dùng' do thiếu margin và khoảng trắng cách ly.",
            "impact": "Lỗi thẩm mỹ giao diện, giảm tính chuyên nghiệp của hệ thống hành chính số.",
            "fix": "Bổ sung khoảng trắng hoặc margin-left (gap: 8px) giữa tên nhà cung cấp và thẻ badge.",
            "img": "bug_05_settings_glued_gemini.png"
        },
        {
            "id": "6",
            "name": "Lỗi dính chữ tên provider và model OpenAI (OpenAIGPT-4o)",
            "page": "Modal Cài đặt AI (AISettingsModal.jsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Tại tùy chọn nhà cung cấp OpenAI, chuỗi ký tự hiển thị bị dính liền thành 'OpenAIGPT-4o / GPT-4o-mini' thay vì có dấu cách phân định rõ ràng giữa tên hãng OpenAI và dòng mô hình GPT-4o.",
            "impact": "Giao diện hiển thị sai lỗi chính tả và căn lề typographic.",
            "fix": "Thêm khoảng trắng và định dạng rõ: 'OpenAI (GPT-4o / GPT-4o-mini)'.",
            "img": "bug_06_settings_glued_openai.png"
        },
        {
            "id": "7",
            "name": "Dropdown Cài đặt AI chứa model ảo gemini-3.8-flash",
            "page": "Modal Cài đặt AI (AISettingsModal.jsx)",
            "priority": "High (Nghiêm trọng)",
            "desc": "Trong danh sách thả xuống 'Mô hình LLM (Hỏi đáp & Phân loại)', mục chọn khuyến nghị được gắn tên 'gemini-3.8-flash (Khuyên dùng - Nhanh & Mới nhất)'. Khi người dùng lưu cấu hình này, toàn bộ yêu cầu tra cứu AI sẽ bị lỗi.",
            "impact": "Khiến toàn bộ chức năng hỏi đáp AI bị vô hiệu hóa sau khi người dùng lưu cài đặt.",
            "fix": "Cập nhật danh sách select với các phiên bản hợp lệ: gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro.",
            "img": "bug_07_settings_dropdown_fake_gemini_38.png"
        },
        {
            "id": "8",
            "name": "Lỗi tràn viền và cắt cụt text ô Mô hình Vector Embedding",
            "page": "Modal Cài đặt AI (AISettingsModal.jsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Tại hàng 'Mô hình Vector Embedding', trường chọn mô hình có kích thước chiều ngang không đủ, dẫn tới văn bản 'models/gemini-embedding-0...' bị tràn lề phải và cắt cụt đuôi chuỗi.",
            "impact": "Người dùng không thể xem trọn vẹn tên mô hình embedding đang được áp dụng.",
            "fix": "Điều chỉnh layout flexbox/grid và áp dụng text-overflow hoặc mở rộng chiều rộng của container.",
            "img": "bug_08_settings_embedding_text_overflow.png"
        },
        {
            "id": "9",
            "name": "Header modal Cài đặt AI dùng màu tím cứng vi phạm Design Tokens",
            "page": "Modal Cài đặt AI (AISettingsModal.jsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Khối header của modal sử dụng màu tím cố định (#4338ca) thay vì sử dụng biến màu Design Tokens chuẩn (var(--color-brand-primary)) được quy định trong src/styles/global.css.",
            "impact": "Không đồng bộ màu nhận diện thương hiệu Bảo Long và làm hỏng khả năng tương thích khi chuyển đổi chế độ giao diện.",
            "fix": "Thay thế mã màu hex bằng biến token var(--color-brand-primary).",
            "img": "bug_09_settings_header_color_token_violation.png"
        },
        {
            "id": "10",
            "name": "Kho tài liệu hiển thị cây thư mục mẫu giả định (folder1, item1.docx)",
            "page": "Kho tài liệu AI (/ai-assistant?tab=knowledge)",
            "priority": "Medium (Trung bình)",
            "desc": "Cây thư mục quản lý tài liệu hiển thị cấu trúc giả lập hardcode gồm các thư mục 'folder1', 'folder2' và các tập tin 'item1.docx', 'item2.docx', 'item3.docx' thay vì hiển thị dữ liệu văn bản thực từ database.",
            "impact": "Người dùng không nắm bắt được danh mục hồ sơ tài liệu quy trình thực tế được nạp vào cơ sở tri thức.",
            "fix": "Kết nối API /api/ai/documents để tải cây danh mục tài liệu thực tế của hệ thống.",
            "img": "bug_10_kho_tai_lieu_mock_data_tree.png"
        },
        {
            "id": "11",
            "name": "Nút Xóa toàn bộ kho tài liệu nguy hiểm, thiếu bảo vệ xác nhận",
            "page": "Kho tài liệu AI (/ai-assistant?tab=knowledge)",
            "priority": "High (Nghiêm trọng)",
            "desc": "Nút màu đỏ 'Xóa toàn bộ kho tài liệu' cho phép kích hoạt lệnh xóa sạch cơ sở dữ liệu vector nhưng không yêu cầu gõ chữ xác nhận bảo vệ ('DELETE') và không giới hạn quyền chỉ dành cho quản trị viên tối cao.",
            "impact": "Nguy cơ mất trắng toàn bộ dữ liệu chỉ mục tìm kiếm ngữ nghĩa nếu người dùng thao tác nhầm.",
            "fix": "Bổ sung modal xác nhận gõ chuỗi 'DELETE' và ẩn nút này đối với các tài khoản không có quyền Admin.",
            "img": "bug_11_kho_tai_lieu_dangerous_delete_all.png"
        },
        {
            "id": "12",
            "name": "Biểu tượng AI tròn xanh nằm đè lên thanh Menu điều hướng bên trái",
            "page": "Toàn hệ thống (Layout navbar)",
            "priority": "Medium (Trung bình)",
            "desc": "Nút tròn AI nổi (Floating Trigger) được định vị cố định ở góc trái màn hình (y ≈ 760px) nằm đè trực tiếp lên thanh menu navigation bên trái, che khuất biểu tượng chức năng và cản trở thao tác bấm.",
            "impact": "Gây cản trở thao tác điều hướng của người dùng khi sử dụng menu hệ thống.",
            "fix": "Điều chỉnh vị trí nút nổi sang góc dưới bên phải màn hình hoặc ẩn khi thanh điều hướng bên trái mở rộng.",
            "img": "bug_12_floating_robot_overlap_navbar.png"
        },
        {
            "id": "13",
            "name": "Floating AI Box dùng dữ liệu mock (setTimeout), ngắt kết nối backend",
            "page": "Widget nổi (FloatingAIBox.tsx)",
            "priority": "High (Nghiêm trọng)",
            "desc": "Cửa sổ chatbox nổi FloatingAIBox.tsx hoàn toàn không thực hiện cuộc gọi API tới backend Django /api/ai/chat mà sử dụng hàm giả lập setTimeout(..., 800) với bộ dữ liệu câu trả lời cứng tự sinh.",
            "impact": "Tính năng tra cứu tại widget nổi trở thành tính năng giả lập (mock), không có giá trị nghiệp vụ thực tế.",
            "fix": "Tích hợp hook gọi API backend /api/ai/chat dùng chung với trang AiAssistantPage.",
            "img": "bug_13_floating_ai_mock_timeout_response.png"
        },
        {
            "id": "14",
            "name": "Xung đột mô hình giữa Trang chính (Gemini) và Widget nổi (GPT-4o)",
            "page": "Widget nổi (FloatingAIBox.tsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Trong khi toàn bộ phân hệ Trợ lý AI đang được cấu hình hoạt động trên nền tảng Google Gemini, widget chatbox nổi lại gắn cố định huy hiệu màu tím 'GPT-4o' và xưng danh là 'Trợ Lý AI TLBM (GPT-4o)'.",
            "impact": "Gây mâu thuẫn nhận diện hệ thống và thông tin sai lệch cho người sử dụng.",
            "fix": "Đồng bộ trạng thái mô hình AI đang được kích hoạt từ cấu hình hệ thống.",
            "img": "bug_14_floating_ai_badge_gpt4o_inconsistent.png"
        },
        {
            "id": "15",
            "name": "Floating AI Box không parse Markdown, in thô dấu sao (**)",
            "page": "Widget nổi (FloatingAIBox.tsx)",
            "priority": "Medium (Trung bình)",
            "desc": "Bong bóng tin nhắn của Floating AI Box in trực tiếp các ký tự định dạng markdown như '**Xin chào Quý Cán bộ!**', '**Trợ Lý AI TLBM (GPT-4o)**' thay vì hiển thị dưới dạng chữ in đậm thẩm mỹ.",
            "impact": "Giao diện tin nhắn hiển thị thô ráp, làm giảm trải nghiệm tương tác của người dùng.",
            "fix": "Tích hợp bộ render Markdown (react-markdown) để hiển thị đúng cú pháp in đậm, gạch đầu dòng.",
            "img": "bug_15_floating_ai_raw_markdown_asterisks.png"
        },
    ]

    for bug in detailed_bugs:
        # Title of Bug
        p_btitle = doc.add_paragraph()
        p_btitle.paragraph_format.space_before = Pt(14)
        p_btitle.paragraph_format.space_after = Pt(4)
        r_num = p_btitle.add_run(f"Bug #{bug['id']}: {bug['name']}\n")
        r_num.font.name = "Arial"
        r_num.font.size = Pt(12)
        r_num.font.bold = True
        r_num.font.color.rgb = RGBColor(15, 23, 42)
        
        # Details Box / Paragraph
        p_bdesc = doc.add_paragraph()
        p_bdesc.paragraph_format.space_after = Pt(6)
        
        r1 = p_bdesc.add_run("• Vị trí phát sinh: "); r1.font.bold = True
        p_bdesc.add_run(f"{bug['page']}  |  ")
        r2 = p_bdesc.add_run("Mức độ: "); r2.font.bold = True
        r_pri = p_bdesc.add_run(f"{bug['priority']}\n")
        r_pri.font.bold = True
        if "High" in bug['priority']:
            r_pri.font.color.rgb = RGBColor(220, 38, 38)
        elif "Medium" in bug['priority']:
            r_pri.font.color.rgb = RGBColor(217, 119, 6)
            
        r3 = p_bdesc.add_run("• Mô tả lỗi: "); r3.font.bold = True
        p_bdesc.add_run(f"{bug['desc']}\n")
        
        r4 = p_bdesc.add_run("• Hậu quả: "); r4.font.bold = True
        p_bdesc.add_run(f"{bug['impact']}\n")
        
        r5 = p_bdesc.add_run("• Hướng xử lý: "); r5.font.bold = True
        p_bdesc.add_run(f"{bug['fix']}")
        
        for r in p_bdesc.runs:
            r.font.name = "Arial"
            r.font.size = Pt(9.5)
            
        # Add Image with Arrow
        img_path = os.path.join(QA_DIR, bug['img'])
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(4)
            p_img.paragraph_format.space_after = Pt(10)
            doc.add_picture(img_path, width=Inches(6.2))
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(14)
            r_cap = p_cap.add_run(f"Hình #{bug['id']}: Bằng chứng lỗi - Mũi tên đỏ chỉ trực tiếp vào vị trí lỗi")
            r_cap.font.name = "Arial"
            r_cap.font.size = Pt(8.5)
            r_cap.font.italic = True
            r_cap.font.color.rgb = RGBColor(100, 116, 139)

    # Save to workspace
    doc.save(WORKSPACE_DOCX)
    print(f"Saved workspace file: {WORKSPACE_DOCX}")
    
    # Copy to Desktop
    try:
        shutil.copy2(WORKSPACE_DOCX, DESKTOP_DOCX)
        print(f"Successfully saved to Desktop: {DESKTOP_DOCX}")
    except PermissionError:
        alt_desktop = os.path.join(DESKTOP_PATH, "Bao_Cao_Kiem_Thu_Bug_Nhom_8_v2.docx")
        shutil.copy2(WORKSPACE_DOCX, alt_desktop)
        print(f"Original file is currently open in Word. Saved updated copy to Desktop as: {alt_desktop}")

if __name__ == "__main__":
    create_word_report()
