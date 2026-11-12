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

    # Đổi mật khẩu cá nhân
    path("change-password/", views.change_password_view, name="change_password"),

    # Admin đặt lại mật khẩu cho tài khoản (admin set pass)
    path("admin-set-password/", views.admin_set_password_view, name="admin_set_password"),

    # Đăng xuất
    path("logout/", views.logout_view, name="logout"),

    # Xác thực hai yếu tố (2FA TOTP)
    path("verify-2fa/", views.verify_2fa_view, name="verify_2fa"),
    path("2fa/status/", views.twofa_status_view, name="twofa_status"),
    path("2fa/setup/", views.twofa_setup_view, name="twofa_setup"),
    path("2fa/confirm/", views.twofa_confirm_view, name="twofa_confirm"),
    path("2fa/disable/", views.twofa_disable_view, name="twofa_disable"),
    path("2fa/backup-codes/regenerate/", views.twofa_regenerate_backup_codes_view, name="twofa_regenerate_backup_codes"),

    # Danh sách cán bộ nhân viên
    path("staffs/", views.staffs_view, name="staffs"),
]
