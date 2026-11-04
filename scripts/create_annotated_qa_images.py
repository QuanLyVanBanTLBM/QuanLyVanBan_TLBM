import os
from PIL import Image, ImageDraw, ImageFont

ARTIFACT_DIR = r"C:\Users\admi\.gemini\antigravity-ide\brain\fbaef7a3-0f75-4ed9-891e-3f2d394c4d7a"
TEMP_DIR = os.path.join(ARTIFACT_DIR, ".tempmediaStorage")

FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
FONT_REG_PATH = "C:/Windows/Fonts/arial.ttf"

def get_fonts():
    try:
        f_title = ImageFont.truetype(FONT_PATH, 16)
        f_body = ImageFont.truetype(FONT_REG_PATH, 14)
        f_badge = ImageFont.truetype(FONT_PATH, 14)
        f_header = ImageFont.truetype(FONT_PATH, 18)
    except Exception:
        f_title = ImageFont.load_default()
        f_body = ImageFont.load_default()
        f_badge = ImageFont.load_default()
        f_header = ImageFont.load_default()
    return f_title, f_body, f_badge, f_header

f_title, f_body, f_badge, f_header = get_fonts()

def draw_callout(draw, box, text_lines, badge_num=None, align_pos='bottom', line_to=None):
    BORDER_COLOR = (220, 38, 38)     # Bright Red
    BG_COLOR = (254, 242, 242)        # Light Red Tint
    TEXT_COLOR = (153, 27, 27)        # Dark Red Text
    HEADER_BG = (220, 38, 38)         # Solid Red for badge/header
    WHITE = (255, 255, 255)

    x1, y1, x2, y2 = box

    # 1. Bounding box (3px thickness)
    for i in range(3):
        draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=BORDER_COLOR)

    # 2. Numbered badge
    if badge_num is not None:
        badge_r = 13
        bx, by = x1 - 8, y1 - 8
        draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r], fill=HEADER_BG, outline=WHITE, width=2)
        draw.text((bx - 4, by - 8), str(badge_num), fill=WHITE, font=f_badge)

    # 3. Callout Box
    line_h = 20
    pad_x = 12
    pad_y = 10
    max_w = max(draw.textbbox((0, 0), line, font=f_body)[2] for line in text_lines)
    box_w = max_w + pad_x * 2
    box_h = len(text_lines) * line_h + pad_y * 2

    if isinstance(align_pos, tuple):
        cx1, cy1 = align_pos
    elif align_pos == 'bottom':
        cx1 = max(10, min(x1, 1920 - box_w - 20))
        cy1 = y2 + 15
    elif align_pos == 'top':
        cx1 = max(10, min(x1, 1920 - box_w - 20))
        cy1 = max(10, y1 - box_h - 15)
    elif align_pos == 'left':
        cx1 = max(10, x1 - box_w - 20)
        cy1 = y1
    elif align_pos == 'right':
        cx1 = min(1920 - box_w - 20, x2 + 20)
        cy1 = y1

    cx2 = cx1 + box_w
    cy2 = cy1 + box_h

    if line_to:
        px, py = line_to
    else:
        px, py = (x1 + x2) // 2, (y1 + y2) // 2
    
    c_anchor_x = (cx1 + cx2) // 2
    c_anchor_y = cy1 if cy1 > py else cy2
    draw.line([(px, py), (c_anchor_x, c_anchor_y)], fill=BORDER_COLOR, width=2)
    draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=BORDER_COLOR)

    # Background & border
    draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=6, fill=BG_COLOR, outline=BORDER_COLOR, width=2)

    # Text lines
    curr_y = cy1 + pad_y
    for idx, line in enumerate(text_lines):
        font = f_title if idx == 0 else f_body
        draw.text((cx1 + pad_x, curr_y), line, fill=TEXT_COLOR, font=font)
        curr_y += line_h

