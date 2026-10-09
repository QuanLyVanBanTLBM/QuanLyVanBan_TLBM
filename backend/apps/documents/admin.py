"""Django Admin cho Module Văn Bản — Phân hệ Đến & Đi."""

from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import (
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    DocumentViewLog,
    DocumentAccessLog,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Văn bản Đến Admin
# ═══════════════════════════════════════════════════════════════════

class VanBanDenAttachmentInline(admin.TabularInline):
    model = VanBanDenAttachment
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(VanBanDen)
class VanBanDenAdmin(admin.ModelAdmin):
    list_display = [
        "so_hieu",
        "nam",
        "so_thu_tu",
        "ngay_den",
        "trich_yeu_short",
        "noi_ban_hanh",
        "pham_vi",
        "hieu_luc",
        "hien_thi",
        "created_at",
    ]
    list_filter = ["nam", "pham_vi", "hieu_luc", "hien_thi"]
    search_fields = ["so_hieu", "trich_yeu", "noi_ban_hanh"]
    readonly_fields = ["so_thu_tu", "created_at", "updated_at"]
    inlines = [VanBanDenAttachmentInline]
    list_per_page = 20

    @admin.display(description="Trích yếu")
    def trich_yeu_short(self, obj):
        if len(obj.trich_yeu) > 80:
            return obj.trich_yeu[:80] + "..."
        return obj.trich_yeu


# ═══════════════════════════════════════════════════════════════════
# 2. Văn bản Đi Admin
# ═══════════════════════════════════════════════════════════════════

class VanBanDiAttachmentInline(admin.TabularInline):
    model = VanBanDiAttachment
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(VanBanDi)
class VanBanDiAdmin(admin.ModelAdmin):
    list_display = [
        "so_hieu",
        "nam",
        "so_thu_tu",
        "ngay_ban_hanh",
        "trich_yeu_short",
        "noi_ban_hanh",
        "pham_vi",
        "hieu_luc",
        "hien_thi",
        "created_at",
    ]
    list_filter = ["nam", "pham_vi", "hieu_luc", "hien_thi"]
    search_fields = ["so_hieu", "trich_yeu", "noi_ban_hanh"]
    readonly_fields = ["so_thu_tu", "created_at", "updated_at"]
    inlines = [VanBanDiAttachmentInline]
    list_per_page = 20

    @admin.display(description="Trích yếu")
    def trich_yeu_short(self, obj):
        if len(obj.trich_yeu) > 80:
            return obj.trich_yeu[:80] + "..."
        return obj.trich_yeu


# ═══════════════════════════════════════════════════════════════════
# 3. View Log Admin & Access Log Admin
# ═══════════════════════════════════════════════════════════════════

@admin.register(DocumentViewLog)
class DocumentViewLogAdmin(admin.ModelAdmin):
    list_display = ["document_type", "document_id", "user", "viewed_at"]
    list_filter = ["document_type", "viewed_at"]
    search_fields = ["user__username", "user__ho_ten"] if hasattr(get_user_model(), "ho_ten") else ["user__username", "user__first_name", "user__last_name"]
    readonly_fields = ["viewed_at"]
    list_per_page = 30


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ["document_type", "document_id", "user", "hanh_dong", "doi_tuong_user", "created_at"]
    list_filter = ["document_type", "hanh_dong", "created_at"]
    search_fields = ["user__username", "user__ho_ten"] if hasattr(get_user_model(), "ho_ten") else ["user__username", "user__first_name", "user__last_name"]
    readonly_fields = ["created_at"]
    list_per_page = 30
