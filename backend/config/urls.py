"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # ── Module Nhóm 1 — Hiếu ──────────────────────────────────────────────
    # API Xác thực & Tài khoản: POST /api/auth/login/, GET /api/auth/profile/, ...
    path("api/auth/", include("accounts.urls", namespace="accounts")),

    # API Tổng quan Dashboard: GET /api/dashboard/overview/
    path("api/dashboard/", include("dashboard.urls", namespace="dashboard")),

    # ── Module Nhóm 7 — Khánh ─────────────────────────────────────────────
    # API Cơ cấu Tổ chức & Đơn vị: GET /api/organizations/regions/, /units/, ...
    path("api/organizations/", include("organizations.urls", namespace="organizations")),
]