def annotate_image_1():
    img_path = os.path.join(TEMP_DIR, "media_1792838995873.png")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Defect 1: Raw backend error bubble "Thiếu cấu hình kết nối CSDL chỉ đọc cho AI."
    draw_callout(
        draw,
        box=(740, 560, 1055, 622),
        text_lines=[
            "[LỖI 1 - HIGH] Trả về chuỗi lỗi kỹ thuật HTTP 403 raw vào bóng chat",
            "• Nguyên nhân: Backend thiếu biến môi trường DB_READONLY_USER trong .env.",
            "• Hiện tượng: Chatbot in trực tiếp raw JSON: 'Thiếu cấu hình kết nối CSDL chỉ đọc cho AI.'",
            "• Yêu cầu: Bắt lỗi graceful, hiển thị Toast cảnh báo thay vì in lỗi thô vào tin nhắn người dùng."
        ],
        badge_num=1,
        align_pos=(280, 520),
        line_to=(740, 590)
    )

    # Defect 2: Fake Gemini Model "gemini-3.8-flash"
    draw_callout(
        draw,
        box=(1500, 65, 1690, 95),
        text_lines=[
            "[LỖI 2 - HIGH] Mô hình 'gemini-3.8-flash' không tồn tại trên Google Gemini API",
            "• Cả frontend và backend đều đặt cứng mô hình ảo 'gemini-3.8-flash'.",
            "• Google Gemini chính thức chỉ có: gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro.",
            "• Yêu cầu: Đổi cấu hình mặc định về model chính thức để tránh 404/Fail khi gọi API thật."
        ],
        badge_num=2,
        align_pos=(880, 50),
        line_to=(1500, 80)
    )

    # Defect 3: i18n failure (EN chosen, but VN shown) + Token PKI violation
    draw_callout(
        draw,
        box=(735, 155, 1460, 368),
        text_lines=[
            "[LỖI 3 - MEDIUM] Không hỗ trợ i18n khi chọn Tiếng Anh (EN) & Sai chuẩn ký số",
            "• Người dùng đang chọn cờ 'EN', nhưng toàn bộ lời chào và 4 thẻ gợi ý vẫn hiển thị 100% Tiếng Việt.",
            "• Thẻ 'Hướng dẫn ký số điện tử token PKI' vi phạm quy chuẩn (hệ thống TLBM dùng chữ ký số Ed25519 nội bộ).",
            "• Yêu cầu: Dùng t('aiAssistant...') cho toàn bộ lời chào; xóa bỏ nội dung Token PKI/HSM theo spec."
        ],
        badge_num=3,
        align_pos=(280, 200),
        line_to=(735, 260)
    )

    # Highlight language badge EN
    for i in range(2):
        draw.rectangle([1685 - i, 16 - i, 1720 + i, 38 + i], outline=(37, 99, 235))
    draw.line([(1685, 27), (1550, 27)], fill=(37, 99, 235), width=2)
    draw.text((1350, 18), "Ngôn ngữ đang chọn: EN ->", fill=(37, 99, 235), font=f_badge)

    out_path = os.path.join(ARTIFACT_DIR, "qa_bug_01_chat_error_and_i18n.png")
    im.save(out_path, "PNG")
    print("Saved:", out_path)

