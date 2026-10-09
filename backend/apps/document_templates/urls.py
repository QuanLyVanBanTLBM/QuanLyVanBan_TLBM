from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    DanhMucTaiLieuViewSet,
    LoaiTaiLieuViewSet,
    TaiLieuChiTietViewSet,
    ChiTietTaiLieuAttachmentViewSet,
)

router = DefaultRouter()
router.register(r'categories', DanhMucTaiLieuViewSet, basename='document-category')
router.register(r'types', LoaiTaiLieuViewSet, basename='document-type')
router.register(r'documents', TaiLieuChiTietViewSet, basename='document-detail')
router.register(r'chi-tiet-tai-lieu', TaiLieuChiTietViewSet, basename='chi-tiet-tai-lieu')
router.register(r'general-documents', TaiLieuChiTietViewSet, basename='general-document')
router.register(r'attachments', ChiTietTaiLieuAttachmentViewSet, basename='document-attachment')

urlpatterns = [
    path('', include(router.urls)),
]
