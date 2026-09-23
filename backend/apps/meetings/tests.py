from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import StaffProfile
from meetings.models import PhongHop, DatPhongHop


class MeetingRoomAndBookingTestCase(TestCase):
    """
    Test suite toàn diện cho Issue #22 (Phòng họp & Đặt lịch/Khóa khung giờ).
    """

    def setUp(self):
        self.client = APIClient()

        # Tạo user thường 1 (CBNV)
        self.user_staff1 = User.objects.create_user(
            username="hieu_staff",
            email="hieu@itc.edu.vn",
            password="password123",
            first_name="Minh",
            last_name="Hiệu",
        )
        self.profile1 = StaffProfile.objects.create(
            user=self.user_staff1,
            full_name="Nguyễn Phan Minh Hiệu",
            department="Phòng Hành chính - Tổng hợp",
            role="staff",
        )

        # Tạo user thường 2 (CBNV khác)
        self.user_staff2 = User.objects.create_user(
            username="tinh_staff",
            email="tinh@itc.edu.vn",
            password="password123",
            first_name="Đình",
            last_name="Tình",
        )
        self.profile2 = StaffProfile.objects.create(
            user=self.user_staff2,
            full_name="Trần Đình Tình",
            department="Phòng Công nghệ thông tin",
            role="staff",
        )

        # Tạo user Quản trị viên (Admin)
        self.user_admin = User.objects.create_superuser(
            username="tan_admin",
            email="tan@itc.edu.vn",
            password="adminpassword",
            first_name="Thanh",
            last_name="Tân",
        )
        self.profile_admin = StaffProfile.objects.create(
            user=self.user_admin,
            full_name="Tô Thanh Tân",
            department="Ban Giám hiệu",
            role="admin",
        )

        # Tạo phòng họp mẫu
        self.room_a = PhongHop.objects.create(
            ten_phong="Phòng Hội thảo A",
            vi_tri="Tầng 2, Tòa A",
            suc_chua=30,
            thiet_bi="Máy chiếu 4K, 2 Micro không dây, Hệ thống họp trực tuyến",
            is_public=True,
        )
        self.room_b = PhongHop.objects.create(
            ten_phong="Phòng Họp B",
            vi_tri="Tầng 3, Tòa B",
            suc_chua=10,
            thiet_bi="TV 65 inch, Bảng trắng",
            is_public=True,
        )

        # Cấu hình thời gian chuẩn cho test (ngày mai)
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.base_date = now + timedelta(days=1)
        self.t_08_00 = self.base_date.replace(hour=8)
        self.t_09_00 = self.base_date.replace(hour=9)
        self.t_10_00 = self.base_date.replace(hour=10)
        self.t_11_00 = self.base_date.replace(hour=11)
        self.t_12_00 = self.base_date.replace(hour=12)

    # ─────────────────────────────────────────────────────────────
    # 1. Tests Danh mục phòng họp (PhongHop CRUD & Validation)
    # ─────────────────────────────────────────────────────────────

    def test_unauthenticated_cannot_access_api(self):
        """Chưa đăng nhập gọi API phải bị chặn (401 Unauthorized)."""
        res = self.client.get("/api/meeting-rooms/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res_book = self.client.get("/api/meeting-bookings/")
        self.assertEqual(res_book.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_and_search_meeting_rooms(self):
        """User đăng nhập có thể xem danh sách và tìm kiếm phòng họp."""
        self.client.force_authenticate(user=self.user_staff1)
        res = self.client.get("/api/meeting-rooms/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

        # Tìm kiếm theo tên
        res_search = self.client.get("/api/meeting-rooms/?search=Hội thảo")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertEqual(res_search.data["count"], 1)
        self.assertEqual(res_search.data["results"][0]["ten_phong"], "Phòng Hội thảo A")

    def test_staff_cannot_create_room_without_permission(self):
        """CBNV thường không có quyền tạo phòng mới (403 Forbidden)."""
        self.client.force_authenticate(user=self.user_staff1)
        data = {
            "ten_phong": "Phòng Họp Mới",
            "vi_tri": "Tầng 1",
            "suc_chua": 20,
        }
        res = self.client.post("/api/meeting-rooms/", data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_room_with_validation(self):
        """Admin có quyền tạo phòng mới; kiểm tra validate sức chứa > 0."""
        self.client.force_authenticate(user=self.user_admin)

        # Validate sức chứa <= 0 phải báo lỗi
        invalid_data = {
            "ten_phong": "Phòng Không Hợp Lệ",
            "suc_chua": 0,
        }
        res_fail = self.client.post("/api/meeting-rooms/", invalid_data)
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # Tạo hợp lệ
        valid_data = {
            "ten_phong": "Phòng Họp C",
            "vi_tri": "Tầng 4",
            "suc_chua": 15,
            "thiet_bi": "Máy chiếu, Bảng trắng",
            "is_public": True,
        }
        res_ok = self.client.post("/api/meeting-rooms/", valid_data)
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_ok.data["ten_phong"], "Phòng Họp C")

    def test_cannot_delete_room_with_existing_bookings(self):
        """Không cho phép xóa phòng đã có lịch đặt để bảo toàn lịch sử."""
        # Tạo 1 lịch đặt cho room_a
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Họp giao ban",
            thoi_gian_bat_dau=self.t_08_00,
            thoi_gian_ket_thuc=self.t_09_00,
        )

        self.client.force_authenticate(user=self.user_admin)
        res = self.client.delete(f"/api/meeting-rooms/{self.room_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Không thể xóa phòng", res.data["error"])

        # Phòng B chưa có lịch -> được xóa thành công
        res_b = self.client.delete(f"/api/meeting-rooms/{self.room_b.id}/")
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)

    # ─────────────────────────────────────────────────────────────
    # 2. Tests Đặt lịch phòng họp & Khóa khung giờ (DatPhongHop)
    # ─────────────────────────────────────────────────────────────

    def test_create_booking_auto_assigns_user_and_department(self):
        """Tạo lịch đặt phòng tự động gắn người đặt và đơn vị từ CBNV profile."""
        self.client.force_authenticate(user=self.user_staff1)

        data = {
            "phong_hop": self.room_a.id,
            "tieu_de": "Họp triển khai công việc tuần 40",
            "thoi_gian_bat_dau": self.t_09_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_10_00.isoformat(),
            "so_nguoi_tham_gia": 12,
        }
        res = self.client.post("/api/meeting-bookings/", data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["tieu_de"], "Họp triển khai công việc tuần 40")
        self.assertEqual(res.data["nguoi_dat_detail"]["username"], "hieu_staff")
        self.assertEqual(res.data["nguoi_dat_detail"]["full_name"], "Nguyễn Phan Minh Hiệu")
        self.assertEqual(res.data["don_vi_to_chuc"], "Phòng Hành chính - Tổng hợp")
        self.assertEqual(res.data["trang_thai"], "da_dat")

    def test_booking_invalid_time_range_fails(self):
        """Bắt đầu >= kết thúc phải báo lỗi validate 400."""
        self.client.force_authenticate(user=self.user_staff1)

        data = {
            "phong_hop": self.room_a.id,
            "tieu_de": "Lịch thời gian ngược",
            "thoi_gian_bat_dau": self.t_10_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_09_00.isoformat(),
        }
        res = self.client.post("/api/meeting-bookings/", data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("thoi_gian_ket_thuc", res.data)

    def test_prevent_overlapping_booking_in_same_room(self):
        """Khung giờ đã được đặt phải bị khóa; ngăn chặn người khác đặt trùng."""
        # Staff 1 đặt từ 09:00 đến 11:00
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Họp Hội đồng",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_11_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        # Staff 2 cố gắng đặt từ 10:00 đến 12:00 cùng phòng A -> phải bị chặn 400
        self.client.force_authenticate(user=self.user_staff2)
        conflict_data = {
            "phong_hop": self.room_a.id,
            "tieu_de": "Họp phòng CNTT",
            "thoi_gian_bat_dau": self.t_10_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_12_00.isoformat(),
        }
        res = self.client.post("/api/meeting-bookings/", conflict_data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = str(res.data)
        self.assertTrue("trùng" in error_msg or "Họp Hội đồng" in error_msg)

    def test_allow_adjacent_bookings_without_collision(self):
        """Hai lịch liền kề nhau (ví dụ 09:00-10:00 và 10:00-11:00) không bị tính là trùng."""
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Họp Ca 1",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_10_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        self.client.force_authenticate(user=self.user_staff2)
        adjacent_data = {
            "phong_hop": self.room_a.id,
            "tieu_de": "Họp Ca 2 Nối Tiếp",
            "thoi_gian_bat_dau": self.t_10_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_11_00.isoformat(),
        }
        res = self.client.post("/api/meeting-bookings/", adjacent_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["tieu_de"], "Họp Ca 2 Nối Tiếp")

    def test_different_rooms_can_have_same_time(self):
        """Khác phòng họp thì có thể đặt cùng một khung giờ bình thường."""
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Họp Phòng A",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_10_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        self.client.force_authenticate(user=self.user_staff2)
        diff_room_data = {
            "phong_hop": self.room_b.id,
            "tieu_de": "Họp Phòng B",
            "thoi_gian_bat_dau": self.t_09_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_10_00.isoformat(),
        }
        res = self.client.post("/api/meeting-bookings/", diff_room_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_cancel_booking_releases_time_slot(self):
        """Hủy lịch giải phóng khung giờ, cho phép người khác đặt lại slot đó."""
        booking = DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Cuộc họp cần hủy",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_10_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        # Chủ lịch hủy cuộc họp
        self.client.force_authenticate(user=self.user_staff1)
        res_cancel = self.client.post(
            f"/api/meeting-bookings/{booking.id}/cancel/",
            {"ly_do_huy": "Hoãn họp do bận công tác"},
        )
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.trang_thai, DatPhongHop.STATUS_DA_HUY)
        self.assertIn("Hoãn họp do bận công tác", booking.ghi_chu)

        # Bây giờ Staff 2 có thể đặt lại chính khung giờ 09:00 - 10:00 đó
        self.client.force_authenticate(user=self.user_staff2)
        rebook_data = {
            "phong_hop": self.room_a.id,
            "tieu_de": "Cuộc họp thay thế",
            "thoi_gian_bat_dau": self.t_09_00.isoformat(),
            "thoi_gian_ket_thuc": self.t_10_00.isoformat(),
        }
        res_rebook = self.client.post("/api/meeting-bookings/", rebook_data)
        self.assertEqual(res_rebook.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_edit_or_cancel_others_booking(self):
        """Người dùng thông thường không thể sửa hoặc hủy lịch của người khác."""
        booking = DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Họp của Hiệu",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_10_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        # Tình cố gắng hủy lịch của Hiệu -> 403 Forbidden
        self.client.force_authenticate(user=self.user_staff2)
        res_cancel = self.client.post(f"/api/meeting-bookings/{booking.id}/cancel/")
        self.assertEqual(res_cancel.status_code, status.HTTP_403_FORBIDDEN)

        # Tình cố gắng cập nhật tiêu đề lịch của Hiệu -> 403 Forbidden
        res_edit = self.client.patch(
            f"/api/meeting-bookings/{booking.id}/",
            {"tieu_de": "Chiếm lịch trái phép"},
        )
        self.assertEqual(res_edit.status_code, status.HTTP_403_FORBIDDEN)

        # Admin có quyền can thiệp hủy lịch
        self.client.force_authenticate(user=self.user_admin)
        res_admin_cancel = self.client.post(f"/api/meeting-bookings/{booking.id}/cancel/")
        self.assertEqual(res_admin_cancel.status_code, status.HTTP_200_OK)

    def test_filter_bookings_by_date(self):
        """Lọc lịch đặt phòng họp theo ngày hoạt động chính xác."""
        self.client.force_authenticate(user=self.user_staff1)

        # Lịch ngày mai
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Lịch ngày mai",
            thoi_gian_bat_dau=self.t_09_00,
            thoi_gian_ket_thuc=self.t_10_00,
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )
        # Lịch 5 ngày sau
        day5 = self.base_date + timedelta(days=5)
        DatPhongHop.objects.create(
            phong_hop=self.room_a,
            nguoi_dat=self.user_staff1,
            tieu_de="Lịch 5 ngày sau",
            thoi_gian_bat_dau=day5.replace(hour=9),
            thoi_gian_ket_thuc=day5.replace(hour=10),
            trang_thai=DatPhongHop.STATUS_DA_DAT,
        )

        date_str = self.base_date.strftime("%Y-%m-%d")
        res = self.client.get(f"/api/meeting-bookings/?date={date_str}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["tieu_de"], "Lịch ngày mai")
