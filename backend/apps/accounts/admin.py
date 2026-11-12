from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Employee, Position


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("display_order", "name", "is_public")
    search_fields = ("name",)
    ordering = ("display_order",)


@admin.register(Employee)
class EmployeeAdmin(BaseUserAdmin):
    list_display = ("username", "ho_ten", "email", "don_vi", "chuc_vu", "trang_thai", "is_active")
    list_filter = ("trang_thai", "is_active", "is_staff", "don_vi")
    search_fields = ("username", "ho_ten", "email", "sdt")
    ordering = ("ho_ten",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Thông tin CBNV", {"fields": ("ho_ten", "ngay_sinh", "email", "sdt", "don_vi", "chuc_vu", "chuc_danh", "trang_thai", "is_public", "ghi_chu")}),
        ("Phân quyền", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "ho_ten", "ngay_sinh", "email", "don_vi", "chuc_vu")}),
    )
    filter_horizontal = ("groups", "user_permissions")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or obj.pk == request.user.pk:
            return fieldsets
        return tuple(
            (name, {**options, "fields": tuple(field for field in options["fields"] if field != "ngay_sinh")})
            for name, options in fieldsets
        )
