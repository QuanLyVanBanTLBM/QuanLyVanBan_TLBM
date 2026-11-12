"""Searchable business scope notes derived from repository branches 1 through 7.

These cards describe module intent only. They are not a source of live records,
counts, permissions, or workflow state.
"""

import re
import unicodedata


MODULES = [
    {
        "code": "branch-01-dashboard",
        "title": "Nhanh 1 - Dashboard va tong quan",
        "keywords": "dashboard tong quan thong ke ngay thang van ban den di trinh ky phe duyet cong viec han xu ly lich hop sinh nhat",
        "content": "Branch 1 describes a dashboard that summarizes incoming and outgoing documents, pending approvals or signatures, assigned and overdue tasks, today's meetings, events, and birthdays. These are planned dashboard indicators. Current values must come from authorized live application data.",
    },
    {
        "code": "branch-02-documents",
        "title": "Nhanh 2 - Quan ly van ban den, di va mat",
        "keywords": "van ban den tiep nhan vao so phan phoi xu ly van ban di du thao duyet ban hanh cap so phat hanh van ban mat tuyet mat nguoi nhan phong ban",
        "content": "Branch 2 covers incoming documents (receipt, registration, distribution, and processing), outgoing documents (drafting, approval, numbering, and release), and confidential documents with recipient or department access restrictions. Details about a specific document must be retrieved from authorized SQL records.",
    },
    {
        "code": "branch-03-records",
        "title": "Nhanh 3 - Ho so va loai van ban",
        "keywords": "ho so cong viec danh muc loai van ban nghi quyet quyet dinh chi thi thong bao to trinh thoi han bao quan dong mo nop luu luu tru",
        "content": "Branch 3 covers document type catalogs and case files: creating a file, grouping documents, tracking retention periods, closing or reopening files, and transferring them to archives. A live file's status or retention deadline must be looked up from application data.",
    },
    {
        "code": "branch-04-templates",
        "title": "Nhanh 4 - Tai lieu dung chung va bieu mau",
        "keywords": "tai lieu dung chung bieu mau mau van ban template tai xuong docx xlsx pdf phan loai phong ban linh vuc",
        "content": "Branch 4 covers shared resources and standard templates, categorized by department or field, with downloadable DOCX, XLSX, or PDF files. The actual catalog and available downloads must be checked in the live repository.",
    },
    {
        "code": "branch-05-signing",
        "title": "Nhanh 5 - Quy trinh trinh ky va ky so",
        "keywords": "trinh ky ky duyet ky so chu ky dien tu quy trinh luong phe duyet nhieu cap nguoi ky workflow du thao dang trinh ky da ky tu choi thu hoi sha256 khan cap",
        "content": "Branch 5 specifies a multi-step signing and approval workflow, ordered approvers, urgency and confidentiality, step history, approval or rejection with a reason, and SHA-256 file integrity checks. Proposed states include draft, in approval, approved, rejected, and recalled. This is a feature specification and does not prove that a particular workflow is implemented or active.",
    },
    {
        "code": "branch-06-tasks",
        "title": "Nhanh 6 - Giao viec va xu ly cong viec",
        "keywords": "cong viec giao viec nhiem vu chu tri chi dao tham gia phoi hop deadline han xu ly qua han dang xu ly cho duyet ket qua bang chung hoan thanh y kien",
        "content": "Branch 6 covers assigning tasks directly or from documents, with creator, lead, directing, and participating roles; deadlines, progress, comments, and evidence. Specified statuses include waiting, in progress, awaiting approval, completed, incomplete, and overdue. A person's actual tasks or current status require authorized live data.",
    },
    {
        "code": "branch-07-system",
        "title": "Nhanh 7 - To chuc, phan quyen, phong hop va su kien",
        "keywords": "quan tri he thong co cau to chuc don vi phong ban chuc vu can bo nhan vien phan quyen vai tro rbac phong hop lich hop dat phong thiet bi chong trung sinh nhat su kien thong bao",
        "content": "Branch 7 covers organizational units, departments, positions, employee profiles, role-based access control, meeting-room bookings with conflict prevention, events, and birthdays. Personal or schedule details must only be answered from records the current account is allowed to see.",
    },
]

STOP_WORDS = {
    "va", "la", "cua", "cho", "toi", "ban", "gi", "nao", "nay", "do",
    "duoc", "trong", "tren", "duoi", "voi", "theo", "cac", "nhung",
    "mot", "co", "khong", "hay", "giup", "hoi", "ve", "tai", "tu",
    "can", "lam", "sao", "bao", "nhieu", "nhanh",
}


def _normalize(text):
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def match_business_sources(question, limit=2):
    """Return relevant static branch cards as citation-compatible sources."""
    terms = {
        term for term in _normalize(question).split()
        if len(term) > 2 and term not in STOP_WORDS
    }
    if not terms:
        return []

    ranked = []
    for module in MODULES:
        searchable = set(_normalize(" ".join((module["title"], module["keywords"], module["content"]))).split())
        matched = terms.intersection(searchable)
        score = len(matched)
        if score >= 2:
            ranked.append((score, module))
    ranked.sort(key=lambda row: row[0], reverse=True)

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
        for score, module in ranked[:limit]
    ]
