"""
Django Admin cho app meetings (Issue #22 - Nhóm 7).
"""

from django.contrib import admin
from meetings.models import MeetingRoom, MeetingBooking


@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "capacity", "trang_thai", "is_public", "created_at", "updated_at")
    list_filter = ("trang_thai", "is_public", "created_at")
    search_fields = ("name", "location", "amenities", "ghi_chu")
    ordering = ("name",)


@admin.register(MeetingBooking)
class MeetingBookingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "room",
        "organizer",
        "department",
        "date",
        "start_time",
        "end_time",
        "attendees_count",
        "trang_thai",
        "created_at",
    )
    list_filter = ("trang_thai", "room", "date")
    search_fields = (
        "title",
        "purpose",
        "organizer__username",
        "organizer__ho_ten",
        "department__ten",
    )
    ordering = ("-date", "-start_time")
