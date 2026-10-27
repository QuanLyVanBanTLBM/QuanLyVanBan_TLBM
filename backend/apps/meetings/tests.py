"""
Unit tests cho phân hệ Phòng họp (Issue #22 - Nhóm 7).

Kiểm thử toàn diện:
1. Model MeetingRoom: default, validator, __str__
2. API MeetingRoomViewSet: CRUD, validation, search, filter, pagination, permission
"""

from datetime import timedelta, datetime, time, date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from unittest import mock, skipUnless
import threading

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from meetings.models import MeetingRoom, MeetingBooking

User = get_user_model()


def _column_info(table, column):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT udt_name, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
            [table, column],
        )
        return cursor.fetchone()


def _constraint_names(table):
    with connection.cursor() as cursor:
        cursor.execute("SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass", [table])
        return {row[0] for row in cursor.fetchall()}


def ensure_permissions_seeded():
    """Đảm bảo các quyền RBAC chuẩn luôn có trong auth_permission của DB test."""
    from authorization.rbac_seed import PERMISSIONS, EXTRA_PERMISSIONS
    with connection.cursor() as cursor:
        for name, codename, module_ten in [*PERMISSIONS, *EXTRA_PERMISSIONS]:
            cursor.execute(
                "INSERT INTO auth_permission (name, codename, module_ten) "
                "SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM auth_permission WHERE codename = %s)",
                [name, codename, module_ten, codename],
            )


class MeetingRoomModelTestCase(TestCase):
    """Kiểm thử cấp Model cho MeetingRoom."""

    def test_create_room_defaults(self):
        room = MeetingRoom.objects.create(name="Phòng Hội thảo A")
        self.assertEqual(room.name, "Phòng Hội thảo A")
        self.assertEqual(room.location, "")
        self.assertEqual(room.capacity, 10)
        self.assertEqual(room.amenities, "")
        self.assertTrue(room.is_public)
        self.assertEqual(room.ghi_chu, "")
        self.assertEqual(str(room), "Phòng Hội thảo A (10 chỗ)")

    def test_room_capacity_validator(self):
        room = MeetingRoom(name="Phòng Test Lỗi", capacity=0)
        with self.assertRaises(ValidationError):
            room.full_clean()


