from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    # Đăng nhập — cấp access + refresh token
    path("login/", views.login_view, name="login"),

    # Làm mới access token bằng refresh token (SimpleJWT built-in)
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Lấy thông tin cá nhân người dùng đang đăng nhập
    path("profile/", views.profile_view, name="profile"),

    # Đổi mật khẩu
    path("change-password/", views.change_password_view, name="change_password"),

    # Đăng xuất
    path("logout/", views.logout_view, name="logout"),

    # Danh sách cán bộ nhân viên
    path("staffs/", views.staffs_view, name="staffs"),
]
