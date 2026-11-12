"""
URL Configuration cho app meetings (Issue #22 - Nhóm 7).
"""

from rest_framework.routers import DefaultRouter
from meetings.views import MeetingRoomViewSet, MeetingBookingViewSet

app_name = "meetings"

router = DefaultRouter()
router.register(r"meeting-rooms", MeetingRoomViewSet, basename="meeting-room")
router.register(r"meeting-bookings", MeetingBookingViewSet, basename="meeting-booking")

urlpatterns = router.urls