class MeetingRoomAPITestCase(APITestCase):
    """Kiểm thử API endpoints cho /api/meeting-rooms/."""

    def setUp(self):
        ensure_permissions_seeded()
        # Admin user (có mọi quyền)
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@tlbm.vn",
            password="AdminPassword123!",
        )

        # Staff user thông thường (có quyền xem lịch phòng họp, chưa có quyền ghi MeetingRoom)
        self.regular_user = User.objects.create_user(
            username="regular_user",
            email="regular@tlbm.vn",
            password="RegularPassword123!",
        )
        view_perm = Permission.objects.filter(codename="view_schedule_phonghop")
        self.regular_user.user_permissions.add(*view_perm)

        # Staff user có quyền quản lý phòng họp
        self.manager_user = User.objects.create_user(
            username="manager_user",
            email="manager@tlbm.vn",
            password="ManagerPassword123!",
        )
        manager_perms = Permission.objects.filter(
            codename__in=["view_schedule_phonghop", "add_phonghop", "change_phonghop", "delete_phonghop"]
        )
        self.manager_user.user_permissions.add(*manager_perms)

        # Tạo sẵn một số phòng họp mẫu
        self.room1 = MeetingRoom.objects.create(
            name="Phòng Hội trường A",
            location="Tầng 1, Tòa Hành chính",
            capacity=100,
            amenities="Hệ thống âm thanh hội nghị, 2 máy chiếu, 4 micro",
            is_public=True,
            ghi_chu="Dành cho hội nghị lớn",
        )
        self.room2 = MeetingRoom.objects.create(
            name="Phòng Họp B",
            location="Tầng 2, Tòa Kỹ thuật",
            capacity=15,
            amenities="Tivi 75 inch, bảng viết kính",
            is_public=False,
            ghi_chu="Đang sửa điều hòa",
        )

    def test_unauthenticated_access_denied(self):
        """Người dùng chưa đăng nhập không thể truy cập API."""
        response = self.client.get("/api/meeting-rooms/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_rooms_paginated(self):
        """Lấy danh sách phòng họp có phân trang: User thường chỉ thấy phòng public, Quản lý thấy tất cả."""
        # User thường chỉ thấy phòng is_public=True
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/meeting-rooms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Phòng Hội trường A")

        # Quản lý có quyền change_phonghop thấy cả phòng nội bộ
        self.client.force_authenticate(user=self.manager_user)
        res_mgr = self.client.get("/api/meeting-rooms/")
        self.assertEqual(res_mgr.status_code, status.HTTP_200_OK)
        self.assertEqual(res_mgr.data["count"], 2)

    def test_list_rooms_all_unpaginated(self):
        """Tham số all=true trả về danh sách thuần không phân trang."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.get("/api/meeting-rooms/?all=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)

    def test_user_without_view_schedule_permission_denied(self):
        """Tài khoản đăng nhập nhưng không có view_schedule_phonghop bị 403."""
        no_perm_user = User.objects.create_user(
            username="no_perm_user",
            email="noperm@tlbm.vn",
            password="NoPermPassword123!",
        )
        self.client.force_authenticate(user=no_perm_user)
        res = self.client.get("/api/meeting-rooms/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_room_detail(self):
        """Xem chi tiết một phòng họp."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f"/api/meeting-rooms/{self.room1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Phòng Hội trường A")
        self.assertEqual(response.data["capacity"], 100)

    def test_search_rooms(self):
        """Tìm kiếm phòng họp theo từ khóa (tên, vị trí, thiết bị)."""
        self.client.force_authenticate(user=self.manager_user)

        # Tìm theo tên
        res1 = self.client.get("/api/meeting-rooms/?search=Hội trường")
        self.assertEqual(res1.data["count"], 1)
        self.assertEqual(res1.data["results"][0]["name"], "Phòng Hội trường A")

        # Tìm theo vị trí
        res2 = self.client.get("/api/meeting-rooms/?search=Kỹ thuật")
        self.assertEqual(res2.data["count"], 1)
        self.assertEqual(res2.data["results"][0]["name"], "Phòng Họp B")

        # Tìm theo thiết bị
        res3 = self.client.get("/api/meeting-rooms/?search=máy chiếu")
        self.assertEqual(res3.data["count"], 1)

    def test_filter_by_is_public(self):
        """Lọc phòng họp theo trạng thái công khai / nội bộ."""
        # Manager thấy cả 2
        self.client.force_authenticate(user=self.manager_user)
        res_public = self.client.get("/api/meeting-rooms/?is_public=true")
        self.assertEqual(res_public.data["count"], 1)
        self.assertEqual(res_public.data["results"][0]["name"], "Phòng Hội trường A")

        res_hidden = self.client.get("/api/meeting-rooms/?is_public=false")
        self.assertEqual(res_hidden.data["count"], 1)
        self.assertEqual(res_hidden.data["results"][0]["name"], "Phòng Họp B")

        # Regular user không bao giờ thấy phòng is_public=false
        self.client.force_authenticate(user=self.regular_user)
        res_reg_hidden = self.client.get("/api/meeting-rooms/?is_public=false")
        self.assertEqual(res_reg_hidden.data["count"], 0)

    def test_create_room_as_manager(self):
        """User có quyền có thể tạo phòng họp mới."""
        self.client.force_authenticate(user=self.manager_user)
        payload = {
            "name": "Phòng Họp Ban Giám Đốc",
            "location": "Tầng 5, Tòa Nhà A",
            "capacity": 20,
            "amenities": "Micro cổ ngỗng, màn hình tương tác thông minh",
            "is_public": True,
            "ghi_chu": "Phục vụ các cuộc họp lãnh đạo cấp cao",
        }
        response = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Phòng Họp Ban Giám Đốc")
        self.assertTrue(MeetingRoom.objects.filter(name="Phòng Họp Ban Giám Đốc").exists())

    def test_create_room_permission_denied_for_regular_user(self):
        """User không có quyền tạo phòng sẽ bị chặn 403."""
        self.client.force_authenticate(user=self.regular_user)
        payload = {
            "name": "Phòng Không Được Phép",
            "capacity": 10,
        }
        response = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_room_validation_empty_name(self):
        """Tên phòng rỗng hoặc chỉ có khoảng trắng phải báo lỗi 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "   ",
            "capacity": 15,
        }
        response = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_create_room_validation_duplicate_name(self):
        """Trùng tên phòng họp (kể cả khác hoa thường) phải báo lỗi 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "phòng hội trường a",  # self.room1 đã có "Phòng Hội trường A"
            "capacity": 50,
        }
        response = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_create_room_validation_invalid_capacity(self):
        """Sức chứa <= 0 phải báo lỗi 400."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Phòng Sức Chứa Sai",
            "capacity": 0,
        }
        response = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("capacity", response.data)

    def test_update_room_put_and_patch(self):
        """Cập nhật phòng họp thành công qua PUT và PATCH."""
        self.client.force_authenticate(user=self.manager_user)

        # PATCH: chỉ sửa sức chứa và trạng thái
        patch_res = self.client.patch(
            f"/api/meeting-rooms/{self.room2.id}/",
            {"capacity": 25, "is_public": True},
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.room2.refresh_from_db()
        self.assertEqual(self.room2.capacity, 25)
        self.assertTrue(self.room2.is_public)

        # PUT: cập nhật toàn bộ
        put_payload = {
            "name": "Phòng Họp B (Đã Nâng Cấp)",
            "location": "Tầng 2, Tòa Kỹ thuật",
            "capacity": 30,
            "amenities": "Tivi 85 inch, Bảng thông minh",
            "is_public": True,
            "ghi_chu": "Hoàn tất sửa chữa",
        }
        put_res = self.client.put(f"/api/meeting-rooms/{self.room2.id}/", put_payload)
        self.assertEqual(put_res.status_code, status.HTTP_200_OK)
        self.room2.refresh_from_db()
        self.assertEqual(self.room2.name, "Phòng Họp B (Đã Nâng Cấp)")

    def test_delete_room_success(self):
        """Xóa phòng họp khi chưa có dữ liệu ràng buộc."""
        self.client.force_authenticate(user=self.manager_user)
        response = self.client.delete(f"/api/meeting-rooms/{self.room2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MeetingRoom.objects.filter(id=self.room2.id).exists())

    def test_delete_room_forbidden_for_regular_user(self):
        """User không có quyền delete_phonghop bị 403."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.delete(f"/api/meeting-rooms/{self.room1.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MeetingBookingModelTestCase(TestCase):
    """Kiểm thử cấp Model cho MeetingBooking."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_booker",
            email="booker@tlbm.vn",
            password="Password123!",
        )
        self.room = MeetingRoom.objects.create(
            name="Phòng Hội Thảo Model Test",
            capacity=20,
        )
        self.booking_date = timezone.localdate() + timedelta(days=7)

    def test_create_booking_success_model(self):
        booking = MeetingBooking.objects.create(
            room=self.room,
            organizer=self.user,
            title="Họp Bàn Giao",
            date=self.booking_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=10,
        )
        self.assertEqual(booking.trang_thai, MeetingBooking.Status.CONFIRMED)
        self.assertIn("Họp Bàn Giao", str(booking))

    def test_clean_end_time_before_start_time(self):
        booking = MeetingBooking(
            room=self.room,
            organizer=self.user,
            title="Họp Lỗi Giờ",
            date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(9, 0),
            attendees_count=5,
        )
        with self.assertRaises(ValidationError):
            booking.clean()

    def test_clean_capacity_exceeded(self):
        booking = MeetingBooking(
            room=self.room,
            organizer=self.user,
            title="Họp Quá Tải",
            date=self.booking_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=25,  # sức chứa phòng là 20
        )
        with self.assertRaises(ValidationError):
            booking.clean()


class MeetingBookingAPITestCase(APITestCase):
    """Kiểm thử API endpoints cho /api/meeting-bookings/."""

    def setUp(self):
        ensure_permissions_seeded()
        self.admin_user = User.objects.create_superuser(
            username="booking_admin",
            email="admin@tlbm.vn",
            password="AdminPassword123!",
        )
        self.user1 = User.objects.create_user(
            username="user_one",
            email="user1@tlbm.vn",
            password="UserOnePass123!",
        )
        self.user2 = User.objects.create_user(
            username="user_two",
            email="user2@tlbm.vn",
            password="UserTwoPass123!",
        )

        booking_perms = Permission.objects.filter(
            codename__in=["add_datphonghop", "change_own_datphonghop", "view_schedule_phonghop"]
        )
        self.user1.user_permissions.add(*booking_perms)
        self.user2.user_permissions.add(*booking_perms)

        self.room1 = MeetingRoom.objects.create(
            name="Phòng Họp VIP 1",
            capacity=15,
            is_public=True,
        )
        self.room2 = MeetingRoom.objects.create(
            name="Phòng Họp VIP 2",
            capacity=10,
            is_public=True,
        )

        # Mốc tương đối so với ngày chạy để test không phụ thuộc đồng hồ thật
        self.booking_date = timezone.localdate() + timedelta(days=7)
        self.base_time = timezone.make_aware(
            datetime.combine(self.booking_date, time(0, 0)), timezone.get_current_timezone()
        )
        self.booking1 = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp sáng của User 1",
            date=self.booking_date,
            start_time=time(9, 0),
            end_time=time(10, 30),
            attendees_count=8,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )

    def test_booking_fixture_uses_a_coherent_future_date(self):
        """Booking date anchors align and its aware start remains in the future."""
        self.assertGreater(self.booking_date, timezone.localdate())
        self.assertEqual(self.base_time.date(), self.booking_date)
        self.assertEqual(self.booking1.date, self.booking_date)
        booking_start = timezone.make_aware(
            datetime.combine(self.booking1.date, self.booking1.start_time),
            timezone.get_current_timezone(),
        )
        self.assertGreater(booking_start, timezone.now())

    def test_list_bookings_authenticated(self):
        """User đã xác thực có thể xem danh sách lịch đặt."""
        self.client.force_authenticate(user=self.user2)
        res = self.client.get("/api/meeting-bookings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # response phân trang có results
        count = res.data.get("count", len(res.data.get("results", [])))
        self.assertGreaterEqual(count, 1)

    def test_filter_bookings_by_room(self):
        """Lọc lịch đặt theo phòng họp."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.get(f"/api/meeting-bookings/?room={self.room1.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", [])
        for item in results:
            self.assertEqual(item["room"], self.room1.id)

    def test_create_booking_success(self):
        """Tạo lịch đặt phòng mới thành công và tự gán organizer."""
        self.client.force_authenticate(user=self.user2)
        payload = {
            "room": self.room1.id,
            "title": "Họp Triển Khai Chiều",
            "date": self.booking_date.isoformat(),
            "start_time": "14:00",
            "end_time": "16:00",
            "attendees_count": 10,
            "purpose": "Yêu cầu máy chiếu",
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["organizer"], self.user2.id)
        self.assertEqual(res.data["title"], "Họp Triển Khai Chiều")

    def test_create_booking_conflict_error(self):
        """Chặn đặt trùng khung giờ trong cùng phòng họp."""
        self.client.force_authenticate(user=self.user2)
        # Booking1 diễn ra từ 09:00 đến 10:30 phòng 1
        # Thử đặt từ 10:00 đến 11:30 phòng 1 -> Bị từ chối
        payload = {
            "room": self.room1.id,
            "title": "Họp Cố Tình Trùng Lịch",
            "date": self.booking_date.isoformat(),
            "start_time": "10:00",
            "end_time": "11:30",
            "attendees_count": 5,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_capacity_error(self):
        """Chặn đặt số người vượt quá sức chứa phòng."""
        self.client.force_authenticate(user=self.user2)
        payload = {
            "room": self.room2.id,  # sức chứa 10
            "title": "Họp Quá Đông",
            "date": self.booking_date.isoformat(),
            "start_time": "14:00",
            "end_time": "15:00",
            "attendees_count": 50,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("attendees_count", res.data)

    def test_cancel_booking_action(self):
        """Hủy lịch đặt phòng giải phóng khung giờ."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post(
            f"/api/meeting-bookings/{self.booking1.id}/cancel/",
            {"cancel_reason": "Hoãn họp sang tuần sau"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking1.refresh_from_db()
        self.assertEqual(self.booking1.trang_thai, MeetingBooking.Status.CANCELLED)
        self.assertIn("Hoãn họp sang tuần sau", self.booking1.purpose)

    def test_rebook_after_cancellation(self):
        """Sau khi lịch cũ bị hủy, người khác có thể đặt vào cùng khung giờ đó."""
        # 1. User 1 hủy lịch
        self.client.force_authenticate(user=self.user1)
        self.client.post(f"/api/meeting-bookings/{self.booking1.id}/cancel/")

        # 2. User 2 đặt vào chính khung giờ đó -> Thành công!
        self.client.force_authenticate(user=self.user2)
        payload = {
            "room": self.room1.id,
            "title": "Họp Khẩn Cấp Chiếm Slot Đã Hủy",
            "date": self.booking_date.isoformat(),
            "start_time": "09:00",
            "end_time": "10:30",
            "attendees_count": 6,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_regular_user_cannot_cancel_other_user_booking(self):
        """User thường không thể hủy lịch của người khác."""
        self.client.force_authenticate(user=self.user2)
        res = self.client.post(f"/api/meeting-bookings/{self.booking1.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_cancel_any_booking(self):
        """Admin có quyền hủy bất kỳ lịch đặt phòng nào."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post(
            f"/api/meeting-bookings/{self.booking1.id}/cancel/",
            {"cancel_reason": "Admin điều phối phòng"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking1.refresh_from_db()
        self.assertEqual(self.booking1.trang_thai, MeetingBooking.Status.CANCELLED)

    def test_create_booking_with_ddl_english_payload(self):
        """Tạo lịch đặt phòng bằng payload tiếng Anh theo đúng DDL SQL_Fix4."""
        self.client.force_authenticate(user=self.user1)
        target_date = (self.base_time + timedelta(days=2)).date()
        payload = {
            "room": self.room1.id,
            "title": "Họp Chiến Lược Quý 4",
            "date": target_date.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "attendees_count": 6,
            "purpose": "Đánh giá KPI và kế hoạch ngân sách",
            "trang_thai": "CONFIRMED",
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Họp Chiến Lược Quý 4")
        self.assertEqual(res.data["trang_thai"], "CONFIRMED")
        self.assertEqual(res.data["attendees_count"], 6)

    def test_cannot_book_maintenance_room(self):
        """Không cho phép đặt phòng họp đang ở trạng thái MAINTENANCE."""
        m_room = MeetingRoom.objects.create(
            name="Phòng Bảo Trì 101",
            location="Tầng 1",
            capacity=20,
            trang_thai=MeetingRoom.Status.MAINTENANCE,
        )
        self.client.force_authenticate(user=self.user1)
        payload = {
            "room": m_room.id,
            "title": "Họp Thử Phòng Bảo Trì",
            "date": (self.base_time + timedelta(days=3)).date().isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "attendees_count": 5,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_unavailable_room(self):
        """Không cho phép đặt phòng họp đang ở trạng thái UNAVAILABLE."""
        u_room = MeetingRoom.objects.create(
            name="Phòng Khóa Tạm Thời",
            location="Tầng 2",
            capacity=10,
            trang_thai=MeetingRoom.Status.UNAVAILABLE,
        )
        self.client.force_authenticate(user=self.user1)
        payload = {
            "room": u_room.id,
            "title": "Họp Thử Phòng Khóa",
            "date": (self.booking_date + timedelta(days=3)).isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
            "attendees_count": 4,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_with_change_any_datphonghop_can_cancel_other_booking(self):
        """User có quyền change_any_datphonghop có thể hủy lịch của người khác."""
        perm_user = User.objects.create_user(
            username="dispatcher_user",
            email="dispatcher@tlbm.vn",
            password="DispatcherPass123!",
        )
        perm = Permission.objects.get(codename="change_any_datphonghop")
        perm_user.user_permissions.add(perm)

        self.client.force_authenticate(user=perm_user)
        res = self.client.post(
            f"/api/meeting-bookings/{self.booking1.id}/cancel/",
            {"cancel_reason": "Điều phối bởi bộ phận hành chính"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking1.refresh_from_db()
        self.assertEqual(self.booking1.trang_thai, MeetingBooking.Status.CANCELLED)

    def test_staff_user_without_add_phonghop_cannot_create_room(self):
        """User có is_staff=True nhưng không có quyền add_phonghop bị 403 Forbidden."""
        staff_only_user = User.objects.create_user(
            username="staff_only_user",
            email="staff@tlbm.vn",
            password="StaffPassword123!",
            is_staff=True,  # Chỉ có cờ admin site, không có quyền nghiệp vụ
        )
        self.client.force_authenticate(user=staff_only_user)
        res = self.client.post("/api/meeting-rooms/", {
            "name": "Phòng Tạo Lậu",
            "capacity": 10,
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_status_param_returns_400(self):
        """Truyền trang_thai không thuộc enum (ví dụ ?trang_thai=bogus) phải trả về 400 thay vì 500 DataError."""
        self.client.force_authenticate(user=self.admin_user)
        # Phòng họp
        res_rooms = self.client.get("/api/meeting-rooms/?trang_thai=BOGUS")
        self.assertEqual(res_rooms.status_code, status.HTTP_400_BAD_REQUEST)

        # Lịch đặt phòng
        res_bookings = self.client.get("/api/meeting-bookings/?trang_thai=BOGUS")
        self.assertEqual(res_bookings.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_room_id_param_returns_400(self):
        """Truyền room không phải số (ví dụ ?room=abc) phải trả về 400 thay vì 500 ValueError."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get("/api/meeting-bookings/?room=abc")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_room_name_max_length_100(self):
        """Tên phòng dài hơn 100 ký tự phải báo lỗi 400 thay vì DataError varchar(100)."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/meeting-rooms/", {
            "name": "A" * 105,
            "capacity": 10,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_capacity_max_value_overflow(self):
        """Sức chứa vượt quá giới hạn 32-bit integer phải báo lỗi 400 thay vì DataError integer overflow."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/meeting-rooms/", {
            "name": "Phòng Quá Lớn",
            "capacity": 99999999999999,
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_room_without_is_public_preserves_privacy(self):
        """PUT phòng họp không gửi trường is_public phải giữ nguyên giá trị cũ (không bị reset về True)."""
        self.client.force_authenticate(user=self.admin_user)
        private_room = MeetingRoom.objects.create(
            name="Phòng Cơ Mật HĐQT",
            capacity=10,
            is_public=False,
        )
        res = self.client.put(f"/api/meeting-rooms/{private_room.id}/", {
            "name": "Phòng Cơ Mật HĐQT (Cập nhật)",
            "capacity": 12,
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        private_room.refresh_from_db()
        self.assertFalse(private_room.is_public)
        self.assertEqual(private_room.capacity, 12)

    def test_regular_user_cannot_book_private_room(self):
        """Người dùng thường không có quyền change_phonghop thì không được đặt lịch hoặc dời lịch vào phòng nội bộ."""
        private_room = MeetingRoom.objects.create(
            name="Phòng Riêng VIP Ban Giám Đốc",
            capacity=8,
            is_public=False,
        )
        self.client.force_authenticate(user=self.user2)
        payload = {
            "room": private_room.id,
            "title": "Họp Thử Phòng Riêng",
            "date": (self.base_time.date()).isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "attendees_count": 4,
        }
        # 1. Thử tạo mới vào phòng nội bộ -> 400 Bad Request với key privateRoomForbidden
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        room_err = str(res.data.get("room", ""))
        self.assertIn("meetings.messages.privateRoomForbidden", room_err)

        # 2a. Thử sửa lịch của người khác (booking1 của user1) -> 403 Forbidden
        res_other = self.client.patch(f"/api/meeting-bookings/{self.booking1.id}/", {"room": private_room.id})
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        # 2b. Chủ sở hữu (user1 không có change_phonghop) dời lịch của mình sang phòng nội bộ -> 400 Bad Request
        self.client.force_authenticate(user=self.user1)
        res_patch = self.client.patch(f"/api/meeting-bookings/{self.booking1.id}/", {"room": private_room.id})
        self.assertEqual(res_patch.status_code, status.HTTP_400_BAD_REQUEST)
        patch_err = str(res_patch.data.get("room", ""))
        self.assertIn("meetings.messages.privateRoomForbidden", patch_err)

        # 3. Admin hoặc người có quyền change_phonghop thì đặt được -> 201 Created
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res_admin.status_code, status.HTTP_201_CREATED)

    def test_past_booking_returns_completed_status_and_filtered(self):
        """Lịch đã diễn ra trong quá khứ tự động hiển thị COMPLETED và lọc được bằng ?trang_thai=COMPLETED."""
        self.client.force_authenticate(user=self.admin_user)
        yesterday = timezone.localtime(timezone.now()).date() - timedelta(days=1)
        past_booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp hôm qua",
            date=yesterday,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        # 1. GET chi tiết lịch họp -> trạng thái động trả về COMPLETED
        res = self.client.get(f"/api/meeting-bookings/{past_booking.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["trang_thai"], "COMPLETED")

        # 2. Lọc theo ?trang_thai=COMPLETED -> tìm thấy lịch này
        res_list = self.client.get("/api/meeting-bookings/?trang_thai=COMPLETED")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res_list.data.get("results", [])]
        self.assertIn(past_booking.id, ids)

        # 3. Lọc theo ?trang_thai=CONFIRMED -> không chứa lịch này
        res_confirmed = self.client.get("/api/meeting-bookings/?trang_thai=CONFIRMED")
        self.assertEqual(res_confirmed.status_code, status.HTTP_200_OK)
        confirmed_ids = [item["id"] for item in res_confirmed.data.get("results", [])]
        self.assertNotIn(past_booking.id, confirmed_ids)

    def test_cancel_past_booking_rejected(self):
        """Hủy lịch đã kết thúc trong quá khứ phải trả về 400 kèm key bookingAlreadyEnded."""
        self.client.force_authenticate(user=self.admin_user)
        yesterday = timezone.localtime(timezone.now()).date() - timedelta(days=1)
        past_booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp hôm qua",
            date=yesterday,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        res = self.client.post(
            f"/api/meeting-bookings/{past_booking.id}/cancel/",
            {"cancel_reason": "Hủy muộn"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("detail"), "meetings.messages.bookingAlreadyEnded")
        # Bản ghi vẫn phải giữ nguyên COMPLETED / CONFIRMED, không bị chuyển sang CANCELLED
        past_booking.refresh_from_db()
        self.assertNotEqual(past_booking.trang_thai, MeetingBooking.Status.CANCELLED)

    def test_update_past_booking_rejected(self):
        """Cập nhật lịch đã kết thúc trong quá khứ phải trả về 400 kèm key bookingAlreadyEnded."""
        self.client.force_authenticate(user=self.admin_user)
        yesterday = timezone.localtime(timezone.now()).date() - timedelta(days=1)
        past_booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp hôm qua",
            date=yesterday,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        res = self.client.put(
            f"/api/meeting-bookings/{past_booking.id}/",
            {"title": "Đổi tiêu đề lịch đã qua"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("detail"), "meetings.messages.bookingAlreadyEnded")

    def test_cancel_booking_reason_saved_without_hardcoded_label(self):
        """Hủy lịch hợp lệ: lý do hủy không được kèm nhãn tiếng Việt viết cứng [Lý do hủy]:"""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post(
            f"/api/meeting-bookings/{self.booking1.id}/cancel/",
            {"cancel_reason": "Thay đổi kế hoạch nội bộ"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking1.refresh_from_db()
        self.assertEqual(self.booking1.trang_thai, MeetingBooking.Status.CANCELLED)
        self.assertNotIn("[Lý do hủy]:", self.booking1.purpose)
        self.assertIn("Thay đổi kế hoạch nội bộ", self.booking1.purpose)

    def test_cancel_booking_without_purpose_formats_separator(self):
        """QA #4: Hủy lịch không có ghi chú ban đầu phải luôn lưu dạng \n---\n<reason> để frontend phân tách."""
        self.client.force_authenticate(user=self.user1)
        booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Lịch không có ghi chú ban đầu",
            date=self.booking_date,
            start_time=time(11, 0),
            end_time=time(12, 0),
            attendees_count=5,
            purpose="",
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        res = self.client.post(
            f"/api/meeting-bookings/{booking.id}/cancel/",
            {"cancel_reason": "Giải phóng phòng để bảo trì"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.trang_thai, MeetingBooking.Status.CANCELLED)
        self.assertEqual(booking.purpose, "\n---\nGiải phóng phòng để bảo trì")
        self.assertEqual(res.data["booking"]["purpose"], "\n---\nGiải phóng phòng để bảo trì")

    def test_cancel_booking_with_initial_purpose_preserves_both(self):
        """QA #4: Hủy lịch có ghi chú ban đầu phải giữ nguyên cả purpose và lý do hủy có phân tách."""
        self.client.force_authenticate(user=self.user1)
        booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Lịch có ghi chú ban đầu",
            date=self.booking_date,
            start_time=time(13, 0),
            end_time=time(14, 0),
            attendees_count=5,
            purpose="Chuẩn bị tài liệu hội thảo",
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        res = self.client.post(
            f"/api/meeting-bookings/{booking.id}/cancel/",
            {"cancel_reason": "Dời sang tuần sau"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.trang_thai, MeetingBooking.Status.CANCELLED)
        self.assertEqual(booking.purpose, "Chuẩn bị tài liệu hội thảo\n---\nDời sang tuần sau")
        self.assertEqual(res.data["booking"]["purpose"], "Chuẩn bị tài liệu hội thảo\n---\nDời sang tuần sau")

    def test_room_name_too_long_error_key(self):
        """Tạo phòng họp có tên > 100 ký tự trả về 400 và key roomNameTooLong."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "P" * 101,
            "capacity": 10,
        }
        res = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.roomNameTooLong", str(res.data))

    def test_room_capacity_too_large_error_key(self):
        """Tạo phòng họp có sức chứa quá lớn trả về 400 và key capacityTooLarge."""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Phòng Siêu Lớn",
            "capacity": 2147483648,
        }
        res = self.client.post("/api/meeting-rooms/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.capacityTooLarge", str(res.data))

    def test_permission_denied_custom_message(self):
        """Người dùng không có quyền nhận 403 với detail meetings.messages.permissionDenied."""
        no_perm_user = User.objects.create_user(
            username="no_perm_user",
            email="noperm@tlbm.vn",
            password="Password123!",
        )
        self.client.force_authenticate(user=no_perm_user)
        res = self.client.post(
            "/api/meeting-rooms/",
            {"name": "Phòng Trái Quyền", "capacity": 10},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("meetings.messages.permissionDenied", str(res.data))

    def test_client_cannot_change_booking_status_directly(self):
        """Client không thể tự ý thay đổi trang_thai sang CANCELLED/COMPLETED qua POST hoặc PUT/PATCH."""
        self.client.force_authenticate(user=self.user1)
        future_date = (timezone.localtime(timezone.now()).date() + timedelta(days=5)).isoformat()

        # 1. POST với trang_thai: CANCELLED vẫn được lưu là CONFIRMED
        payload = {
            "room": self.room1.id,
            "title": "Họp Thử Cố Đổi Trạng Thái",
            "date": future_date,
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "attendees_count": 5,
            "trang_thai": "CANCELLED",
        }
        res_post = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        booking_id = res_post.data["id"]
        booking = MeetingBooking.objects.get(id=booking_id)
        self.assertEqual(booking.trang_thai, MeetingBooking.Status.CONFIRMED)

        # 2. PUT với trang_thai: CANCELLED bị bỏ qua, trang_thai vẫn giữ nguyên CONFIRMED
        res_put = self.client.put(
            f"/api/meeting-bookings/{booking_id}/",
            {
                "title": "Họp Đã Đổi Tên",
                "room": self.room1.id,
                "date": future_date,
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "trang_thai": "CANCELLED",
            },
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.trang_thai, MeetingBooking.Status.CONFIRMED)

    def test_delete_booking_returns_405_and_keeps_record(self):
        """Xóa lịch đặt phòng phải trả về 405 Method Not Allowed và không xóa bản ghi trong DB."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.delete(f"/api/meeting-bookings/{self.booking1.id}/")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn("meetings.messages.deleteBookingNotAllowed", str(res.data))
        self.assertTrue(MeetingBooking.objects.filter(id=self.booking1.id).exists())

    def test_create_past_booking_rejected(self):
        """Không cho phép tạo lịch đặt trong quá khứ, trả về 400 và key bookingInPast."""
        self.client.force_authenticate(user=self.user1)
        yesterday = (timezone.localtime(timezone.now()).date() - timedelta(days=1)).isoformat()
        payload = {
            "room": self.room1.id,
            "title": "Họp Trong Quá Khứ",
            "date": yesterday,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "attendees_count": 5,
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.bookingInPast", str(res.data))

    def test_reschedule_booking_to_past_rejected(self):
        """Không cho phép dời lịch họp hiện tại về ngày/giờ trong quá khứ."""
        self.client.force_authenticate(user=self.user1)
        yesterday = (timezone.localtime(timezone.now()).date() - timedelta(days=1)).isoformat()
        res = self.client.patch(
            f"/api/meeting-bookings/{self.booking1.id}/",
            {"date": yesterday},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.bookingInPast", str(res.data))

    def test_put_room_without_status_preserves_maintenance(self):
        """PUT phòng họp mà không truyền trường trang_thai thì không bị reset về AVAILABLE."""
        self.client.force_authenticate(user=self.admin_user)
        m_room = MeetingRoom.objects.create(
            name="Phòng Đang Sửa",
            capacity=15,
            trang_thai=MeetingRoom.Status.MAINTENANCE,
        )
        res = self.client.put(
            f"/api/meeting-rooms/{m_room.id}/",
            {
                "name": "Phòng Đang Sửa Cập Nhật",
                "capacity": 20,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        m_room.refresh_from_db()
        self.assertEqual(m_room.trang_thai, MeetingRoom.Status.MAINTENANCE)

    def test_update_cancelled_booking_rejected(self):
        """Cập nhật lịch họp đã bị hủy phải trả về 400 kèm key bookingAlreadyCancelled."""
        self.client.force_authenticate(user=self.user1)
        self.booking1.trang_thai = MeetingBooking.Status.CANCELLED
        self.booking1.save(update_fields=["trang_thai"])

        res = self.client.put(
            f"/api/meeting-bookings/{self.booking1.id}/",
            {"title": "Cố Sửa Lịch Đã Hủy"},
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.bookingAlreadyCancelled", str(res.data))

    def test_create_booking_without_title_rejected(self):
        """Tạo lịch họp thiếu tiêu đề hoặc để trống phải trả về 400 kèm key titleRequired."""
        self.client.force_authenticate(user=self.user1)
        future_date = (timezone.localtime(timezone.now()).date() + timedelta(days=5)).isoformat()
        payload = {
            "room": self.room1.id,
            "title": "   ",
            "date": future_date,
            "start_time": "14:00:00",
            "end_time": "15:00:00",
        }
        res = self.client.post("/api/meeting-bookings/", payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.titleRequired", str(res.data))

    def test_staff_cannot_see_other_users_private_room_bookings(self):
        """User thường không thể xem lịch phòng nội bộ của người khác, trừ khi chính mình là người đặt."""
        private_room = MeetingRoom.objects.create(
            name="Phòng Họp Mật HĐQT",
            capacity=10,
            is_public=False,
        )
        future_date = (timezone.localtime(timezone.now()).date() + timedelta(days=10))
        # Booking của admin trong phòng riêng
        admin_booking = MeetingBooking.objects.create(
            room=private_room,
            organizer=self.admin_user,
            title="Họp Mật Của Admin",
            date=future_date,
            start_time=time(14, 0),
            end_time=time(15, 0),
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        # Booking của user1 trong phòng riêng
        user1_booking = MeetingBooking.objects.create(
            room=private_room,
            organizer=self.user1,
            title="Họp Mật Của User 1",
            date=future_date,
            start_time=time(16, 0),
            end_time=time(17, 0),
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )

        # 1. user2 (staff thường, không phải organizer) vào xem danh sách -> không thấy cả 2 lịch phòng riêng
        self.client.force_authenticate(user=self.user2)
        res_user2 = self.client.get("/api/meeting-bookings/")
        ids_user2 = [b["id"] for b in res_user2.data.get("results", [])]
        self.assertNotIn(admin_booking.id, ids_user2)
        self.assertNotIn(user1_booking.id, ids_user2)

        # 2. user1 (chính là organizer của user1_booking) vào xem danh sách -> thấy lịch của mình, không thấy của admin
        self.client.force_authenticate(user=self.user1)
        res_user1 = self.client.get("/api/meeting-bookings/")
        ids_user1 = [b["id"] for b in res_user1.data.get("results", [])]
        self.assertIn(user1_booking.id, ids_user1)
        self.assertNotIn(admin_booking.id, ids_user1)

        # 3. Manager/Admin có quyền change_phonghop -> thấy tất cả
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.get("/api/meeting-bookings/")
        ids_admin = [b["id"] for b in res_admin.data.get("results", [])]
        self.assertIn(admin_booking.id, ids_admin)
        self.assertIn(user1_booking.id, ids_admin)

    def test_trang_thai_field_matches_ddl_column(self):
        """Field trang_thai của MeetingRoom và MeetingBooking dùng đúng cột trang_thai của DDL."""
        self.assertEqual(MeetingRoom._meta.get_field("trang_thai").column, "trang_thai")
        self.assertEqual(MeetingBooking._meta.get_field("trang_thai").column, "trang_thai")

    def test_api_fields_use_ddl_names_only(self):
        """API phòng họp và lịch đặt chỉ trả tên field theo DDL, không kèm bí danh."""
        self.client.force_authenticate(user=self.admin_user)
        room_keys = set(self.client.get(f"/api/meeting-rooms/{self.room1.id}/").data.keys())
        self.assertEqual(room_keys, {
            "id", "name", "location", "capacity", "amenities", "is_public",
            "trang_thai", "ghi_chu", "created_at", "updated_at",
        })
        booking_keys = set(self.client.get(f"/api/meeting-bookings/{self.booking1.id}/").data.keys())
        self.assertEqual(booking_keys, {
            "id", "room", "room_detail", "organizer", "organizer_detail", "department",
            "department_name", "title", "date", "start_time", "end_time", "attendees_count",
            "purpose", "trang_thai", "created_at",
        })

    def test_cancel_already_cancelled_booking_returns_400(self):
        """Hủy lại lịch họp đã bị hủy phải trả về 400 kèm key bookingAlreadyCancelled."""
        self.client.force_authenticate(user=self.user1)
        self.booking1.trang_thai = MeetingBooking.Status.CANCELLED
        self.booking1.save(update_fields=["trang_thai"])
        res = self.client.post(f"/api/meeting-bookings/{self.booking1.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.bookingAlreadyCancelled", str(res.data))

    def test_ongoing_meeting_can_update_title_without_reschedule_error(self):
        """Cuộc họp đang diễn ra có thể cập nhật tiêu đề/ghi chú bằng PUT mà không bị coi là dời lịch về quá khứ."""
        # Cố định "hiện tại" ở giữa ngày để khung -15/+45 phút không vượt qua nửa đêm (#225).
        fixed_now = timezone.make_aware(datetime.combine(timezone.localdate(), time(10, 0)))
        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            self._assert_ongoing_meeting_title_update()

    def _assert_ongoing_meeting_title_update(self):
        now_local = timezone.localtime(timezone.now())
        today = now_local.date()
        start_time = (now_local - timedelta(minutes=15)).time().replace(microsecond=0)
        end_time = (now_local + timedelta(minutes=45)).time().replace(microsecond=0)

        ongoing_booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp đang diễn ra",
            date=today,
            start_time=start_time,
            end_time=end_time,
            trang_thai=MeetingBooking.Status.CONFIRMED,
            attendees_count=5,
        )

        self.client.force_authenticate(user=self.user1)
        payload = {
            "room": self.room1.id,
            "title": "Cuộc họp đang diễn ra - Đã cập nhật tiêu đề",
            "date": today.isoformat(),
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S"),
            "attendees_count": 5,
        }
        res = self.client.put(f"/api/meeting-bookings/{ongoing_booking.id}/", payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ongoing_booking.refresh_from_db()
        self.assertEqual(ongoing_booking.title, "Cuộc họp đang diễn ra - Đã cập nhật tiêu đề")

    def test_adjacent_bookings_allowed(self):
        """Các khung giờ liền kề (trước và sau) không bị coi là trùng giờ và được tạo thành công (201)."""
        self.client.force_authenticate(user=self.user1)
        target_date = (self.booking_date + timedelta(days=2))

        # Booking mốc: 14:00 - 15:00
        base_payload = {
            "room": self.room1.id,
            "title": "Cuộc họp mốc",
            "date": target_date.isoformat(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "attendees_count": 5,
        }
        res_base = self.client.post("/api/meeting-bookings/", base_payload)
        self.assertEqual(res_base.status_code, status.HTTP_201_CREATED)

        # 1. Liền kề trước: 13:00 - 14:00 -> 201 Created
        prev_payload = {
            "room": self.room1.id,
            "title": "Cuộc họp liền kề trước",
            "date": target_date.isoformat(),
            "start_time": "13:00:00",
            "end_time": "14:00:00",
            "attendees_count": 5,
        }
        res_prev = self.client.post("/api/meeting-bookings/", prev_payload)
        self.assertEqual(res_prev.status_code, status.HTTP_201_CREATED)

        # 2. Liền kề sau: 15:00 - 16:00 -> 201 Created
        next_payload = {
            "room": self.room1.id,
            "title": "Cuộc họp liền kề sau",
            "date": target_date.isoformat(),
            "start_time": "15:00:00",
            "end_time": "16:00:00",
            "attendees_count": 5,
        }
        res_next = self.client.post("/api/meeting-bookings/", next_payload)
        self.assertEqual(res_next.status_code, status.HTTP_201_CREATED)

    def test_overlapping_bookings_rejected(self):
        """Các trường hợp trùng giờ (bao trùm, nằm trong, giao đầu, giao đuôi, trùng khớp) bị từ chối 400."""
        self.client.force_authenticate(user=self.user1)
        target_date = (self.booking_date + timedelta(days=3))

        # Booking mốc: 14:00 - 16:00
        base_payload = {
            "room": self.room1.id,
            "title": "Cuộc họp mốc 14-16h",
            "date": target_date.isoformat(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "attendees_count": 5,
        }
        res_base = self.client.post("/api/meeting-bookings/", base_payload)
        self.assertEqual(res_base.status_code, status.HTTP_201_CREATED)

        cases = [
            ("Nằm trọn bên trong", "14:30:00", "15:30:00"),
            ("Bao trùm bên ngoài", "13:30:00", "16:30:00"),
            ("Giao khoảng đầu", "13:30:00", "14:30:00"),
            ("Giao khoảng đuôi", "15:30:00", "16:30:00"),
            ("Trùng khớp hoàn toàn", "14:00:00", "16:00:00"),
        ]
        for desc, st, et in cases:
            with self.subTest(desc=desc):
                payload = {
                    "room": self.room1.id,
                    "title": f"Họp trùng - {desc}",
                    "date": target_date.isoformat(),
                    "start_time": st,
                    "end_time": et,
                    "attendees_count": 5,
                }
                res = self.client.post("/api/meeting-bookings/", payload)
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("meetings.messages.roomTimeConflict", str(res.data))

    def test_reschedule_conflict_rejected_and_data_unchanged(self):
        """Dời lịch vào slot đã bận bị trả về 400, dữ liệu cũ không đổi; sửa tiêu đề không tự xung đột."""
        self.client.force_authenticate(user=self.user1)
        target_date = (self.booking_date + timedelta(days=4))

        # Booking A: 09:00 - 10:00
        booking_a = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp A",
            date=target_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )
        # Booking B: 11:00 - 12:00
        booking_b = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Cuộc họp B",
            date=target_date,
            start_time=time(11, 0),
            end_time=time(12, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )

        # 1. Cố dời Booking B vào khung 09:30 - 10:30 (trùng A) -> 400
        res = self.client.put(
            f"/api/meeting-bookings/{booking_b.id}/",
            {
                "room": self.room1.id,
                "title": "Cuộc họp B dời giờ",
                "date": target_date.isoformat(),
                "start_time": "09:30:00",
                "end_time": "10:30:00",
                "attendees_count": 5,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("meetings.messages.roomTimeConflict", str(res.data))

        # Kiểm tra Booking B trong DB vẫn giữ nguyên thời gian và tiêu đề cũ
        booking_b.refresh_from_db()
        self.assertEqual(booking_b.start_time, time(11, 0))
        self.assertEqual(booking_b.end_time, time(12, 0))
        self.assertEqual(booking_b.title, "Cuộc họp B")

        # 2. Cập nhật chỉ tiêu đề của Booking A -> 200 OK, không tự báo trùng với chính mình
        res_a = self.client.put(
            f"/api/meeting-bookings/{booking_a.id}/",
            {
                "room": self.room1.id,
                "title": "Cuộc họp A - Tiêu đề cập nhật",
                "date": target_date.isoformat(),
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "attendees_count": 5,
            },
        )
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        booking_a.refresh_from_db()
        self.assertEqual(booking_a.title, "Cuộc họp A - Tiêu đề cập nhật")

    def test_update_booking_permissions(self):
        """Phân quyền cập nhật lịch: người đặt (200), user khác chỉ có change_own (403), user có change_any (200)."""
        target_date = (self.booking_date + timedelta(days=5))
        booking = MeetingBooking.objects.create(
            room=self.room1,
            organizer=self.user1,
            title="Lịch họp của User 1",
            date=target_date,
            start_time=time(14, 0),
            end_time=time(15, 0),
            attendees_count=5,
            trang_thai=MeetingBooking.Status.CONFIRMED,
        )

        # 1. User 1 (người đặt, có change_own_datphonghop) sửa lịch của mình -> 200 OK
        self.client.force_authenticate(user=self.user1)
        res_own = self.client.patch(
            f"/api/meeting-bookings/{booking.id}/",
            {"title": "User 1 đổi tiêu đề"},
        )
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # 2. User 2 (chỉ có add_datphonghop và change_own_datphonghop, không phải người đặt) sửa -> 403 Forbidden
        self.client.force_authenticate(user=self.user2)
        res_other = self.client.patch(
            f"/api/meeting-bookings/{booking.id}/",
            {"title": "User 2 cố tình sửa"},
        )
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("meetings.messages.permissionDenied", str(res_other.data))

        # 3. User có quyền change_any_datphonghop (không phải người đặt) sửa -> 200 OK
        dispatcher = User.objects.create_user(
            username="dispatcher_updater",
            email="disp_up@tlbm.vn",
            password="Password123!",
        )
        perm = Permission.objects.get(codename="change_any_datphonghop")
        dispatcher.user_permissions.add(perm)

        self.client.force_authenticate(user=dispatcher)
        res_disp = self.client.patch(
            f"/api/meeting-bookings/{booking.id}/",
            {"title": "Điều phối viên sửa tiêu đề"},
        )
        self.assertEqual(res_disp.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.title, "Điều phối viên sửa tiêu đề")

    def test_booking_boundary_conditions(self):
        """Kiểm thử giá trị biên: attendees_count (đúng capacity: 201; > capacity / <= 0: 400), end <= start (400), title rỗng (400)."""
        fixed_now = timezone.make_aware(datetime.combine(timezone.localdate(), time(10, 0)))
        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            self.client.force_authenticate(user=self.user1)
            target_date = (timezone.localdate() + timedelta(days=6)).isoformat()

            # Room1 capacity = 15
            # 1. attendees_count == capacity (15) -> 201 Created
            res_exact = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp đúng sức chứa",
                "date": target_date,
                "start_time": "13:00:00",
                "end_time": "14:00:00",
                "attendees_count": 15,
            })
            self.assertEqual(res_exact.status_code, status.HTTP_201_CREATED)

            # 2. attendees_count > capacity (16) -> 400 Bad Request kèm key capacityExceeded
            res_over = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp quá sức chứa",
                "date": target_date,
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "attendees_count": 16,
            })
            self.assertEqual(res_over.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.capacityExceeded", str(res_over.data))

            # 3. attendees_count == 0 -> 400 Bad Request kèm key attendeesRequired
            res_zero = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp 0 người",
                "date": target_date,
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "attendees_count": 0,
            })
            self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.attendeesMustBePositive", str(res_zero.data))

            # 4. attendees_count < 0 -> 400 Bad Request kèm key attendeesMustBePositive
            res_neg = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp số người âm",
                "date": target_date,
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "attendees_count": -5,
            })
            self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.attendeesMustBePositive", str(res_neg.data))

            # 5. end_time < start_time -> 400 Bad Request kèm key invalidTimeRange
            res_reverse = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp giờ ngược",
                "date": target_date,
                "start_time": "15:00:00",
                "end_time": "14:00:00",
                "attendees_count": 5,
            })
            self.assertEqual(res_reverse.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.invalidTimeRange", str(res_reverse.data))

            # 6. end_time == start_time -> 400 Bad Request kèm key invalidTimeRange
            res_equal = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "Họp giờ bằng nhau",
                "date": target_date,
                "start_time": "15:00:00",
                "end_time": "15:00:00",
                "attendees_count": 5,
            })
            self.assertEqual(res_equal.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.invalidTimeRange", str(res_equal.data))

            # 7. title rỗng hoặc chỉ có khoảng trắng -> 400 Bad Request kèm key titleRequired
            res_blank_title = self.client.post("/api/meeting-bookings/", {
                "room": self.room1.id,
                "title": "   ",
                "date": target_date,
                "start_time": "15:00:00",
                "end_time": "16:00:00",
                "attendees_count": 5,
            })
            self.assertEqual(res_blank_title.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("meetings.messages.titleRequired", str(res_blank_title.data))


@skipUnless(connection.vendor == "postgresql", "Kiểu ENUM và ràng buộc EXCLUDE chỉ có trên PostgreSQL")
class MeetingsReleaseDdlSchemaTestCase(TestCase):
    """Schema tạo từ migration phải khớp release_DDL.sql (meetings_meetingroom, meetings_meetingbooking)."""

    def test_trang_thai_uses_ddl_enum_types(self):
        self.assertEqual(_column_info("meetings_meetingroom", "trang_thai"), ("meetingroom_status", "NO", "'AVAILABLE'::meetingroom_status"))
        self.assertEqual(
            _column_info("meetings_meetingbooking", "trang_thai"),
            ("meetingbooking_status", "NO", "'CONFIRMED'::meetingbooking_status"),
        )

    def test_nullable_columns_match_ddl(self):
        for table, column in [
            ("meetings_meetingroom", "amenities"),
            ("meetings_meetingroom", "ghi_chu"),
            ("meetings_meetingbooking", "purpose"),
        ]:
            self.assertEqual(_column_info(table, column)[1], "YES", f"{table}.{column}")

    def test_ddl_constraints_exist(self):
        self.assertIn("meetings_meetingroom_capacity_check", _constraint_names("meetings_meetingroom"))
        self.assertTrue(
            {"meetings_meetingbooking_attendees_count_check", "chk_booking_time", "excl_room_time"}
            <= _constraint_names("meetings_meetingbooking")
        )

    def test_db_rejects_invalid_values(self):
        user = User.objects.create_user(username="ddl_schema_user", email="ddl@tlbm.vn", password="Password123!")
        room = MeetingRoom.objects.create(name="Phòng Kiểm Tra Schema", location="Tầng 1", capacity=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MeetingRoom.objects.filter(pk=room.pk).update(capacity=0)
        booking_date = timezone.localdate() + timedelta(days=30)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MeetingBooking.objects.create(room=room, organizer=user, title="Giờ ngược", date=booking_date,
                                          start_time=time(10, 0), end_time=time(9, 0))
        MeetingBooking.objects.create(room=room, organizer=user, title="Lịch gốc", date=booking_date,
                                      start_time=time(9, 0), end_time=time(10, 0))
        with self.assertRaises(IntegrityError), transaction.atomic():
            MeetingBooking.objects.create(room=room, organizer=user, title="Trùng giờ", date=booking_date,
                                          start_time=time(9, 30), end_time=time(10, 30))
        # Lịch đã hủy không giữ khung giờ
        MeetingBooking.objects.create(room=room, organizer=user, title="Đã hủy", date=booking_date,
                                      start_time=time(9, 30), end_time=time(10, 30),
                                      trang_thai=MeetingBooking.Status.CANCELLED)


class MeetingBookingConcurrencyTestCase(TransactionTestCase):
    """Kiểm thử tương tranh: 2 request đồng thời đặt cùng phòng và khung giờ."""

    @classmethod
    def _fixture_setup(cls):
        pass

    @classmethod
    def _fixture_teardown(cls):
        pass

    def tearDown(self):
        super().tearDown()
        MeetingBooking.objects.filter(title="Họp Tranh Chấp Slot").delete()
        MeetingRoom.objects.filter(name="Phòng Họp Tương Tranh").delete()
        User.objects.filter(username="concurrent_user").delete()

    def test_concurrent_bookings_same_slot_exactly_one_succeeds(self):
        ensure_permissions_seeded()
        user = User.objects.create_user(
            username="concurrent_user",
            email="conc@tlbm.vn",
            password="Password123!",
        )
        booking_perms = Permission.objects.filter(
            codename__in=["add_datphonghop", "change_own_datphonghop", "view_schedule_phonghop"]
        )
        user.user_permissions.add(*booking_perms)

        room = MeetingRoom.objects.create(
            name="Phòng Họp Tương Tranh",
            capacity=20,
            is_public=True,
        )
        target_date = (timezone.localdate() + timedelta(days=14)).isoformat()
        payload = {
            "room": room.id,
            "title": "Họp Tranh Chấp Slot",
            "date": target_date,
            "start_time": "15:00:00",
            "end_time": "16:00:00",
            "attendees_count": 5,
        }

        results = []
        barrier = threading.Barrier(2)

        def make_booking():
            connection.close()
            client = APIClient()
            client.force_authenticate(user=user)
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError:
                pass
            res = client.post("/api/meeting-bookings/", payload)
            results.append(res.status_code)
            connection.close()

        t1 = threading.Thread(target=make_booking)
        t2 = threading.Thread(target=make_booking)

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Một request thành công 201, một request bị từ chối 400, không có lỗi 500
        self.assertEqual(results.count(status.HTTP_201_CREATED), 1, f"Results: {results}")
        self.assertEqual(results.count(status.HTTP_400_BAD_REQUEST), 1, f"Results: {results}")
        self.assertNotIn(status.HTTP_500_INTERNAL_SERVER_ERROR, results)

        # Số bản ghi đặt phòng trong DB chính xác là 1
        created_count = MeetingBooking.objects.filter(
            room=room,
            date=target_date,
            start_time=time(15, 0),
            end_time=time(16, 0),
            trang_thai=MeetingBooking.Status.CONFIRMED,
        ).count()
        self.assertEqual(created_count, 1)


