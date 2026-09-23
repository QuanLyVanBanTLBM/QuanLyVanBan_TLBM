from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PhongHopViewSet, DatPhongHopViewSet

app_name = "meetings"

router = DefaultRouter()
router.register(r"meeting-rooms", PhongHopViewSet, basename="meeting-rooms")
router.register(r"meeting-bookings", DatPhongHopViewSet, basename="meeting-bookings")

urlpatterns = [
    path("", include(router.urls)),
]
