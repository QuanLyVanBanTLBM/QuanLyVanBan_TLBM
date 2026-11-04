import os
import math
from PIL import Image, ImageDraw

ROOT_DIR = r"d:\QuanLyVanBan_TLBM"
QA_DIR = os.path.join(ROOT_DIR, "docs", "qa", "nhom_8")
TEMP_DIR = r"C:\Users\admi\.gemini\antigravity-ide\brain\fbaef7a3-0f75-4ed9-891e-3f2d394c4d7a\.tempmediaStorage"

os.makedirs(QA_DIR, exist_ok=True)

# Exact Lightshot red color
RED = (240, 10, 10)

def draw_arrow(draw, start, end, color=RED, width=3, head_length=22, head_angle=24):
    x1, y1 = start
    x2, y2 = end
    angle = math.atan2(y2 - y1, x2 - x1)
    base_x = x2 - head_length * 0.7 * math.cos(angle)
    base_y = y2 - head_length * 0.7 * math.sin(angle)
    draw.line([(x1, y1), (base_x, base_y)], fill=color, width=width)
    rad = math.radians(head_angle)
    x3 = x2 - head_length * math.cos(angle - rad)
    y3 = y2 - head_length * math.sin(angle - rad)
    x4 = x2 - head_length * math.cos(angle + rad)
    y4 = y2 - head_length * math.sin(angle + rad)
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)

import numpy as np

def remove_blue_border(im, border_width=36):
    arr = np.array(im.convert('RGB'), dtype=np.float32)
    h, w, _ = arr.shape
    dist_x = np.minimum(np.arange(w), w - 1 - np.arange(w))
    dist_y = np.minimum(np.arange(h), h - 1 - np.arange(h))
    dist_matrix = np.minimum(dist_x[None, :], dist_y[:, None])
    
    # Weight: 1.0 at border (dist=0) down to 0.0 at dist=border_width
    weight = np.clip((border_width - dist_matrix) / border_width, 0.0, 1.0)
    
    # Where B > (R + G) / 2 (blue-tinted glow), reduce B towards (R + G) / 2
    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    neutral_b = (r + g) / 2.0
    
    diff = np.maximum(b - neutral_b, 0.0)
    new_b = b - diff * weight
    new_r = r + (diff * 0.5) * weight
    new_g = g + (diff * 0.2) * weight
    
    arr_out = np.stack([new_r, new_g, new_b], axis=-1)
    arr_out = np.clip(arr_out, 0, 255).astype(np.uint8)
    return Image.fromarray(arr_out)

def generate_bug_image(source_filename, output_filename, arrow_start, arrow_end):
    src_path = os.path.join(TEMP_DIR, source_filename)
    out_path = os.path.join(QA_DIR, output_filename)
    im = Image.open(src_path).convert("RGB")
    im = remove_blue_border(im, 36)
    draw = ImageDraw.Draw(im)
    draw_arrow(draw, arrow_start, arrow_end, color=RED, width=3, head_length=22)
    im.save(out_path, quality=95)
    print(f"Generated: {output_filename}")
    return out_path

