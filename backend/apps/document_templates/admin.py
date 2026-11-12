from django.contrib import admin
from .models import (
    DanhMucTaiLieu,
    LoaiTaiLieu,
    TaiLieuChiTiet,
    ChiTietTaiLieuLoaiTaiLieu,
    ChiTietTaiLieuAttachment,
)


class ChiTietTaiLieuLoaiTaiLieuInline(admin.TabularInline):
    model = ChiTietTaiLieuLoaiTaiLieu
    extra = 1


class ChiTietTaiLieuAttachmentInline(admin.TabularInline):
    model = ChiTietTaiLieuAttachment
    extra = 1
    fields = ('name', 'path', 'file_size', 'mime_type', 'is_deleted', 'nguoi_tao', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(DanhMucTaiLieu)
class DanhMucTaiLieuAdmin(admin.ModelAdmin):
    list_display = ('stt_uu_tien', 'ky_hieu', 'ten_tai_lieu', 'nguoi_lap', 'ngay_lap', 'created_at')
    search_fields = ('ten_tai_lieu', 'ky_hieu', 'ghi_chu')
    ordering = ('stt_uu_tien',)


@admin.register(LoaiTaiLieu)
class LoaiTaiLieuAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_loai', 'dm_tai_lieu', 'is_public', 'ngay_lap', 'created_at')
    list_filter = ('dm_tai_lieu', 'is_public')
    search_fields = ('ten_loai', 'ghi_chu')
    ordering = ('id',)


@admin.register(TaiLieuChiTiet)
class TaiLieuChiTietAdmin(admin.ModelAdmin):
    list_display = ('id', 'ky_hieu', 'tieu_de', 'dm_tai_lieu', 'hieu_luc', 'ngay_dang', 'hien_thi', 'don_vi_id', 'nguoi_tao')
    list_filter = ('hieu_luc', 'hien_thi', 'dm_tai_lieu', 'ngay_dang')
    search_fields = ('tieu_de', 'ky_hieu', 'noi_ban_hanh', 'ghi_chu')
    inlines = [ChiTietTaiLieuLoaiTaiLieuInline, ChiTietTaiLieuAttachmentInline]
    ordering = ('-ngay_dang', '-id')


@admin.register(ChiTietTaiLieuAttachment)
class ChiTietTaiLieuAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'document', 'file_size', 'mime_type', 'is_deleted', 'created_at', 'nguoi_tao')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('name', 'path', 'document__tieu_de')
    ordering = ('-created_at',)
