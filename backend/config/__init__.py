import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_DIR = Path(__file__).resolve().parents[2]

# Server đặt AI_DATA_DIR ra thư mục dùng chung để tài liệu/vector store không nằm trong thư mục release.
DATA_DIR = Path(os.getenv("AI_DATA_DIR") or BASE_DIR / "data")
DOCS_DIR = DATA_DIR / "docs"
CHROMA_DIR = DATA_DIR / "chroma_db"
DOC_REGISTRY_PATH = DATA_DIR / "doc_registry.json"
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "smart_documents")

MODEL_PROVIDER = "openai"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBED_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-6-luna"
VISION_MODEL = LLM_MODEL

# Load persisted AI settings from DATA_DIR if present across workers/restarts
_settings_file = DATA_DIR / "ai_settings.json"
if _settings_file.exists():
    try:
        import json as _json
        _stored = _json.loads(_settings_file.read_text(encoding="utf-8"))
        if isinstance(_stored, dict):
            if _stored.get("openai_api_key"):
                OPENAI_API_KEY = _stored["openai_api_key"]
                os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    except Exception:
        pass

VISION_OCR_ENABLED = os.getenv("VISION_OCR_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
# VISION_OCR_MODE: "all" | "fallback" | "math" | "off"
#   all      - luôn chạy Vision OCR cho mọi trang (chậm)
#   math     - luôn chạy Vision OCR, dùng prompt chuyên biệt cho toán/hình học (chậm)
#   fallback - chỉ chạy khi pdfplumber không đọc được text tốt (KHUYẾN NGHỊ)
#   off      - tắt Vision OCR hoàn toàn
VISION_OCR_MODE = os.getenv("VISION_OCR_MODE", "fallback").lower()

# Tăng DPI lên 150 để đọc rõ ký tự toán và hình vẽ (mặc định cũ là 72 - quá thấp)
VISION_OCR_PDF_DPI = int(os.getenv("VISION_OCR_PDF_DPI", "150"))
VISION_OCR_TIMEOUT = float(os.getenv("VISION_OCR_TIMEOUT", "60"))

# Tăng kích thước ảnh tối đa để giữ chi tiết công thức/hình học
VISION_OCR_MAX_IMAGE_SIZE = int(os.getenv("VISION_OCR_MAX_IMAGE_SIZE", "1024"))

# Tăng chất lượng JPEG để không bị mờ ký tự nhỏ trong công thức
VISION_OCR_JPEG_QUALITY = int(os.getenv("VISION_OCR_JPEG_QUALITY", "90"))
VISION_OCR_PARALLEL_WORKERS = int(os.getenv("VISION_OCR_PARALLEL_WORKERS", "3"))

SIMILARITY_TOP_K = 6

ALLOWED_EXTENSIONS = (
    ".pdf", ".docx", ".txt",
    ".csv",
    ".pptx",
    ".md", ".markdown",
    ".html", ".htm",
    ".json",
    ".xml",
# Image OCR uses OpenAI gpt-6-luna Vision
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif",
)

PARENT_CHUNK_SIZE = 1500
PARENT_CHUNK_OVERLAP = 300
CHILD_CHUNK_SIZE = 300
CHILD_CHUNK_OVERLAP = 50
SOURCE_SCORE_THRESHOLD = 0.15

CHAT_HISTORY_MAX_TURNS = int(os.getenv("CHAT_HISTORY_MAX_TURNS", "4"))
CHAT_HISTORY_MAX_CHARS = int(os.getenv("CHAT_HISTORY_MAX_CHARS", "800"))

try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    celery_app = None
    __all__ = ()
