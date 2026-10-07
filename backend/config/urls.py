"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include

from backend.api import views as ai_views

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # ── Module Nhóm 1 — Hiếu ──────────────────────────────────────────────
    # API Xác thực & Tài khoản: POST /api/auth/login/, GET /api/auth/profile/, ...
    path("api/auth/", include("accounts.urls", namespace="accounts")),

    # API Tổng quan Dashboard: GET /api/dashboard/overview/
    path("api/dashboard/", include("dashboard.urls", namespace="dashboard")),

    # ── Module Nhóm 7 — Quang ─────────────────────────────────────────────
    # API Quản lý Khối & Đơn vị: /api/organizations/...
    path("api/organizations/", include("organizations.urls", namespace="organizations")),

    # ── Module Nhóm 7 — Khánh (Issue #24) ──────────────────────────────────
    # API Quản lý Cán bộ Nhân viên (CBNV): /api/accounts/...
    path("api/accounts/", include("accounts.employee_urls", namespace="employee_management")),
    # Danh mục Chức vụ (Issue #20)
    path("api/positions/", include("accounts.position_urls", namespace="positions")),

    # ── Module Nhóm 7 — Tân + Hiếu (Issue #21) ─────────────────────────────
    # API Phân quyền (Issue #21): /api/roles/, /api/permissions/, /api/auth/me/permissions/
    path("api/", include("authorization.urls", namespace="authorization")),

    # ── Module Nhóm 7 — Tình (Issue #23) ──────────────────────────────────
    # API Sinh nhật: GET /api/birthdays/calendar/, /api/birthdays/day/, ...
    path("api/birthdays/", include("birthdays.urls", namespace="birthdays")),

    # ── Module Nhóm 8 — Trợ lý AI (Chatbox, RAG) ───────────────────────────
    # Mọi endpoint yêu cầu đăng nhập; chat cần use_aiassistant, quản trị kho/cài đặt chỉ superuser.
    path("health/ai", ai_views.ai_health),
    path("api/chat", ai_views.chat),
    path("api/upload", ai_views.upload_sync),
    path("api/upload/async", ai_views.upload_async),
    path("api/upload/progress/<str:job_id>", ai_views.upload_progress),
    path("api/documents", ai_views.documents),
    path("api/documents/<path:filename>/preview", ai_views.preview_document),
    path("api/documents/<path:filename>/file", ai_views.document_file),
    path("api/documents/<path:filename>", ai_views.document_detail),
    path("api/categories", ai_views.categories),
    path("api/reclassify/<path:filename>", ai_views.reclassify),
    path("api/settings/ai", ai_views.ai_settings),
]

