"""URL routing cho Module Văn Bản — Hỗ trợ 2 phân hệ (Đến / Đi) và unified endpoint."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .confidential_api import (ConfidentialKeyView, ConfidentialDirectoryView,
                              ConfidentialDocumentView, ConfidentialDetailView, ConfidentialRevokeView)

from .views import (
    DocumentViewSet,
    VanBanDenViewSet,
    VanBanDiViewSet,
)

router = DefaultRouter()
router.register(r"documents/den", VanBanDenViewSet, basename="vanbanden")
router.register(r"documents/di", VanBanDiViewSet, basename="vanbandi")
router.register(r"documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("confidential/key/", ConfidentialKeyView.as_view()),
    path("confidential/directory/", ConfidentialDirectoryView.as_view()),
    path("confidential/documents/", ConfidentialDocumentView.as_view()),
    path("confidential/documents/<uuid:pk>/", ConfidentialDetailView.as_view()),
    path("confidential/documents/<uuid:pk>/revoke/", ConfidentialRevokeView.as_view()),
    path("", include(router.urls)),
]
