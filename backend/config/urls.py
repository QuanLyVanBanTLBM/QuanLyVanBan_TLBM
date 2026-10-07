from django.contrib import admin
from django.urls import path, include

from backend.api import views


urlpatterns = [
    # ── Django Admin ──────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── Module Staging (Nhóm 1): Xác thực & Dashboard ────────────────────
    path("api/auth/", include("accounts.urls", namespace="accounts")),
    path("api/dashboard/", include("dashboard.urls", namespace="dashboard")),

    # ── Module Chatbox AI & RAG (Nhóm 8): Hoàn toàn nguyên bản ────────────
    # 1. Các endpoint gốc
    path("", views.root),
    path("health/ai", views.ai_health),
    path("chat", views.chat),
    path("upload", views.upload_sync),
    path("upload/async", views.upload_async),
    path("upload/progress/<str:job_id>", views.upload_progress),
    path("documents", views.documents),
    path("documents/<path:filename>/preview", views.preview_document),
    path("documents/<path:filename>/file", views.document_file),
    path("documents/<path:filename>", views.document_detail),
    path("categories", views.categories),
    path("reclassify/<path:filename>", views.reclassify),
    path("settings/ai", views.ai_settings),

    # 2. Các alias tiền tố /api/ tương thích ngược với Frontend
    path("api/chat", views.chat),
    path("api/upload", views.upload_sync),
    path("api/upload/async", views.upload_async),
    path("api/upload/progress/<str:job_id>", views.upload_progress),
    path("api/documents", views.documents),
    path("api/documents/<path:filename>/preview", views.preview_document),
    path("api/documents/<path:filename>/file", views.document_file),
    path("api/documents/<path:filename>", views.document_detail),
    path("api/categories", views.categories),
    path("api/reclassify/<path:filename>", views.reclassify),
    path("api/settings/ai", views.ai_settings),
]
