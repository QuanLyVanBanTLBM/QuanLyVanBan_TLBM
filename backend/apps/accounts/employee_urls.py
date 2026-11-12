"""
URL Routing cho phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
Tác giả: Lê Duy Khánh (leduykhanhdevs).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_employee import EmployeeViewSet, GroupViewSet

app_name = "employee_management"

router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"groups", GroupViewSet, basename="group")

urlpatterns = [
    path("", include(router.urls)),
]