def annotate_image_2():
    img_path = os.path.join(TEMP_DIR, "media_1792838883100.png")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Defect 1: Glued text Google GeminiKhuyên dùng
    draw_callout(
        draw,
        box=(575, 435, 750, 460),
        text_lines=[
            "[LỖI 1 - MEDIUM] Lỗi dính chữ giữa nhãn 'Google Gemini' và Badge 'Khuyên dùng'",
            "• Hiển thị: 'Google GeminiKhuyên dùng' (dính liền không có dấu cách).",
            "• File: frontend/src/components/AISettingsModal.jsx."
        ],
        badge_num=1,
        align_pos=(80, 420),
        line_to=(575, 447)
    )

    # Defect 2: Glued text OpenAI
    draw_callout(
        draw,
        box=(575, 552, 795, 578),
        text_lines=[
            "[LỖI 2 - MEDIUM] Lỗi dính chữ 'OpenAIGPT-4o / GPT-4o-mini'",
            "• Hiển thị: 'OpenAIGPT-4o' dính liền tên hãng và model.",
            "• File: frontend/src/components/AISettingsModal.jsx."
        ],
        badge_num=2,
        align_pos=(80, 540),
        line_to=(575, 565)
    )

    # Defect 3: Truncated Embedding Model
    draw_callout(
        draw,
        box=(575, 750, 975, 770),
        text_lines=[
            "[LỖI 3 - MEDIUM] Lỗi tràn viền & cắt cụt text ô Mô hình Vector Embedding",
            "• Hiển thị: 'Mô hình Vector Embedding:models/gemini-embedding-0' bị cắt xén viền phải.",
            "• Chiều rộng khung input/select bị tràn ra ngoài viền modal.",
            "• Cần căn chỉnh flex/grid và đặt max-width responsive."
        ],
        badge_num=3,
        align_pos=(80, 720),
        line_to=(575, 760)
    )

    # Defect 4: Model gemini-3.8-flash in dropdown
    draw_callout(
        draw,
        box=(775, 730, 1175, 755),
        text_lines=[
            "[LỖI 4 - HIGH] Dropdown chứa mô hình ảo 'gemini-3.8-flash (Khuyên dùng - Nhanh & Mới nhất)'",
            "• Người dùng chọn mô hình này sẽ khiến việc gọi Gemini API thất bại hoàn toàn.",
            "• Cần cập nhật danh sách model chính thức: gemini-1.5-flash, gemini-2.0-flash."
        ],
        badge_num=4,
        align_pos=(1220, 710),
        line_to=(1175, 742)
    )

    # Defect 5: Design Token Header
    draw_callout(
        draw,
        box=(550, 175, 1370, 275),
        text_lines=[
            "[LỖI 5 - LOW] Header modal dùng màu tím cứng (#4338ca) vi phạm CSS Design Tokens",
            "• Vi phạm quy chuẩn Design Tokens (AGENTS.md mục 4): Bắt buộc dùng var(--color-brand-...)",
            "• Không tương thích với chế độ Dark/Light của hệ thống."
        ],
        badge_num=5,
        align_pos=(1220, 210),
        line_to=(1370, 225)
    )

    out_path = os.path.join(ARTIFACT_DIR, "qa_bug_02_settings_modal_defects.png")
    im.save(out_path, "PNG")
    print("Saved:", out_path)

def annotate_image_3():
    img_path = os.path.join(TEMP_DIR, "media_1792838906231.png")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Defect 1: Mock folders item1.docx
    draw_callout(
        draw,
        box=(85, 320, 350, 690),
        text_lines=[
            "[LỖI 1 - MEDIUM] Cây thư mục hiển thị dữ liệu mẫu giả định (Dummy Mock Data)",
            "• Các thư mục hiển thị: 'folder1', 'folder2' với tệp lặp lại 'item1.docx', 'item2.docx', 'item3.docx'.",
            "• Logic phân cấp thư mục bị fallback vào mock data thay vì lấy danh mục và tài liệu thật.",
            "• Yêu cầu: Đồng bộ đúng cấu trúc thư mục thật từ API /api/ai/documents."
        ],
        badge_num=1,
        align_pos=(380, 420),
        line_to=(350, 505)
    )

    # Defect 2: Clear all docs dangerous button
    draw_callout(
        draw,
        box=(85, 706, 350, 742),
        text_lines=[
            "[LỖI 2 - HIGH] Nút 'Xóa toàn bộ kho tài liệu' nguy hiểm và thiếu bảo vệ RBAC",
            "• Thao tác hủy diệt (DELETE /api/ai/documents) xóa sạch ChromaDB và toàn bộ tệp.",
            "• Yêu cầu: Bắt buộc ẩn với user thường, chỉ superuser mới thấy và phải có xác nhận gõ chữ 'DELETE'."
        ],
        badge_num=2,
        align_pos=(380, 690),
        line_to=(350, 724)
    )

    # Defect 3: Overlapping Robot icon on left navbar
    draw_callout(
        draw,
        box=(15, 740, 58, 785),
        text_lines=[
            "[LỖI 3 - MEDIUM] Biểu tượng AI tròn xanh nằm đè lên thanh Menu điều hướng",
            "• Icon robot cố định ở góc trái che mất các vị trí menu cuối cùng của Sidebar chính.",
            "• Gây xung đột thao tác click và vỡ bố cục tổng thể."
        ],
        badge_num=3,
        align_pos=(80, 780),
        line_to=(58, 762)
    )

    out_path = os.path.join(ARTIFACT_DIR, "qa_bug_03_document_repository_mock.png")
    im.save(out_path, "PNG")
    print("Saved:", out_path)

