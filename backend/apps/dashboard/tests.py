from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Position
from documents.models import PhamVi, VanBanDen, VanBanDi
from organizations.models import DonVi, KhoiKhuVuc


class DashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        UserModel = get_user_model()
        self.baseline_today_birthday_ids = set(
            UserModel.objects.filter(
                is_active=True,
                ngay_sinh__month=self.today.month,
                ngay_sinh__day=self.today.day,
            ).values_list("pk", flat=True)
        )
        self.baseline_tomorrow_birthday_ids = set(
            UserModel.objects.filter(
                is_active=True,
                ngay_sinh__month=self.tomorrow.month,
                ngay_sinh__day=self.tomorrow.day,
            ).values_list("pk", flat=True)
        )

        khoi = KhoiKhuVuc.objects.create(ten="Khối Hỗ trợ")
        latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest_stt + 1, ten="Phòng Hành chính")
        chuc_vu = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Chuyên viên văn thư"
        )
        UserModel = get_user_model()

        self.staff_user = UserModel.objects.create_user(
            username="staffuser",
            password="password123",
            ho_ten="Cán Bộ Nhân Viên",
            don_vi=don_vi,
            chuc_vu=chuc_vu,
            ngay_sinh=date(1995, self.today.month, self.today.day),
        )
        self.staff_user.user_permissions.add(*Permission.objects.filter(
            codename__in=("view_vanbanden", "view_vanbandi")
        ))
        self.admin_user = UserModel.objects.create_superuser(
            username="adminuser",
            password="password123",
            ho_ten="Quản Trị Viên",
            don_vi=don_vi,
            chuc_vu=chuc_vu,
            ngay_sinh=date(1990, self.tomorrow.month, self.tomorrow.day),
        )

    def test_overview_unauthorized(self):
        """Yêu cầu chưa xác thực phải bị từ chối 401."""
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_overview_authorized_contract(self):
        """Người dùng hợp lệ nhận đủ các khóa của hợp đồng API."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("kpis", "recentIncoming", "recentOutgoing", "recentSigning", "tasks", "meetingRooms", "birthdays"):
            self.assertIn(key, response.data)
        self.assertEqual(
            set(response.data["kpis"]), {"incomingCount", "outgoingCount", "signingCount", "tasksCount"}
        )

    @patch("dashboard.views.tong_quan_dashboard")
    def test_recent_signing_preserves_current_attempt_status(self, mock_signing_overview):
        mock_signing_overview.return_value = {
            "so_cho_ky": 0,
            "gan_day": [{
                "id": 17,
                "tieu_de": "Hồ sơ đã trả sửa",
                "nguoi_trinh": "Người trình",
                "ngay_trinh": timezone.now().isoformat(),
                "trang_thai": "CHO_KY",
                "trang_thai_luot": "YEU_CAU_SUA",
                "nhan_trang_thai": "Chờ người trình sửa",
                "can_toi_ky": False,
            }],
        }
        self.client.force_authenticate(user=self.staff_user)

        item = self.client.get("/api/dashboard/overview/").data["recentSigning"][0]

        self.assertEqual(item["trang_thai"], "CHO_KY")
        self.assertEqual(item["trang_thai_luot"], "YEU_CAU_SUA")
        self.assertEqual(item["status"], "CHO_KY")
        self.assertEqual(item["statusLabel"], "Chờ người trình sửa")

    def test_documents_use_shared_visibility_for_counts_and_recent_lists(self):
        """KPI và 5 bản ghi gần nhất chỉ gồm văn bản mà người gọi được xem."""
        VanBanDen.objects.create(
            nam=self.today.year, so_thu_tu=10, so_hieu="DEN-10", trich_yeu="Đến nội bộ",
            nguoi_tao=self.admin_user, pham_vi=PhamVi.NOI_BO,
        )
        VanBanDen.objects.create(
            nam=self.today.year, so_thu_tu=11, so_hieu="DEN-11", trich_yeu="Đến hạn chế của cán bộ",
            nguoi_tao=self.staff_user, pham_vi=PhamVi.HAN_CHE,
        )
        VanBanDen.objects.create(
            nam=self.today.year, so_thu_tu=12, so_hieu="DEN-12", trich_yeu="Đến hạn chế khác",
            nguoi_tao=self.admin_user, pham_vi=PhamVi.HAN_CHE,
        )
        VanBanDi.objects.create(
            nam=self.today.year, so_thu_tu=10, so_hieu="DI-10", trich_yeu="Đi nội bộ",
            nguoi_tao=self.admin_user, pham_vi=PhamVi.NOI_BO,
        )
        VanBanDi.objects.create(
            nam=self.today.year, so_thu_tu=11, so_hieu="DI-11", trich_yeu="Đi hạn chế của cán bộ",
            nguoi_tao=self.staff_user, pham_vi=PhamVi.HAN_CHE,
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["kpis"]["incomingCount"], 2)
        self.assertEqual(response.data["kpis"]["outgoingCount"], 2)
        self.assertEqual(
            {doc["code"] for doc in response.data["recentIncoming"]}, {"DEN-10", "DEN-11"}
        )
        self.assertEqual(
            {doc["code"] for doc in response.data["recentOutgoing"]}, {"DI-10", "DI-11"}
        )
        self.assertEqual(response.data["meetingRooms"], [])

        # Superuser chỉ thấy văn bản HAN_CHE do chính mình tạo.
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.data["kpis"]["incomingCount"], 2)
        self.assertEqual(response.data["kpis"]["outgoingCount"], 1)
        self.assertNotIn("DI-11", {doc["code"] for doc in response.data["recentOutgoing"]})

    def test_overview_has_no_confidential_data(self):
        """Không còn khóa văn bản mật; superuser không có đường xem riêng."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertNotIn("confidentialCount", response.data["kpis"])
        self.assertNotIn("confidential_total", response.data["stats"])

    def test_overview_birthdays_today_and_tomorrow(self):
        """Sinh nhật hôm nay và ngày mai vẫn đọc từ bảng nhân viên."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        labels = {b["label"] for b in response.data["birthdays"]}
        self.assertEqual(labels, {"Hôm nay", "Ngày mai"})

    def test_tasks_match_work_visibility_and_status(self):
        from work.models import Task, TaskAttachment, TaskComment, TaskStatus
        from dashboard.views import _tasks

        own = Task.objects.create(title="Visible task", created_by=self.staff_user,
                                  due_date=self.today, requirement="Review")
        Task.objects.create(title="Other task", created_by=self.admin_user,
                            due_date=self.today, requirement="Review")
        # Hidden tasks remain visible to their creator, as in the work API.
        hidden = Task.objects.create(title="Creator hidden task", created_by=self.staff_user,
                                     due_date=self.today, requirement="Review", is_public=False)
        result = _tasks(self.staff_user, self.today)
        self.assertEqual({row["id"] for row in result}, {str(own.pk), str(hidden.pk)})
        self.assertTrue(all(row["workStatus"] == TaskStatus.CHO_XU_LY for row in result))
        # Evidence takes precedence over the deadline in the domain status selector.
        comment = TaskComment.objects.create(task=own, author=self.staff_user, content="Evidence")
        TaskAttachment.objects.create(task=own, comment=comment, kind="BANG_CHUNG",
                                      file="proof.pdf", uploaded_by=self.staff_user)
        own.due_date = self.today - timedelta(days=1)
        own.created_date = own.due_date
        own.save(update_fields=["due_date", "created_date"])
        result = {row["id"]: row for row in _tasks(self.staff_user, self.today)}
        self.assertEqual(result[str(own.pk)]["workStatus"], TaskStatus.CHO_DUYET)
        self.assertEqual(result[str(own.pk)]["status"], "pending")
        self.assertEqual(len(_tasks(self.admin_user, self.today)), 3)

    def test_resources_match_template_visibility_before_limit(self):
        from document_templates.models import DanhMucTaiLieu, TaiLieuChiTiet
        from document_templates.selectors import visible_resources
        from dashboard.views import _resources

        category = DanhMucTaiLieu.objects.create(
            ten_tai_lieu="Templates", nguoi_lap=self.admin_user
        )
        for i in range(6):
            TaiLieuChiTiet.objects.create(dm_tai_lieu=category, ky_hieu=f"PRIVATE-{i}",
                tieu_de="Private", ngay_dang=self.today, hien_thi="NOI_BO_PHONG_BAN",
                nguoi_tao=self.admin_user, don_vi_id=None)
        for code, creator, unit, visibility, validity in (
            ("PUBLIC", self.admin_user, None, "TAT_CA", "CON_HIEU_LUC"),
            ("OWN", self.staff_user, None, "NOI_BO_PHONG_BAN", "CON_HIEU_LUC"),
            ("DEPT", self.admin_user, self.staff_user.don_vi_id, "NOI_BO_PHONG_BAN", "CON_HIEU_LUC"),
            ("EXPIRED", self.staff_user, None, "TAT_CA", "HET_HIEU_LUC"),
        ):
            TaiLieuChiTiet.objects.create(dm_tai_lieu=category, ky_hieu=code,
                tieu_de=code, ngay_dang=self.today, hien_thi=visibility,
                nguoi_tao=creator, don_vi_id=unit, hieu_luc=validity)
        expected = set(visible_resources(TaiLieuChiTiet.objects.all(), self.staff_user)
                       .filter(hieu_luc="CON_HIEU_LUC").values_list("ky_hieu", flat=True))
        self.assertEqual(expected, {"PUBLIC", "OWN", "DEPT"})
        self.assertEqual({row["code"] for row in _resources(self.staff_user)}, expected)
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual({row["code"] for row in response.data["resources"]}, expected)


class DashboardOverviewPayloadTests(DashboardAPITests):
    """Đặc tả nội dung từng phần của /api/dashboard/overview/ (giá trị, thứ tự, giới hạn, giá trị mặc định)."""

    def _at(self, month, day, hour=9):
        return timezone.make_aware(datetime(self.today.year, month, day, hour))

    def test_recent_incoming_payload(self):
        from documents.models import VanBanDenAttachment

        docs = []
        for i in range(6):
            docs.append(VanBanDen.objects.create(
                nam=self.today.year, so_thu_tu=100 + i, so_hieu=f"DEN-{100 + i}", trich_yeu=f"Đến {i}",
                nguoi_tao=self.admin_user, pham_vi=PhamVi.NOI_BO, ngay_den=self._at(1, 1 + i),
                ngay_van_ban=self._at(1, 1 + i),
                noi_ban_hanh="" if i == 5 else f"Cơ quan {i}",
            ))
        newest = docs[5]
        newest.ngay_van_ban = self._at(1, 20)
        newest.save(update_fields=["ngay_van_ban"])
        att_docx = VanBanDenAttachment.objects.create(document=newest, name="a.DOCX", path="den/a.docx",
                                                      created_at=self._at(2, 1))
        att_png = VanBanDenAttachment.objects.create(document=newest, name="b.png", path="den/b.png",
                                                     created_at=self._at(2, 2))
        VanBanDenAttachment.objects.create(document=newest, name="c.xlsx", path="den/c.xlsx",
                                           created_at=self._at(2, 3), is_deleted=True)
        att_noext = VanBanDenAttachment.objects.create(document=newest, name="scan", path="den/scan",
                                                       created_at=self._at(2, 4))

        self.client.force_authenticate(user=self.staff_user)
        data = self.client.get("/api/dashboard/overview/").data
        self.assertEqual(data["kpis"]["incomingCount"], 6)
        self.assertEqual(data["stats"]["incoming_total"], 6)
        self.assertEqual([row["code"] for row in data["recentIncoming"]],
                         ["DEN-105", "DEN-104", "DEN-103", "DEN-102", "DEN-101"])
        self.assertEqual(data["recentIncoming"][0], {
            "id": newest.pk,
            "code": "DEN-105",
            "title": "Đến 5",
            "date": "20/01/" + str(self.today.year),
            "sender": "Cơ quan ban hành",
            "scope": PhamVi.NOI_BO,
            "attachments": [
                {"name": "a.DOCX", "url": att_docx.path, "type": "word", "size": ""},
                {"name": "b.png", "url": att_png.path, "type": "image", "size": ""},
                {"name": "scan", "url": att_noext.path, "type": "pdf", "size": ""},
            ],
        })
        self.assertEqual(data["recentIncoming"][1]["sender"], "Cơ quan 4")
        self.assertEqual(data["recentIncoming"][1]["date"], "05/01/" + str(self.today.year))
        self.assertEqual(data["recentIncoming"][1]["attachments"], [])
        self.assertEqual(data["recent_incoming"], data["recentIncoming"])

    def test_recent_outgoing_payload(self):
        from documents.models import VanBanDiAttachment

        doc = VanBanDi.objects.create(
            nam=self.today.year, so_thu_tu=200, so_hieu="DI-200", trich_yeu="Đi 200",
            nguoi_tao=self.admin_user, pham_vi=PhamVi.NOI_BO, ngay_ban_hanh=self._at(3, 4), ngay_van_ban=None, nguoi_ky="",
        )
        older = VanBanDi.objects.create(
            nam=self.today.year - 1, so_thu_tu=201, so_hieu="DI-201", trich_yeu="Đi năm trước",
            nguoi_tao=self.admin_user, pham_vi=PhamVi.NOI_BO,
            ngay_ban_hanh=timezone.make_aware(datetime(self.today.year - 1, 12, 31, 9)),
            ngay_van_ban=None, nguoi_ky="Giám đốc",
        )
        att = VanBanDiAttachment.objects.create(document=doc, name="bao-cao.xls", path="di/bao-cao.xls")

        self.client.force_authenticate(user=self.staff_user)
        data = self.client.get("/api/dashboard/overview/").data
        self.assertEqual(data["kpis"]["outgoingCount"], 1)
        self.assertEqual(data["recentOutgoing"], [
            {
                "id": doc.pk,
                "code": "DI-200",
                "title": "Đi 200",
                "date": "04/03/" + str(self.today.year),
                "recipient": "Nơi nhận",
                "scope": PhamVi.NOI_BO,
                "attachments": [{"name": "bao-cao.xls", "url": att.path, "type": "excel", "size": ""}],
            },
            {
                "id": older.pk,
                "code": "DI-201",
                "title": "Đi năm trước",
                "date": "31/12/" + str(self.today.year - 1),
                "recipient": "Giám đốc",
                "scope": PhamVi.NOI_BO,
                "attachments": [],
            },
        ])

    def test_tasks_payload_and_pending_count(self):
        from work.models import Task

        tasks = [
            Task.objects.create(title=f"Task {i}", created_by=self.staff_user,
                                due_date=self.today + timedelta(days=1), requirement="Review")
            for i in range(22)
        ]
        self.client.force_authenticate(user=self.staff_user)
        data = self.client.get("/api/dashboard/overview/").data
        self.assertEqual(len(data["tasks"]), 20)
        self.assertEqual(data["tasks"][0], {
            "id": str(tasks[-1].pk),
            "title": "Task 21",
            "due": (self.today + timedelta(days=1)).strftime("%d/%m/%Y"),
            "status": "processing",
            "statusLabel": "Chờ xử lý",
            "workStatus": "CHO_XU_LY",
            "variant": "info",
        })
        self.assertEqual([row["id"] for row in data["tasks"]], [str(t.pk) for t in reversed(tasks[2:])])
        self.assertEqual(data["kpis"]["tasksCount"], 20)
        self.assertEqual(data["stats"]["tasks_pending"], 20)

    def test_resources_payload(self):
        from document_templates.models import ChiTietTaiLieuAttachment, DanhMucTaiLieu, TaiLieuChiTiet

        category = DanhMucTaiLieu.objects.create(ten_tai_lieu="Mẫu", nguoi_lap=self.admin_user)
        rows = [
            TaiLieuChiTiet.objects.create(dm_tai_lieu=category, ky_hieu=code, tieu_de=f"Mẫu {i}",
                                          ngay_dang=self.today, hien_thi="TAT_CA", nguoi_tao=self.admin_user)
            for i, code in enumerate(["MAU-0", None, "", "MAU-3", "MAU-4", "MAU-5"])
        ]
        ChiTietTaiLieuAttachment.objects.create(document=rows[0], name="old.pdf", path="r/old.pdf",
                                                is_deleted=True)
        ChiTietTaiLieuAttachment.objects.create(document=rows[0], name="mau.xlsx", path="r/mau.xlsx")
        ChiTietTaiLieuAttachment.objects.create(document=rows[0], name="mau.pdf", path="r/mau.pdf")
        ChiTietTaiLieuAttachment.objects.create(document=rows[3], name="khong-duoi", path="r/khong-duoi")

        self.client.force_authenticate(user=self.staff_user)
        data = self.client.get("/api/dashboard/overview/").data
        self.assertEqual(data["resources"], [
            {"code": "MAU-0", "title": "Mẫu 0", "format": "XLSX"},
            {"code": f"BM-{rows[1].pk:02d}", "title": "Mẫu 1", "format": "DOCX"},
            {"code": f"BM-{rows[2].pk:02d}", "title": "Mẫu 2", "format": "DOCX"},
            {"code": "MAU-3", "title": "Mẫu 3", "format": "DOCX"},
            {"code": "MAU-4", "title": "Mẫu 4", "format": "DOCX"},
        ])

    def test_birthdays_payload(self):
        UserModel = get_user_model()
        UserModel.objects.create_user(
            username="inactive_birthday", password="password123", ho_ten="Đã nghỉ",
            ngay_sinh=date(1990, self.today.month, self.today.day), is_active=False,
        )
        no_name = UserModel.objects.create_user(
            username="no_name_birthday", password="password123", ho_ten="",
            ngay_sinh=date(1991, self.tomorrow.month, self.tomorrow.day),
        )
        no_name.refresh_from_db()

        self.client.force_authenticate(user=self.staff_user)
        data = self.client.get("/api/dashboard/overview/").data
        today_label = self.today.strftime("%d/%m") + " (Hôm nay)"
        tomorrow_label = self.tomorrow.strftime("%d/%m") + " (Ngày mai)"
        birthdays = {row["id"]: row for row in data["birthdays"]}
        self.assertEqual(
            set(birthdays),
            self.baseline_today_birthday_ids
            | self.baseline_tomorrow_birthday_ids
            | {self.staff_user.pk, self.admin_user.pk, no_name.pk},
        )
        self.assertEqual(birthdays[self.staff_user.pk], {
            "id": self.staff_user.pk,
            "name": "Cán Bộ Nhân Viên",
            "fullName": "Cán Bộ Nhân Viên",
            "full_name": "Cán Bộ Nhân Viên",
            "birthdate": today_label,
            "position": "Chuyên viên văn thư",
            "roleTitle": "Chuyên viên văn thư",
            "department": "Phòng Hành chính",
            "unit": "Phòng Hành chính",
            "isToday": True,
            "label": "Hôm nay",
        })
        self.assertEqual(birthdays[no_name.pk]["name"], "no_name_birthday")
        self.assertEqual(birthdays[no_name.pk]["position"], no_name.chuc_vu.name)
        self.assertEqual(birthdays[no_name.pk]["department"], no_name.don_vi.ten)
        self.assertEqual(birthdays[no_name.pk]["birthdate"], tomorrow_label)
        self.assertFalse(birthdays[no_name.pk]["isToday"])
        self.assertTrue(birthdays[self.staff_user.pk]["isToday"])
        self.assertIn(
            {
                "full_name": "Cán Bộ Nhân Viên",
                "department": "Phòng Hành chính",
                "position": "Chuyên viên văn thư",
            },
            data["birthdays_by_day"]["today"],
        )
        tomorrow_birthdays = data["birthdays_by_day"]["tomorrow"]
        self.assertIn(
            {"full_name": "Quản Trị Viên", "department": "Phòng Hành chính", "position": "Chuyên viên văn thư"},
            tomorrow_birthdays,
        )
        self.assertIn(
            {"full_name": "no_name_birthday", "department": no_name.don_vi.ten, "position": no_name.chuc_vu.name},
            tomorrow_birthdays,
        )
        self.assertEqual(data["meetingRooms"], [])
        self.assertEqual(data["today_meetings"], [])

    @patch("dashboard.views.tong_quan_dashboard")
    def test_overview_continues_when_signing_selector_fails(self, mock_signing):
        """Kiểm thử khi selector module Trình ký thất bại thì endpoint overview vẫn hoạt động bình thường."""
        mock_signing.side_effect = RuntimeError("Database connection lost in signing module")
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/dashboard/overview/")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["kpis"]["signingCount"], 0)
        self.assertEqual(data["recentSigning"], [])
        self.assertIn("recentIncoming", data)
        self.assertIn("recentOutgoing", data)
        self.assertIn("tasks", data)
