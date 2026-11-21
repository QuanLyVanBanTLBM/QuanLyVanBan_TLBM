"""Searchable business scope notes derived from repository branches 1 through 7.

These cards describe module intent only. They are not a source of live records,
counts, permissions, or workflow state.
"""

import re
import unicodedata


MODULES = [
    {
        "code": "branch-00-overview",
        "title": "Tong quan he thong QLVB va TLBM (8 phan he)",
        "phrases": (
            "he thong", "ho tro", "phan he", "tong quan", "chuc nang", "tlbm", "qlvb",
            "tro ly ai", "ai assistant", "overview", "modules",
        ),
        "content": (
            "Hệ thống Quản lý Văn bản & Tài liệu Bảo mật (TLBM) hỗ trợ 8 phân hệ chính: "
            "(1) Trang chủ / Dashboard tổng hợp số liệu, lịch họp và việc cần xử lý (/dashboard); "
            "(2) Quản lý văn bản đến, văn bản đi và văn bản mật (/documents); "
            "(3) Hồ sơ công việc & danh mục loại văn bản; "
            "(4) Kho tài liệu dùng chung & biểu mẫu nội bộ (/resources); "
            "(5) Trình ký và ký số điện tử kèm xác thực PIN/SMS OTP; "
            "(6) Giao việc, xử lý và theo dõi tiến độ công việc; "
            "(7) Quản trị hệ thống, cơ cấu tổ chức, phân quyền RBAC, đặt phòng họp, sự kiện và sinh nhật; "
            "(8) Trợ lý AI Chatbox tra cứu văn bản và quy trình (/ai-assistant). "
            "Số liệu thực tế của từng phân hệ phải lấy từ dữ liệu được cấp quyền trong ứng dụng."
        ),
    },
    {
        "code": "branch-01-dashboard",
        "title": "Nhanh 1 - Dashboard va tong quan",
        "phrases": (
            "dashboard", "trang chu", "tong quan", "thong ke", "viec can xu ly",
            "lich hop", "sinh nhat",
        ),
        "content": (
            "Phân hệ Dashboard tổng hợp nhanh văn bản đến/đi, hồ sơ chờ trình ký/phê duyệt, công việc được giao hoặc quá hạn, "
            "lịch họp, sự kiện và sinh nhật trong ngày (/dashboard). "
            "Branch 1 describes a dashboard summarizing incoming/outgoing documents, pending approvals, tasks, meetings, and birthdays. "
            "Số liệu hiển thị phụ thuộc vào dữ liệu thực tế mà tài khoản được quyền xem."
        ),
    },
    {
        "code": "branch-02-documents",
        "title": "Nhanh 2 - Quan ly van ban den, di va mat",
        "phrases": (
            "van ban den", "van ban di", "van ban mat", "van ban", "tiep nhan",
            "vao so", "cap so", "phan phoi", "xu ly", "ban hanh", "phat hanh",
            "pham vi", "noi bo", "han che", "phan loai", "quyen truy cap",
            "incoming document", "outgoing document",
        ),
        "content": (
            "Phân hệ Quản lý Văn bản bao gồm văn bản đến, văn bản đi và văn bản mật (/documents): "
            "Quy trình tiếp nhận và xử lý văn bản đến gồm các bước: (1) Tiếp nhận văn bản & kiểm tra thể thức, đính kèm; "
            "(2) Vào sổ đăng ký, cấp số thứ tự đến và cập nhật trích yếu/hiệu lực; (3) Trình lãnh đạo xem xét, phân phối về đơn vị/người xử lý; "
            "(4) Thực hiện xử lý, cập nhật tiến độ và lưu hồ sơ. "
            "Văn bản đi đi qua các bước dự thảo, duyệt nội dung, cấp số phát hành và ban hành. "
            "Về phân loại và phạm vi truy cập: văn bản phạm vi nội bộ (NOI_BO) phục vụ tra cứu đúng đối tượng/đơn vị, "
            "còn văn bản mật/hạn chế (HAN_CHE) áp dụng kiểm soát quyền xem nghiêm ngặt và tự động loại trừ khỏi chỉ mục AI. "
            "Chi tiết từng văn bản cụ thể phải tra cứu từ bản ghi SQL được cấp quyền."
        ),
    },
    {
        "code": "branch-03-records",
        "title": "Nhanh 3 - Ho so, loai van ban va quyen truy cap tai lieu",
        "phrases": (
            "ho so", "loai van ban", "phan loai", "quyen truy cap", "tai lieu",
            "thoi han bao quan", "nop luu", "luu tru", "case file",
        ),
        "content": (
            "Phân hệ Hồ sơ & Loại văn bản quản lý danh mục loại văn bản, lập hồ sơ công việc, gom văn bản vào hồ sơ, "
            "theo dõi thời hạn bảo quản, đóng/mở hồ sơ và nộp lưu trữ. "
            "Tài liệu và hồ sơ được phân loại theo danh mục loại văn bản và mức độ hiển thị / quyền truy cập "
            "(TAT_CA cho toàn đơn vị, NOI_BO_PHONG_BAN cho phạm vi phòng ban, đồng thời kiểm tra quyền xem tài liệu và hiệu lực văn bản). "
            "Trạng thái hoặc thời hạn bảo quản của một hồ sơ cụ thể phải tra cứu từ dữ liệu ứng dụng."
        ),
    },
    {
        "code": "branch-04-templates",
        "title": "Nhanh 4 - Tai lieu dung chung va bieu mau",
        "phrases": (
            "bieu mau", "tai lieu dung chung", "tai lieu noi bo", "tai lieu",
            "noi bo", "kho tai lieu", "tai xuong", "template", "resources",
        ),
        "content": (
            "Phân hệ Tài liệu dùng chung & Biểu mẫu chuẩn nằm tại mục [Kho Tài Liệu & Biểu Mẫu](/resources), "
            "nơi lưu trữ tài liệu nội bộ, quy chế, hướng dẫn và các biểu mẫu chuẩn phân loại theo phòng ban/lĩnh vực "
            "với tệp tải xuống định dạng DOCX, XLSX hoặc PDF. "
            "Branch 4 covers shared resources and templates in [Kho Tài Liệu & Biểu Mẫu](/resources), categorized by department or field. "
            "Danh mục tệp tải xuống thực tế cần kiểm tra trực tiếp trên trang kho tài liệu."
        ),
    },
    {
        "code": "branch-05-signing",
        "title": "Nhanh 5 - Quy trinh trinh ky, ky so va PIN SMS OTP",
        "phrases": (
            "trinh ky", "ky so", "ky duyet", "chu ky", "tao pin", "ma pin",
            "dat lai pin", "sms otp", "otp", "sms", "pin", "sha256", "phe duyet",
        ),
        "content": (
            "Phân hệ Trình ký & Ký số hỗ trợ luồng phê duyệt nhiều cấp theo thứ tự người ký, thiết lập độ khẩn/độ mật, "
            "theo dõi lịch sử từng bước (nháp, đang trình ký, đã ký, từ chối kèm lý do, thu hồi) và kiểm tra toàn vẹn tệp bằng mã băm SHA-256. "
            "Quy trình tạo và sử dụng mã PIN ký số qua SMS OTP: người dùng vào phần cấu hình chữ ký/bảo mật cá nhân để đăng ký/tạo mã PIN ký "
            "(hệ thống băm lưu bằng PBKDF2 kết hợp secret riêng, không lưu PIN dạng rõ); khi thực hiện tạo hoặc đặt lại PIN và khi xác nhận ký số, "
            "hệ thống gửi mã xác thực OTP qua SMS về số điện thoại đã đăng ký (ký bằng HMAC) để xác minh danh tính trước khi kích hoạt hoặc áp dụng chữ ký số. "
            "Thông tin phiếu trình ký thực tế phải kiểm tra từ dữ liệu tài khoản được quyền truy cập."
        ),
    },
    {
        "code": "branch-06-tasks",
        "title": "Nhanh 6 - Giao viec va xu ly cong viec",
        "phrases": (
            "giao viec", "cong viec", "nhiem vu", "han xu ly", "qua han",
            "chu tri", "phoi hop", "cho duyet", "hoan thanh",
        ),
        "content": (
            "Phân hệ Công việc hỗ trợ giao việc trực tiếp hoặc tạo nhiệm vụ từ văn bản với các vai trò chủ trì, chỉ đạo, phối hợp; "
            "theo dõi thời hạn xử lý, tiến độ, ý kiến trao đổi và tệp bằng chứng hoàn thành (trạng thái: chờ xử lý, đang thực hiện, chờ duyệt, hoàn thành, quá hạn). "
            "Công việc và tiến độ cụ thể của từng cá nhân cần tra cứu từ dữ liệu được cấp quyền."
        ),
    },
    {
        "code": "branch-07-system",
        "title": "Nhanh 7 - Co cau to chuc, phan quyen, phong hop va su kien",
        "phrases": (
            "co cau", "to chuc", "phan quyen", "vai tro", "rbac", "can bo",
            "nhan vien", "phong ban", "don vi", "chuc vu", "phong hop",
            "dat phong", "lich hop", "su kien", "sinh nhat",
        ),
        "content": (
            "Phân hệ Tổ chức & Hệ thống quản lý cơ cấu tổ chức (đơn vị, phòng ban, chức vụ, hồ sơ cán bộ nhân viên), "
            "phân quyền dựa trên vai trò RBAC theo mã quyền (ví dụ quyền `use_aiassistant` để dùng Trợ lý AI, quyền `view_tailieu` để xem tài liệu chung, "
            "quyền quản trị kho AI cho quản trị viên/nhóm ADMIN), đặt phòng họp chống trùng lịch, sự kiện, thông báo và chúc mừng sinh nhật. "
            "Thông tin nhân sự hoặc lịch họp chi tiết chỉ được trả lời từ dữ liệu mà tài khoản hiện tại có quyền xem."
        ),
    },
]