def annotate_image_4():
    img_path = os.path.join(TEMP_DIR, "media_1792839028099.png")
    im = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # Defect 1: Inconsistent Model Badge GPT-4o
    draw_callout(
        draw,
        box=(1675, 416, 1725, 440),
        text_lines=[
            "[LỖI 1 - MEDIUM] Xung đột cấu hình mô hình (Trang chính Gemini, Widget lại ghi GPT-4o)",
            "• Module AI chính đang chạy Google Gemini, nhưng Floating Widget lại ghi cứng badge 'GPT-4o'.",
            "• Gây hiểu nhầm cho người dùng về mô hình đang vận hành hệ thống."
        ],
        badge_num=1,
        align_pos=(980, 385),
        line_to=(1675, 428)
    )

    # Defect 2: Raw Markdown Asterisks
    draw_callout(
        draw,
        box=(1550, 470, 1860, 585),
        text_lines=[
            "[LỖI 2 - LOW] Lỗi hiển thị: Không parse Markdown, in thô dấu sao (**)",
            "• Tin nhắn bot hiển thị: '**Xin chào Quý Cán bộ!** Tôi là **Trợ Lý AI TLBM (GPT-4o)**...'",
            "• Thiếu bộ phân tích Markdown cho component FloatingAIBox.tsx."
        ],
        badge_num=2,
        align_pos=(1000, 480),
        line_to=(1550, 520)
    )

    # Defect 3: Mock Data & Obsolete Spec (Token PKI / HSM)
    draw_callout(
        draw,
        box=(1550, 595, 1860, 720),
        text_lines=[
            "[LỖI 3 - HIGH] Widget AI nổi dùng hàm MOCK (setTimeout) và trả lời SAI nghiệp vụ ký số",
            "• FloatingAIBox.tsx không hề gọi backend /api/ai/chat mà tự bịa câu trả lời bằng hàm mock.",
            "• Trả lời: 'Lãnh đạo xác thực ký số điện tử (USB Token / Cloud HSM)' -> SAI HOÀN TOÀN quy chuẩn,",
            "  hệ thống TLBM chỉ dùng chữ ký số nội bộ Ed25519 và tuyệt đối cấm mô tả Token PKI / Cloud HSM.",
            "• Vi phạm quy tắc AGENTS.md mục 6: 'Không dùng dữ liệu mock thay backend thật trên route chính thức'."
        ],
        badge_num=3,
        align_pos=(880, 620),
        line_to=(1550, 650)
    )

    # Defect 4: Zero i18n support
    draw_callout(
        draw,
        box=(1510, 405, 1890, 935),
        text_lines=[
            "[LỖI 4 - MEDIUM] Toàn bộ Widget Floating AI Box không hỗ trợ đa ngôn ngữ (i18n = 0%)",
            "• Trang chủ Dashboard đang chọn tiếng Anh (EN), nhưng widget AI nổi 100% tiếng Việt hardcode.",
            "• Placeholder: 'Hỏi trợ lý AI về văn bản...', nút gợi ý, tiêu đề đều không qua t('...')."
        ],
        badge_num=4,
        align_pos=(980, 810),
        line_to=(1510, 870)
    )

    out_path = os.path.join(ARTIFACT_DIR, "qa_bug_04_floating_ai_mock_and_markdown.png")
    im.save(out_path, "PNG")
    print("Saved:", out_path)

if __name__ == "__main__":
    annotate_image_1()
    annotate_image_2()
    annotate_image_3()
    annotate_image_4()
    print("Regenerated all 4 QA bug annotated screenshots successfully!")
