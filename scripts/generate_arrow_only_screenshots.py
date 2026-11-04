import os
import math
from PIL import Image, ImageDraw

ROOT_DIR = r"d:\QuanLyVanBan_TLBM"
QA_DIR = os.path.join(ROOT_DIR, "docs", "qa", "nhom_8")
TEMP_DIR = r"C:\Users\admi\.gemini\antigravity-ide\brain\fbaef7a3-0f75-4ed9-891e-3f2d394c4d7a\.tempmediaStorage"

os.makedirs(QA_DIR, exist_ok=True)

# Exact Lightshot red color
RED = (240, 10, 10)

def draw_arrow(draw, start, end, color=RED, width=4, head_length=24, head_angle=24):
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

# 1. Bug: Chat Error 403 Raw JSON
def make_bug_01():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838995873.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing directly to "Thiếu cấu hình kết nối CSDL chỉ đọc cho AI."
    draw_arrow(draw, (550, 520), (745, 575), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_01_chat_error_403.png")
    im.save(out)
    print("Saved:", out)

# 2. Bug: Fake Gemini Model gemini-3.8-flash
def make_bug_02():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838995873.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing to "gemini | gemini-3.8-flash" badge
    draw_arrow(draw, (1320, 55), (1500, 78), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_02_model_gemini_fake.png")
    im.save(out)
    print("Saved:", out)

# 3. Bug: Settings Modal Glued Text (Google GeminiKhuyên dùng & OpenAIGPT-4o)
def make_bug_03():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838883100.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing directly to glued "Google GeminiKhuyên dùng"
    draw_arrow(draw, (460, 420), (660, 442), width=3, head_length=22)
    # Arrow pointing directly to glued "OpenAIGPT-4o"
    draw_arrow(draw, (460, 540), (620, 555), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_03_settings_dinh_chu.png")
    im.save(out)
    print("Saved:", out)

# 4. Bug: Settings Modal Truncated Text & Fake Model Dropdown
def make_bug_04():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838883100.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing to fake model gemini-3.8-flash in dropdown
    draw_arrow(draw, (1260, 712), (1095, 712), width=3, head_length=22)
    # Arrow pointing to truncated embedding select box
    draw_arrow(draw, (1200, 770), (995, 738), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_04_settings_tran_vien.png")
    im.save(out)
    print("Saved:", out)

# 5. Bug: Kho tài liệu Mock Dummy Data & Xóa toàn bộ & Overlap icon
def make_bug_05():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838906231.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing to folder1/folder2/item1.docx tree
    draw_arrow(draw, (380, 390), (180, 420), width=3, head_length=22)
    # Arrow pointing to [Xóa toàn bộ kho tài liệu]
    draw_arrow(draw, (380, 738), (210, 738), width=3, head_length=22)
    # Arrow pointing to blue robot icon on navbar
    draw_arrow(draw, (180, 790), (55, 770), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_05_kho_tai_lieu_mock_data.png")
    im.save(out)
    print("Saved:", out)

# 6. Bug: Floating AI Box Markdown Asterisks, Mock setTimeout, Inconsistent GPT-4o Badge
def make_bug_06():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792839028099.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing to badge GPT-4o
    draw_arrow(draw, (1500, 400), (1680, 425), width=3, head_length=22)
    # Arrow pointing to raw markdown asterisks **Xin chào...**
    draw_arrow(draw, (1400, 495), (1570, 495), width=3, head_length=22)
    # Arrow pointing to quick suggestions / mock responses
    draw_arrow(draw, (1400, 640), (1570, 640), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_06_floating_ai_mock_and_markdown.png")
    im.save(out)
    print("Saved:", out)

# 7. Bug: i18n Failure (EN selected, VN shown)
def make_bug_07():
    im = Image.open(os.path.join(TEMP_DIR, "media_1792838995873.png")).convert("RGB")
    draw = ImageDraw.Draw(im)
    # Arrow pointing to Language toggle EN
    draw_arrow(draw, (1580, 27), (1720, 27), width=3, head_length=22)
    # Arrow pointing to welcome title in VN
    draw_arrow(draw, (620, 160), (750, 185), width=3, head_length=22)
    # Arrow pointing to prompt "Hướng dẫn ký số điện tử token PKI?"
    draw_arrow(draw, (620, 340), (750, 340), width=3, head_length=22)
    out = os.path.join(QA_DIR, "bug_07_i18n_tieng_anh.png")
    im.save(out)
    print("Saved:", out)

if __name__ == "__main__":
    make_bug_01()
    make_bug_02()
    make_bug_03()
    make_bug_04()
    make_bug_05()
    make_bug_06()
    make_bug_07()
    print("All arrow-only screenshots generated successfully!")
