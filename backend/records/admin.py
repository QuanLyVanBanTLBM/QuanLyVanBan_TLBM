from django.contrib import admin
from .models import Dossier, DocumentType

@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_by', 'created_at', 'is_system', 'sort_order')
    search_fields = ('code', 'name')
    list_filter = ('is_system', 'created_at')
    readonly_fields = ('created_at', 'is_system') 
    ordering = ('-is_system', 'sort_order') # Sắp xếp hệ thống lên đầu

    def get_readonly_fields(self, request, obj=None):
        # Chặn sửa field hệ thống để bảo vệ Hồ sơ chung
        if obj and obj.is_system:
            return self.readonly_fields + ('code', 'name')
        return self.readonly_fields

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'dossier', 'created_at', 'sort_order')
    search_fields = ('name', 'dossier__code', 'dossier__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    ordering = ('dossier', 'sort_order')