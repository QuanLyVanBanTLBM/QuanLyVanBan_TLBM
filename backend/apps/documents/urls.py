"""URL routing cho Module Văn Bản — Hỗ trợ 2 phân hệ (Đến / Đi) và unified endpoint."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet,
    VanBanDenViewSet,
    VanBanDiViewSet,
    VanBanMatViewSet,
    FolderViewSet,
    FolderFileViewSet,
)

router = DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folder")
router.register(r"folder-files", FolderFileViewSet, basename="folder-file")
router.register(r"documents/den", VanBanDenViewSet, basename="vanbanden")
router.register(r"documents/di", VanBanDiViewSet, basename="vanbandi")
router.register(r"documents/mat", VanBanMatViewSet, basename="vanbanmat")
router.register(r"documents/confidential", VanBanMatViewSet, basename="vanbanmat_confidential")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("", include(router.urls)),
]
