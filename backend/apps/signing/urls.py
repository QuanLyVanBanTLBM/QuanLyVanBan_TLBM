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

    # Hồ sơ trình ký (Phase 7, #80)
    path("trinh-ky/", views.TrinhKyListCreateView.as_view(), name="trinh-ky-list"),
    path("trinh-ky/thong-ke/", views.ThongKeHoSoView.as_view(), name="trinh-ky-thong-ke"),
    path("trinh-ky/<int:pk>/", views.TrinhKyDetailView.as_view(), name="trinh-ky-detail"),
    path("trinh-ky/<int:pk>/tep/", views.TrinhKyTepView.as_view(), name="trinh-ky-tep"),
    path("trinh-ky/<int:pk>/gui/", views.TrinhKyActionView.as_view(action="gui"), name="trinh-ky-gui"),
    path("trinh-ky/<int:pk>/huy/", views.TrinhKyActionView.as_view(action="huy"), name="trinh-ky-huy"),
    path("trinh-ky/<int:pk>/trinh-lai/", views.TrinhKyActionView.as_view(action="trinh-lai"),
         name="trinh-ky-trinh-lai"),

    # Hành động người ký (Phase 8, #80)
    path("trinh-ky/<int:pk>/ky/", views.HanhDongKyView.as_view(action="ky"), name="trinh-ky-ky"),
    path("trinh-ky/<int:pk>/tu-choi/", views.HanhDongKyView.as_view(action="tu-choi"), name="trinh-ky-tu-choi"),
    path("trinh-ky/<int:pk>/thu-hoi/", views.HanhDongKyView.as_view(action="thu-hoi"), name="trinh-ky-thu-hoi"),
    path("trinh-ky/<int:pk>/uy-quyen/", views.UyQuyenView.as_view(), name="trinh-ky-uy-quyen"),

    # Trả lại để sửa (lõi Phase 9, #80)
    path("trinh-ky/<int:pk>/yeu-cau-sua/", views.YeuCauSuaView.as_view(), name="trinh-ky-yeu-cau-sua"),
    path("trinh-ky/<int:pk>/trao-doi/", views.TraoDoiView.as_view(), name="trinh-ky-trao-doi"),
    path("trinh-ky/<int:pk>/giai-quyet/", views.GiaiQuyetView.as_view(), name="trinh-ky-giai-quyet"),

    # Bằng chứng và tệp hoàn tất (lõi Phase 10, #80)
    path("trinh-ky/<int:pk>/bang-chung/", views.BangChungView.as_view(), name="trinh-ky-bang-chung"),
    path("trinh-ky/<int:pk>/tep-hoan-tat/", views.TepHoanTatView.as_view(), name="trinh-ky-tep-hoan-tat"),
    path("trinh-ky/<int:pk>/tao-lai-tep-hoan-tat/", views.TaoLaiTepHoanTatView.as_view(),
         name="trinh-ky-tao-lai-tep-hoan-tat"),
    path("trinh-ky/<int:pk>/anh-chu-ky/<int:chu_ky_id>/", views.AnhChuKyView.as_view(), name="trinh-ky-anh-chu-ky"),

    # Tìm tài khoản để cấu hình người ký (người quản lý quy trình)
    path("nguoi-dung/", views.NguoiDungView.as_view(), name="nguoi-dung"),
    path("don-vi/", views.DonViView.as_view(), name="don-vi"),
    path("chuc-vu/", views.ChucVuView.as_view(), name="chuc-vu"),
    path("can-bo-theo-chuc-vu/", views.CanBoTheoChucVuView.as_view(), name="can-bo-theo-chuc-vu"),
    path("thong-bao/", views.ThongBaoView.as_view(), name="thong-bao"),
    path("tai-lieu/", views.TaiLieuView.as_view(), name="tai-lieu"),
    # Hỗ trợ giao diện: người dùng hiện tại, chọn văn bản đi
    path("toi/", views.ToiView.as_view(), name="toi"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("van-ban-di/", views.VanBanDiView.as_view(), name="van-ban-di"),
]