SYSTEM_GUIDE_PHRASES = (
    "quy trinh",
    "huong dan",
    "cac buoc",
    "nhung buoc nao",
    "hoat dong the nao",
    "lam the nao",
    "cach su dung",
    "phan he",
    "he thong ho tro",
    "tong quan he thong",
    "tao pin",
    "sms otp",
    "phan quyen",
    "co cau",
    "o dau",
    "phan loai",
    "quyen truy cap",
)

# Standalone ambiguous words or phrases like "ho tro" / "he thong" alone shouldn't trigger without domain context.
HIGH_SPECIFICITY_SINGLE_TERMS = {
    "rbac", "sha256", "otp", "sms", "pin", "tlbm", "qlvb", "dashboard",
}


def _normalize(text):
    lowered = (text or "").lower().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _contains_phrase(norm_text, phrase):
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", norm_text))


def is_system_guide_query(question):
    """Return True when the question asks about TLBM modules, workflows, or access rules."""
    normalized = _normalize(question)
    if not normalized:
        return False
    return any(_contains_phrase(normalized, phrase) for phrase in SYSTEM_GUIDE_PHRASES)


def match_business_sources(question, limit=2):
    """Return relevant static branch cards as citation-compatible sources."""
    norm_question = _normalize(question)
    if not norm_question:
        return []

    ranked = []
    for module in MODULES:
        matched_phrases = [
            phrase for phrase in module["phrases"]
            if _contains_phrase(norm_question, phrase)
        ]
        if not matched_phrases:
            continue
        score = sum(len(phrase.split()) for phrase in matched_phrases)
        has_specific_single = any(p in HIGH_SPECIFICITY_SINGLE_TERMS for p in matched_phrases)
        if score >= 3 or (len(matched_phrases) >= 2 and score >= 2) or has_specific_single:
            ranked.append((score, len(matched_phrases), module))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)

    return [
        {
            "index": 0,
            "file_name": module["title"],
            "page": None,
            "section": None,
            "chunk_id": module["code"],
            "category": "Mo ta chuc nang",
            "score": float(score),
            "preview": module["content"][:180],
            "context": module["content"],
            "source_type": "business_spec",
            "source_id": module["code"],
        }
        for score, _count, module in ranked[:limit]
    ]
