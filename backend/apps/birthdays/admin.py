from django.contrib import admin
from .models import BirthdayEmailLog, BirthdayWish


@admin.register(BirthdayWish)
class BirthdayWishAdmin(admin.ModelAdmin):
    list_display = ("employee", "sender_name", "trang_thai", "likes_count", "created_at")
    list_filter = ("trang_thai", "card_template", "is_anonymous")
    search_fields = ("employee__ho_ten", "sender_name", "message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BirthdayEmailLog)
class BirthdayEmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "sent_date",
        "recipient_email",
        "trang_thai",
        "retry_count",
        "sent_at",
    )
    list_filter = (
        "trang_thai",
        "sent_date",
        "card_template",
    )
    search_fields = (
        "employee__ho_ten",
        "recipient_email",
        "subject",
    )
    readonly_fields = (
        "employee",
        "sent_date",
        "sent_at",
        "recipient_email",
        "subject",
        "card_template",
        "retry_count",
        "error_message",
        "smtp_response_code",
        "next_retry_at",
        "opened_at",
        "clicked_count",
        "email_provider",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
