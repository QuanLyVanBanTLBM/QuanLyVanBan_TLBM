from django.contrib import admin
from .models import PhongHop, DatPhongHop


@admin.register(PhongHop)
class PhongHopAdmin(admin.ModelAdmin):
    list_display = ("ten_phong", "vi_tri", "suc_chua", "is_public", "created_at")
    list_filter = ("is_public", "created_at")
    search_fields = ("ten_phong", "vi_tri", "thiet_bi")
    ordering = ("ten_phong",)


@admin.register(DatPhongHop)
class DatPhongHopAdmin(admin.ModelAdmin):
    list_display = (
        "tieu_de",
        "phong_hop",
        "nguoi_dat",
        "don_vi_to_chuc",
        "thoi_gian_bat_dau",
        "thoi_gian_ket_thuc",
        "trang_thai",
    )
    list_filter = ("trang_thai", "phong_hop", "thoi_gian_bat_dau")
    search_fields = ("tieu_de", "don_vi_to_chuc", "nguoi_dat__username", "nguoi_dat__profile__full_name")
    ordering = ("-thoi_gian_bat_dau",)
