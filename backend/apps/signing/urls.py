from django.urls import path

from . import views

app_name = "signing"

urlpatterns = [
    # Kiểm tra app đã được nối vào hệ thống
    path("ping/", views.ping_view, name="ping"),

    # Quy trình trình ký
    path("quy-trinh/", views.QuyTrinhListCreateView.as_view(), name="quy-trinh-list"),
    path("quy-trinh/<int:pk>/", views.QuyTrinhDetailView.as_view(), name="quy-trinh-detail"),
    path("quy-trinh/<int:pk>/kich-hoat/", views.QuyTrinhActionView.as_view(action="kich-hoat"), name="quy-trinh-kich-hoat"),
    path("quy-trinh/<int:pk>/ngung/", views.QuyTrinhActionView.as_view(action="ngung"), name="quy-trinh-ngung"),
    path("quy-trinh/<int:pk>/nhan-ban/", views.QuyTrinhActionView.as_view(action="nhan-ban"), name="quy-trinh-nhan-ban"),

    # Khóa ký của người dùng hiện tại
    path("khoa/", views.KhoaListCreateView.as_view(), name="khoa-list"),
    path("khoa/<int:pk>/thach-thuc/", views.KhoaThachThucView.as_view(), name="khoa-thach-thuc"),
    path("khoa/<int:pk>/xac-minh/", views.KhoaActionView.as_view(action="xac-minh"), name="khoa-xac-minh"),
    path("khoa/<int:pk>/kich-hoat/", views.KhoaActionView.as_view(action="kich-hoat"), name="khoa-kich-hoat"),
    path("khoa/<int:pk>/thu-hoi/", views.KhoaActionView.as_view(action="thu-hoi"), name="khoa-thu-hoi"),
    path("khoa/<int:pk>/xoay-vong/", views.KhoaActionView.as_view(action="xoay-vong"), name="khoa-xoay-vong"),

    # PIN mở khóa ký (Phase 6)
    path("khoa/<int:pk>/dat-pin/", views.KhoaPinView.as_view(action="dat-pin"), name="khoa-dat-pin"),
    path("khoa/<int:pk>/mo-khoa-ky/", views.KhoaPinView.as_view(action="mo-khoa-ky"), name="khoa-mo-khoa-ky"),
    path("khoa/<int:pk>/doi-pin/", views.KhoaPinView.as_view(action="doi-pin"), name="khoa-doi-pin"),
]
