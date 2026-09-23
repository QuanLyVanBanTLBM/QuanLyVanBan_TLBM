"""
URL routing cho phân hệ Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
Tác giả: Lê Duy Khánh.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KhoiKhuVucViewSet, DonViViewSet

app_name = "organizations"

router = DefaultRouter()
router.register(r"regions", KhoiKhuVucViewSet, basename="regions")
router.register(r"units", DonViViewSet, basename="units")

urlpatterns = [
    path("", include(router.urls)),
]
