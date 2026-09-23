"""
Cấu hình Django Admin cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from django.contrib import admin
from .models import KhoiKhuVuc, DonVi


@admin.register(KhoiKhuVuc)
class KhoiKhuVucAdmin(admin.ModelAdmin):
    list_display = ("id", "ten", "thu_tu_hien_thi", "get_don_vi_count", "created_at")
    list_editable = ("thu_tu_hien_thi",)
    search_fields = ("ten",)
    ordering = ("thu_tu_hien_thi", "ten")

    @admin.display(description="Số lượng Đơn vị trực thuộc")
    def get_don_vi_count(self, obj):
        return obj.don_vi_list.count()


@admin.register(DonVi)
class DonViAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stt_uu_tien",
        "ten",
        "khoi",
        "dien_thoai",
        "email",
        "is_public",
        "created_at",
    )
    list_display_links = ("ten",)
    list_editable = ("stt_uu_tien", "is_public")
    list_filter = ("khoi", "is_public")
    search_fields = ("ten", "dia_chi", "dien_thoai", "email", "ghi_chu")
    ordering = ("stt_uu_tien", "ten")
    autocomplete_fields = ("khoi",)