# Definition of exactly 15 bugs with 1-to-1 arrow targeting
BUGS = [
    # 1. Bug 1: Lỗi 403 API in trực tiếp chuỗi kỹ thuật thô vào bong bóng chat
    {
        "file": "bug_01_chat_error_403.png",
        "src": "media_1792838995873.png",
        "start": (550, 520),
        "end": (745, 575),
    },
    # 2. Bug 2: Badge hiển thị mô hình AI ảo gemini-3.8-flash ở header
    {
        "file": "bug_02_model_gemini_fake.png",
        "src": "media_1792838995873.png",
        "start": (1320, 55),
        "end": (1500, 78),
    },
    # 3. Bug 3: Giao diện chọn EN nhưng lời chào vẫn 100% tiếng Việt
    {
        "file": "bug_03_i18n_greeting_vietnamese.png",
        "src": "media_1792838995873.png",
        "start": (620, 160),
        "end": (750, 185),
    },
    # 4. Bug 4: Chip gợi ý đề cập sai quy chuẩn ký số "Token PKI" (hệ thống dùng Ed25519 nội bộ)
    {
        "file": "bug_04_chip_token_pki_wrong_spec.png",
        "src": "media_1792838995873.png",
        "start": (620, 340),
        "end": (750, 340),
    },
    # 5. Bug 5: Chữ dính liền "Google GeminiKhuyên dùng" trong modal Cài đặt AI
    {
        "file": "bug_05_settings_glued_gemini.png",
        "src": "media_1792838883100.png",
        "start": (460, 420),
        "end": (660, 442),
    },
    # 6. Bug 6: Chữ dính liền "OpenAIGPT-4o" trong modal Cài đặt AI
    {
        "file": "bug_06_settings_glued_openai.png",
        "src": "media_1792838883100.png",
        "start": (460, 558),
        "end": (630, 558),
    },
    # 7. Bug 7: Dropdown chọn mô hình LLM chứa model ảo gemini-3.8-flash
    {
        "file": "bug_07_settings_dropdown_fake_gemini_38.png",
        "src": "media_1792838883100.png",
        "start": (1260, 740),
        "end": (1095, 740),
    },
    # 8. Bug 8: Ô chọn "Mô hình Vector Embedding" bị tràn viền và cắt cụt văn bản
    {
        "file": "bug_08_settings_embedding_text_overflow.png",
        "src": "media_1792838883100.png",
        "start": (1200, 766),
        "end": (995, 766),
    },
    # 9. Bug 9: Header Modal Cài đặt AI dùng màu tím #4338ca vi phạm Design Tokens
    {
        "file": "bug_09_settings_header_color_token_violation.png",
        "src": "media_1792838883100.png",
        "start": (400, 200),
        "end": (545, 235),
    },
    # 10. Bug 10: Cây thư mục Kho tài liệu AI hiển thị mock data (folder1, folder2, item1.docx)
    {
        "file": "bug_10_kho_tai_lieu_mock_data_tree.png",
        "src": "media_1792838906231.png",
        "start": (380, 390),
        "end": (180, 420),
    },
    # 11. Bug 11: Nút "Xóa toàn bộ kho tài liệu" nguy hiểm, thiếu bước xác nhận an toàn
    {
        "file": "bug_11_kho_tai_lieu_dangerous_delete_all.png",
        "src": "media_1792838906231.png",
        "start": (380, 738),
        "end": (210, 738),
    },
    # 12. Bug 12: Nút robot nổi Floating Chat Widget đè lên thanh navbar bên trái
    {
        "file": "bug_12_floating_robot_overlap_navbar.png",
        "src": "media_1792838906231.png",
        "start": (180, 790),
        "end": (55, 770),
    },
    # 13. Bug 13: Floating AI Box dùng hàm mock setTimeout(800) không gọi API backend
    {
        "file": "bug_13_floating_ai_mock_timeout_response.png",
        "src": "media_1792839028099.png",
        "start": (1450, 540),
        "end": (1630, 540),
    },
    # 14. Bug 14: Xung đột mô hình: Trang chính chạy Gemini nhưng Floating Chat gắn badge GPT-4o
    {
        "file": "bug_14_floating_ai_badge_gpt4o_inconsistent.png",
        "src": "media_1792839028099.png",
        "start": (1500, 400),
        "end": (1680, 425),
    },
    # 15. Bug 15: Tin nhắn trong Floating AI Chatbox không parse Markdown, in thô dấu **
    {
        "file": "bug_15_floating_ai_raw_markdown_asterisks.png",
        "src": "media_1792839028099.png",
        "start": (1400, 495),
        "end": (1570, 495),
    },
]

if __name__ == "__main__":
    for b in BUGS:
        generate_bug_image(b["src"], b["file"], b["start"], b["end"])
    print(f"\nSuccessfully generated {len(BUGS)} separate bug screenshots with arrow-only annotations!")
