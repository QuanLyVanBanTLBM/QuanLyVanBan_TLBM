from django.contrib import admin
from .models import KhoiKhuVuc, DonVi


@admin.register(KhoiKhuVuc)
class KhoiKhuVucAdmin(admin.ModelAdmin):
    list_display = ("id", "ten", "thu_tu_hien_thi")
    search_fields = ("ten",)
    ordering = ("ten",)


@admin.register(DonVi)
class DonViAdmin(admin.ModelAdmin):
    list_display = ("stt_uu_tien", "ten", "khoi", "dien_thoai", "email", "is_public")
    list_filter = ("khoi", "is_public")
    search_fields = ("ten", "dia_chi", "dien_thoai", "email")
    ordering = ("stt_uu_tien",)
