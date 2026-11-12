from django.contrib import admin

from .models import HoSo, LoaiVanBan


@admin.register(HoSo)
class HoSoAdmin(admin.ModelAdmin):
    list_display = (
        "stt_uu_tien",
        "so_ky_hieu",
        "ten_ho_so",
        "nguoi_lap",
        "ngay_lap",
        "is_he_thong",
    )
    search_fields = ("so_ky_hieu", "ten_ho_so", "ghi_chu")
    list_filter = ("is_he_thong", "ngay_lap")
    readonly_fields = ("is_he_thong", "created_at", "updated_at")
    list_select_related = ("nguoi_lap",)
    ordering = ("-is_he_thong", "stt_uu_tien", "id")


@admin.register(LoaiVanBan)
class LoaiVanBanAdmin(admin.ModelAdmin):
    list_display = ("ten_loai", "ho_so", "ngay_lap", "updated_at")
    search_fields = ("ten_loai", "ho_so__so_ky_hieu", "ho_so__ten_ho_so")
    list_filter = ("ngay_lap",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("ho_so",)
    ordering = ("ho_so_id", "id")
