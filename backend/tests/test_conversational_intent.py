import re
import unicodedata

def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn").replace("đ", "d")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

DOC_INQUIRY_TERMS = (
    "van ban", "tai lieu", "ho so", "quy trinh", "quy dinh", "quy che",
    "noi quy", "nghi dinh", "thong tu", "quyet dinh", "chi thi", "luat",
    "dieu khoan", "dieu le", "mau bieu", "bieu mau", "to trinh", "cong van",
    "bao cao", "so hieu", "han xu ly", "thoi han", "bao mat", "tuyet mat",
    "toi mat", "can bo", "nhan su", "phong ban", "don vi", "chuc vu",
    "chuc danh", "phan quyen", "vai tro", "rbac", "tra cuu", "tim kiem",
    "tom tat", "trich xuat", "ky so", "trinh ky", "phe duyet", "tiep nhan",
    "vao so", "ban hanh", "phat hanh", "phan phoi", "luan chuyen", "luu tru",
    "hop dong", "bien ban", "ke hoach", "de an", "huong dan", "thu tuc",
    "cach tao", "cach duyet", "cach ky", "cach lam", "lam sao de", "danh muc",
    "co cau", "so do", "dinh kem", "tap tin", "tieu chuan", "dieu kien",
)

CONVERSATIONAL_PATTERNS = (
    # Chào hỏi
    "xin chao", "chao ban", "hello", "chao bot", "chao tro ly", "hi ban",
    "chao em", "chao anh", "chao chi", "chao buoi sang", "chao ngay moi",
    "good morning", "good afternoon", "good evening", "alo", "hey",
    # Cảm xúc mệt mỏi, buồn bã, áp lực
    "met moi", "met qua", "met that", "met ghe", "duoi qua", "oai qua",
    "kiet suc", "ap luc", "stress", "chan qua", "chan that", "that vong",
    "bat luc", "chan nan", "nan long", "nan qua", "sau qua", "tam trang te",
    "te qua", "khong vui", "be tac", "co don", "chan doi", "sao buon the",
    # Cảm xúc vui vẻ, hào hứng
    "vui qua", "vui that", "vui ghe", "hanh phuc", "thich qua", "tuyet qua",
    "tuyet voi qua", "phan khoi", "hao hung", "haha", "hihi", "hehe",
    "kaka", "kkk", "cuoi xiu", "hai huoc", "vui tinh", "suong qua",
    # Ngạc nhiên, bất ngờ
    "bat ngo qua", "ngac nhien", "o wow", "that a", "that khong", "that sao",
    # Đùa giỡn, chuyện phiếm
    "ke chuyen cuoi", "ke chuyen vui", "ke chuyen hai", "yeu toi khong",
    "thich toi khong", "lam nguoi yeu", "dang yeu the", "cute the",
    "de thuong the", "dua ti", "treu ti",
    # Cảm ơn, biết ơn
    "cam on", "thanks", "thank you", "tks", "biet on", "gioi qua",
    "thong minh qua", "dinh qua", "dinh that", "tot lam", "duoc day",
    # Thăm hỏi, giới thiệu
    "ban la ai", "ban ten gi", "ban khoe khong", "co khoe khong",
    "khoe khong ban", "dao nay the nao", "hom nay the nao", "ban lam duoc gi",
    "ban giup duoc gi", "chuc nang cua ban", "gioi thieu ban than",
    "gioi thieu ve ban", "ai tao ra ban",
    # Tạm biệt
    "tam biet", "bye", "bye bye", "hen gap lai", "chuc ngu ngon", "ngu ngon",
    "chuc mot ngay tot lanh",
)

def has_doc_terms(normalized: str) -> bool:
    return any(term in normalized for term in DOC_INQUIRY_TERMS)

def is_conversational_or_emotional(question: str) -> bool:
    norm = normalize_for_match(question)
    if not norm:
        return True
    
    if has_doc_terms(norm):
        return False
        
    words = norm.split()
    if any(p in norm for p in CONVERSATIONAL_PATTERNS):
        return True
        
    if norm in ("chao", "hi", "alo", "chao nhe", "bye", "cam on"):
        return True
        
    if len(words) <= 8:
        return True
        
    return False

def test_conversational_cases():
    test_cases = [
        ("xin chào", True),
        ("Chào bạn nhé!", True),
        ("Hello trợ lý", True),
        ("Hôm nay mệt mỏi quá bạn ơi", True),
        ("Tôi buồn quá", True),
        ("Vừa xong việc, vui quá xá!", True),
        ("Haha bạn hài hước thật đấy", True),
        ("Cảm ơn bạn nhiều nha", True),
        ("Bạn là ai thế?", True),
        ("Kể chuyện cười đi bạn", True),
        ("Hôm nay trời đẹp ghê", True),
        ("Buồn ngủ quá rồi", True),
        ("Quy trình tiếp nhận văn bản đến như thế nào?", False),
        ("Chào bạn, quy trình xử lý văn bản đến ra sao?", False),
        ("Văn bản tuyệt mật gồm những loại nào?", False),
        ("Thời hạn lưu trữ hồ sơ công việc là bao lâu?", False),
        ("Tìm cho tôi hợp đồng số 12", False),
        ("Ai là người ký quyết định này?", False),
        ("Hướng dẫn ký số văn bản đi", False),
    ]
    for query, expected in test_cases:
        assert is_conversational_or_emotional(query) == expected, f"Failed on '{query}'"
