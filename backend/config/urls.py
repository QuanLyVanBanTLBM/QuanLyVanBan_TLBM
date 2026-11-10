"""
URL configuration for QLVB&TL project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import staffs_view
from api import views as ai_views

urlpatterns = [
    path("api/records/", include("records.urls", namespace="records")),
    # Django Admin
    path("admin/", admin.site.urls),

    # ── Module Nhóm 1 — Hiếu ──────────────────────────────────────────────
    # API Cán bộ / Nhân viên (phục vụ liên nhóm)
    path("api/accounts/staffs/", staffs_view, name="accounts_staffs"),
    # API Xác thực & Tài khoản: POST /api/auth/login/, GET /api/auth/profile/, ...
    path("api/auth/", include("accounts.urls", namespace="accounts")),

    # API Tổng quan Dashboard: GET /api/dashboard/overview/
    path("api/dashboard/", include("dashboard.urls", namespace="dashboard")),

    # ── Module Nhóm 6 — Công việc ─────────────────────────────────────────
    path("api/work/", include("work.urls")),

    # ── Module Nhóm 2 — Quản lý Văn bản (Kiệt) ───────────────────────────
    path("api/", include("documents.urls")),

    # ── Module Nhóm 5 — Trình ký ──────────────────────────────────────────
    path("api/v1/signing/", include("signing.urls", namespace="signing")),
    # ── Module Nhóm 4 — Tài liệu & Biểu mẫu (Nguyễn Chí Tín) ───────────────
    path("api/resources/", include("document_templates.urls")),

    # ── Module Nhóm 7 — Quang ─────────────────────────────────────────────
    # API Quản lý Khối & Đơn vị: /api/organizations/...
    path("api/organizations/", include("organizations.urls", namespace="organizations")),

    # ── Module Nhóm 7 — Bảo (Issue #22) ──────────────────────────────────
    # API Quản lý Phòng họp & Đặt phòng: /api/meeting-rooms/, /api/meeting-bookings/
    path("api/", include("meetings.urls", namespace="meetings")),

    # ── Module Nhóm 7 — Khánh (Issue #24) ──────────────────────────────────
    # API Quản lý Cán bộ Nhân viên (CBNV): /api/accounts/...
    path("api/accounts/", include("accounts.employee_urls", namespace="employee_management")),
    # Danh mục Chức vụ (Issue #20)
    path("api/positions/", include("accounts.position_urls", namespace="positions")),

    # ── Module Nhóm 7 — Tân + Hiếu (Issue #21) ─────────────────────────────
    # API Phân quyền (Issue #21): /api/roles/, /api/permissions/, /api/auth/me/permissions/
    path("api/", include("authorization.urls", namespace="authorization")),

    # ── Module Nhóm 7 — Tình (Issue #23) ──────────────────────────────────
    # API Sinh nhật: GET /api/birthdays/calendar/, /api/birthdays/day/; POST /api/birthdays/card/.
    path("api/birthdays/", include("birthdays.urls", namespace="birthdays")),

    # ── Module Nhóm 8 — Trợ lý AI (Chatbox, RAG) ───────────────────────────
    # Prefix /api/ai/ tách khỏi router của app documents (/api/documents/...).
    # Mọi endpoint yêu cầu đăng nhập; chat cần use_aiassistant, quản trị kho/cài đặt chỉ superuser.
    path("health/ai", ai_views.ai_health),
    path("api/health/ready/", ai_views.readiness),
    path("api/ai/chat", ai_views.chat),
    path("api/ai/upload", ai_views.upload_sync),
    path("api/ai/upload/async", ai_views.upload_async),
    path("api/ai/upload/progress/<str:job_id>", ai_views.upload_progress),
    path("api/ai/documents", ai_views.documents),
    path("api/ai/documents/<path:filename>/preview", ai_views.preview_document),
    path("api/ai/documents/<path:filename>/file", ai_views.document_file),
    path("api/ai/documents/<path:filename>/", ai_views.document_detail),
    path("api/ai/documents/<path:filename>", ai_views.document_detail),
    path("api/ai/categories", ai_views.categories),
    path("api/ai/reclassify/<path:filename>", ai_views.reclassify),
    path("api/ai/settings", ai_views.ai_settings),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.DOCUMENT_STORAGE_ROOT)
