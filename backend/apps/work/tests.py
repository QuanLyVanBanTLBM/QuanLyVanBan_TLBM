import datetime
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.management import call_command
from django.core.signals import request_finished
from django.db import close_old_connections
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from document_storage import get_document_storage
from organizations.models import DonVi, KhoiKhuVuc
from documents.models import PhamVi, VanBanDen, VanBanDi

from work.models import (
    AttachmentKind,
    DocumentKind,
    ParticipantRole,
    Task,
    TaskAttachment,
    TaskComment,
    TaskDonVi,
    TaskParticipant,
    TaskStatus,
)

User = get_user_model()

TEMP_STORAGE_ROOT = tempfile.mkdtemp(prefix="work-tests-")


def pdf_file(name="bang-chung.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 noi dung thu", content_type="application/pdf")


@override_settings(
    DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT,
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
)
class WorkTestBase(APITestCase):
    """Dữ liệu dùng chung: người tạo, chủ trì, chỉ đạo, tham gia, người ngoài, quản trị viên."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_STORAGE_ROOT, ignore_errors=True)

    def setUp(self):
        self.today = timezone.localdate()
        # Dùng ID và STT sau dữ liệu nền do migration tạo, không giả định bảng đơn vị rỗng.
        default_region = KhoiKhuVuc.objects.create(ten="Khối kiểm thử mặc định")
        latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        self.default_unit = DonVi.objects.create(
            khoi=default_region, stt_uu_tien=latest_stt + 1, ten="Phòng ban kiểm thử mặc định"
        )
        self.creator = User.objects.create_user("nguoitao", ho_ten="Trần Phương Duy", don_vi=self.default_unit)
        self.host = User.objects.create_user("chutri", ho_ten="Phan Quốc Dũng", don_vi=self.default_unit)
        self.director = User.objects.create_user("chidao", ho_ten="Nguyễn Thu Hiền", don_vi=self.default_unit)
        self.member = User.objects.create_user("thamgia", ho_ten="Nguyễn Bình Minh", don_vi=self.default_unit)
        self.outsider = User.objects.create_user("nguoingoai", don_vi=self.default_unit)
        self.admin = User.objects.create_superuser(
            "quantri", "Admin@123", email="quantri@example.com", don_vi=self.default_unit
        )
        permissions = [
            Permission.objects.get(codename=codename)
            for codename in ("add_congviec", "view_vanbanden", "view_vanbandi")
        ]
        self.creator.user_permissions.add(*permissions)
        self.units = {}
        for unit_id in (3, 5, 7, 8, 9):
            latest_stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
            self.units[unit_id] = DonVi.objects.create(
                khoi=default_region,
                stt_uu_tien=latest_stt + 1,
                ten=f"Phòng ban kiểm thử {unit_id}",
            )

    # ----- tiện ích -----

    def days(self, offset):
        return self.today + datetime.timedelta(days=offset)

    def make_task(self, created_offset=0, due_offset=3, is_public=True, title="Công việc thử", **extra):
        task = Task.objects.create(
            title=title,
            requirement="Yêu cầu thử",
            created_date=self.days(created_offset),
            due_date=self.days(due_offset),
            created_by=self.creator,
            is_public=is_public,
            **extra,
        )
        # vai_tro là ENUM: không dùng bulk_create (UNNEST ép varchar[]).
        for user, role in (
            (self.host, ParticipantRole.CHU_TRI),
            (self.director, ParticipantRole.CHI_DAO),
            (self.member, ParticipantRole.THAM_GIA),
        ):
            TaskParticipant.objects.create(task=task, user=user, role=role)
        return task

    def add_evidence(self, task, user=None, name="bang-chung.pdf"):
        """Tạo file bằng chứng đúng cách: nằm trong một ý kiến của người nộp."""
        author = user or self.member
        comment = TaskComment.objects.create(task=task, author=author, content="Nộp kết quả")
        return TaskAttachment.objects.create(
            task=task,
            comment=comment,
            kind=AttachmentKind.BANG_CHUNG,
            file=pdf_file(name),
            uploaded_by=author,
        )

    def status_of(self, task):
        return Task.objects.with_status().get(pk=task.pk).status

    def login(self, user):
        self.client.force_authenticate(user=user)

    def task_url(self, task, suffix=""):
        return f"/api/work/tasks/{task.pk}/{suffix}"


# ==========================================================================
# ===== KHU VỰC: Tính trạng thái, quyền xem, API trang chủ =====
# ==========================================================================

class TaskStatusTests(WorkTestBase):
    def test_moi_tao_la_cho_xu_ly(self):
        self.assertEqual(self.status_of(self.make_task()), TaskStatus.CHO_XU_LY)

    def test_da_mo_la_dang_xu_ly(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.assertEqual(self.status_of(task), TaskStatus.DANG_XU_LY)

    def test_co_bang_chung_la_cho_duyet(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.add_evidence(task)
        self.assertEqual(self.status_of(task), TaskStatus.CHO_DUYET)

    def test_cho_duyet_khong_bi_dong_bang_khi_qua_han(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        self.add_evidence(task)
        self.assertEqual(self.status_of(task), TaskStatus.CHO_DUYET)

    def test_da_duyet_la_hoan_thanh(self):
        task = self.make_task(approved_at=timezone.now(), approved_by=self.host)
        self.add_evidence(task)
        self.assertEqual(self.status_of(task), TaskStatus.HOAN_THANH)

    def test_da_mo_va_het_han_la_chua_hoan_thanh(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        self.assertEqual(self.status_of(task), TaskStatus.CHUA_HOAN_THANH)

    def test_chua_mo_va_het_han_la_qua_han(self):
        task = self.make_task(created_offset=-5, due_offset=-1)
        self.assertEqual(self.status_of(task), TaskStatus.QUA_HAN)

    def test_han_la_hom_nay_chua_tinh_het_han(self):
        task = self.make_task(created_offset=-2, due_offset=0)
        self.assertEqual(self.status_of(task), TaskStatus.CHO_XU_LY)

    def test_xoa_het_bang_chung_quay_ve_dang_xu_ly(self):
        task = self.make_task(first_opened_at=timezone.now())
        evidence = self.add_evidence(task)
        evidence.delete()
        self.assertEqual(self.status_of(task), TaskStatus.DANG_XU_LY)

    def test_loc_trang_thai_chay_trong_db(self):
        self.make_task()
        self.make_task(created_offset=-5, due_offset=-1)
        self.make_task(created_offset=-5, due_offset=-2)
        overdue = Task.objects.with_status().filter(status=TaskStatus.QUA_HAN)
        self.assertEqual(overdue.count(), 2)
        self.assertIn("CASE", str(overdue.query).upper())


class TaskVisibilityTests(WorkTestBase):
    def visible_ids(self, user):
        return set(Task.objects.visible_to(user).values_list("id", flat=True))

    def test_nguoi_lien_quan_thay_cong_viec_dang_hien_thi(self):
        task = self.make_task()
        for user in (self.creator, self.host, self.director, self.member):
            self.assertIn(task.pk, self.visible_ids(user))
        self.assertNotIn(task.pk, self.visible_ids(self.outsider))

    def test_cong_viec_dang_an_chi_nguoi_tao_va_admin_thay(self):
        task = self.make_task(is_public=False)
        self.assertIn(task.pk, self.visible_ids(self.creator))
        self.assertIn(task.pk, self.visible_ids(self.admin))
        for user in (self.host, self.director, self.member, self.outsider):
            self.assertNotIn(task.pk, self.visible_ids(user))

    def test_khong_bi_trung_dong_khi_nguoi_tao_kiem_vai_tro(self):
        task = self.make_task()
        TaskParticipant.objects.filter(task=task, user=self.member).update(user=self.creator)
        self.assertEqual(Task.objects.visible_to(self.creator).filter(pk=task.pk).count(), 1)

    def test_nguoi_ngoai_goi_chi_tiet_nhan_404(self):
        task = self.make_task()
        self.login(self.outsider)
        response = self.client.get(self.task_url(task))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Hãy quay lại danh sách", response.data["detail"])


class TaskDepartmentVisibilityTests(WorkTestBase):
    """
    Quyền xem 3 lớp: người liên quan / view_all_congviec / view_dept_congviec.
    Quyền theo phòng ban lấy đơn vị từ chính người dùng (accounts_employee.don_vi_id).
    """

    def setUp(self):
        super().setUp()
        self.task = self.make_task()
        TaskDonVi.objects.create(task=self.task, don_vi=self.units[7])

    def grant(self, user, *codenames):
        # Nhóm 7 seed sẵn 7 quyền *_congviec theo SQL_Fix4 (codename trần, content_type_id=NULL),
        # backend RBAC kiểm theo codename trần — chỉ cần gán quyền đã có, không tự tạo.
        from django.contrib.auth.models import Permission

        user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
        # Django cache quyền trên từng instance, phải lấy lại bản mới.
        return User.objects.get(pk=user.pk)

    def visible_ids(self, user):
        return set(Task.objects.visible_to(user).values_list("id", flat=True))

    def test_nguoi_ngoai_khong_co_quyen_thi_khong_thay(self):
        self.assertNotIn(self.task.pk, self.visible_ids(self.outsider))

    def test_quyen_xem_toan_he_thong_thay_het_ke_ca_viec_dang_an(self):
        hidden = self.make_task(is_public=False, title="Việc ẩn")
        user = self.grant(self.outsider, "view_all_congviec")
        self.assertEqual(self.visible_ids(user), {self.task.pk, hidden.pk})

    def test_quyen_xem_theo_phong_ban_chi_thay_viec_cua_don_vi_minh(self):
        khac = self.make_task(title="Việc phòng khác")
        TaskDonVi.objects.create(task=khac, don_vi=self.units[9])
        user = self.grant(self.outsider, "view_dept_congviec")
        user.don_vi = self.units[7]
        self.assertEqual(self.visible_ids(user), {self.task.pk})

    def test_co_don_vi_nhung_khong_co_quyen_thi_khong_thay(self):
        user = self.grant(self.outsider, "view_congviec")
        user.don_vi = self.units[7]
        self.assertNotIn(self.task.pk, self.visible_ids(user))

    def test_quyen_phong_ban_khong_thay_cong_viec_dang_an(self):
        hidden = self.make_task(is_public=False, title="Việc ẩn của phòng")
        TaskDonVi.objects.create(task=hidden, don_vi=self.units[7])
        user = self.grant(self.outsider, "view_dept_congviec")
        user.don_vi = self.units[7]
        self.assertEqual(self.visible_ids(user), {self.task.pk})

    def test_api_danh_sach_dung_quyen_phong_ban(self):
        user = self.grant(self.outsider, "view_dept_congviec")
        user.don_vi = self.units[7]
        self.login(user)
        response = self.client.get("/api/work/tasks/")
        self.assertEqual([item["id"] for item in response.data["results"]], [self.task.pk])


class TaskDepartmentAndDocumentApiTests(WorkTestBase):
    """Gắn công việc với nhiều phòng/ban và với văn bản của nhóm 2."""

    def setUp(self):
        super().setUp()
        # Văn bản HAN_CHE: chỉ người tạo/người nhận/đơn vị nhận xem được (quy tắc selectors nhóm 2).
        # Dùng HAN_CHE để test "người ngoài không có quyền xem" đúng với van_ban_xem_duoc,
        # vì văn bản NOI_BO công khai (hien_thi=True) thì ai cũng xem được.
        self.document_incoming = VanBanDen.objects.create(
            nam=self.today.year,
            so_hieu="VB-DEN-WORK",
            trich_yeu="Văn bản đến cho kiểm thử công việc",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
        )
        self.document_outgoing = VanBanDi.objects.create(
            nam=self.today.year,
            so_hieu="VB-DI-WORK",
            trich_yeu="Văn bản đi cho kiểm thử công việc",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
        )

    def payload(self, **overrides):
        data = {
            "title": "Việc có phòng ban",
            "createdDate": self.today.isoformat(),
            "dueDate": self.days(3).isoformat(),
            "requirement": "Yêu cầu",
            "hostId": self.host.pk,
            "directorIds": [self.director.pk],
            "participantIds": [self.member.pk],
        }
        data.update(overrides)
        return data

    def test_tao_cong_viec_gan_nhieu_phong_ban(self):
        self.login(self.creator)
        unit_ids = [self.units[3].pk, self.units[5].pk]
        response = self.client.post("/api/work/tasks/", self.payload(donViIds=unit_ids), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["donViIds"], unit_ids)
        self.assertEqual(TaskDonVi.objects.filter(task_id=response.data["id"]).count(), 2)

    def test_sua_danh_sach_phong_ban(self):
        task = self.make_task()
        TaskDonVi.objects.create(task=task, don_vi=self.units[3])
        self.login(self.creator)
        unit_ids = [self.units[5].pk, self.units[8].pk]
        response = self.client.patch(self.task_url(task), {"donViIds": unit_ids}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["donViIds"], unit_ids)

    def test_gan_cong_viec_voi_van_ban(self):
        self.login(self.creator)
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(documentType="vanbanden", documentId=self.document_incoming.pk),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["documentType"], "vanbanden")
        self.assertEqual(response.data["documentId"], self.document_incoming.pk)

    def test_nguoi_tao_khong_co_quyen_xem_khong_duoc_gan_van_ban_noi_bo(self):
        self.outsider.user_permissions.add(Permission.objects.get(codename="add_congviec"))
        self.login(self.outsider)
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(documentType="vanbanden", documentId=self.document_incoming.pk),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Không tìm thấy văn bản hoặc bạn không có quyền xem", str(response.data["documentId"]))
        self.assertFalse(Task.objects.exists())

    def test_task_details_hide_document_reference_without_document_permission(self):
        from types import SimpleNamespace
        from work.serializers import TaskDetailSerializer

        task = self.make_task(
            document_type=DocumentKind.VAN_BAN_DEN,
            document_id=self.document_incoming.pk,
        )
        data = TaskDetailSerializer(
            task,
            context={"request": SimpleNamespace(user=self.outsider)},
        ).data

        self.assertIsNone(data["documentType"])
        self.assertIsNone(data["documentId"])

    def test_thieu_mot_nua_thong_tin_van_ban_bi_chan(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(documentType="vanbandi"), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("đủ cả loại văn bản và mã văn bản", response.data["documentType"][0])

    def test_chi_con_hai_loai_van_ban(self):
        """Issue #83: GVHD bỏ hẳn văn bản mật, enum chỉ còn văn bản đến và văn bản đi."""
        self.assertEqual(list(DocumentKind.values), ["vanbanden", "vanbandi"])

        self.login(self.creator)
        for loai, document in (
            (DocumentKind.VAN_BAN_DEN, self.document_incoming),
            (DocumentKind.VAN_BAN_DI, self.document_outgoing),
        ):
            response = self.client.post(
                "/api/work/tasks/",
                self.payload(documentType=loai, documentId=document.pk),
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            self.assertEqual(response.data["documentType"], loai)

    def test_loai_van_ban_da_bo_bi_tu_choi(self):
        """Loại văn bản đã bị bỏ khỏi hệ thống thì API phải từ chối."""
        self.login(self.creator)
        loai_da_bo = "vanban" + "mat"  # ghép chuỗi để mã nguồn không còn chứa từ khóa đã gỡ
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(documentType=loai_da_bo, documentId=1),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Văn bản đến hoặc Văn bản đi", response.data["documentType"][0])

    def test_loai_van_ban_khong_hop_le(self):
        self.login(self.creator)
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(documentType="linh tinh", documentId=1),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskTableMappingTests(WorkTestBase):
    """Model phải trỏ đúng tên bảng và tên cột trong CSDL PM đã chốt."""

    def test_ten_bang_dung_chuan_pm(self):
        self.assertEqual(Task._meta.db_table, "task_congviec")
        self.assertEqual(TaskParticipant._meta.db_table, "task_participant")
        self.assertEqual(TaskComment._meta.db_table, "task_comment")
        self.assertEqual(TaskAttachment._meta.db_table, "task_attachment")
        self.assertEqual(TaskDonVi._meta.db_table, "task_congviec_donvi")

    def test_ten_cot_dung_chuan_pm(self):
        cot_task = {f.name: f.column for f in Task._meta.fields}
        self.assertEqual(cot_task["title"], "noi_dung")
        self.assertEqual(cot_task["created_date"], "ngay_tao_cv")
        self.assertEqual(cot_task["due_date"], "ngay_xu_ly")
        self.assertEqual(cot_task["requirement"], "yeu_cau_xu_ly")
        self.assertEqual(cot_task["created_by"], "nguoi_tao_id")
        self.assertEqual(cot_task["is_public"], "hien_thi")
        self.assertEqual(cot_task["first_opened_at"], "opened_at")
        self.assertEqual(cot_task["first_opened_by"], "opened_by")

        cot_file = {f.name: f.column for f in TaskAttachment._meta.fields}
        self.assertEqual(cot_file["original_name"], "name")
        self.assertEqual(cot_file["file"], "path")
        self.assertEqual(cot_file["task"], "cong_viec_id")
        self.assertEqual(cot_file["comment"], "y_kien_id")
        self.assertEqual(cot_file["kind"], "loai")
        self.assertEqual(cot_file["uploaded_by"], "nguoi_tao_id")
        self.assertEqual(cot_file["uploaded_at"], "created_at")
        self.assertEqual(
            sorted(cot_file.values()),
            ["cong_viec_id", "created_at", "id", "is_deleted", "loai", "name", "nguoi_tao_id", "path", "y_kien_id"],
        )


class LatestTasksApiTests(WorkTestBase):
    def test_tra_toi_da_limit_cong_viec_moi_nhat_ma_user_duoc_xem(self):
        for index in range(7):
            self.make_task(title=f"Việc {index}", created_offset=index, due_offset=index + 3)
        self.make_task(title="Việc bị ẩn", created_offset=10, due_offset=13, is_public=False)

        self.login(self.member)
        response = self.client.get("/api/work/tasks/latest/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["title"] for item in response.data], ["Việc 6", "Việc 5", "Việc 4", "Việc 3", "Việc 2"])
        self.assertEqual(
            set(response.data[0].keys()),
            {"id", "title", "createdDate", "dueDate", "status", "statusLabel"},
        )
        self.assertEqual(response.data[0]["statusLabel"], "Chờ xử lý")

    def test_limit_sai_bao_loi_co_huong_dan(self):
        self.login(self.member)
        response = self.client.get("/api/work/tasks/latest/?limit=100")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("từ 1 đến 20", response.data["limit"][0])


# ==========================================================================
# ===== KHU VỰC: Danh sách, thêm / sửa / xóa =====
# ==========================================================================

class TaskListApiTests(WorkTestBase):
    def test_loc_trang_thai_va_phan_trang_dem_dung(self):
        for _ in range(3):
            self.make_task()
        for _ in range(5):
            self.make_task(created_offset=-5, due_offset=-1)

        self.login(self.member)
        response = self.client.get("/api/work/tasks/", {"status": "QUA_HAN", "pageSize": 2, "page": 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(response.data["totalPages"], 3)
        self.assertEqual(response.data["page"], 3)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(all(item["status"] == "QUA_HAN" for item in response.data["results"]))

    def test_tim_theo_tieu_de_va_loc_khoang_ngay_tao(self):
        self.make_task(title="Báo cáo quý 3", created_offset=-3, due_offset=5)
        self.make_task(title="Báo cáo năm", created_offset=0)
        self.make_task(title="Họp giao ban", created_offset=-3, due_offset=5)

        self.login(self.member)
        response = self.client.get("/api/work/tasks/", {
            "search": "báo cáo",
            "createdFrom": self.days(-4).isoformat(),
            "createdTo": self.days(-1).isoformat(),
        })

        self.assertEqual([item["title"] for item in response.data["results"]], ["Báo cáo quý 3"])

    def test_du_lieu_danh_sach_dung_hinh_dang(self):
        self.make_task()
        self.login(self.host)
        item = self.client.get("/api/work/tasks/").data["results"][0]

        self.assertEqual(item["creator"], {
            "id": self.creator.pk,
            "fullName": "Trần Phương Duy",
            "position": self.creator.chuc_vu.name,
            "department": self.creator.don_vi.ten,
        })
        self.assertEqual(item["host"]["fullName"], "Phan Quốc Dũng")
        self.assertEqual([p["id"] for p in item["directors"]], [self.director.pk])
        self.assertEqual([p["id"] for p in item["participants"]], [self.member.pk])
        self.assertEqual(item["myRoles"], ["CHU_TRI"])
        self.assertEqual(item["permissions"], {"canEdit": True, "canDelete": True, "canApprove": False, "canUnapprove": False})

    def test_tinh_trang_khong_hop_le(self):
        self.login(self.member)
        response = self.client.get("/api/work/tasks/", {"status": "ABC"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Hãy chọn một tình trạng", response.data["status"][0])

    def test_khoang_ngay_nguoc(self):
        self.login(self.member)
        response = self.client.get("/api/work/tasks/", {
            "createdFrom": self.days(1).isoformat(),
            "createdTo": self.days(-1).isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskDefaultOrderingTests(WorkTestBase):
    """VIỆC 3: thứ tự mặc định 3 tầng, tie-break -id, và ưu tiên ordering theo request."""

    def ids(self, response):
        return [item["id"] for item in response.data["results"]]

    def test_thu_tu_mac_dinh_ba_tang(self):
        # Nhóm "Chờ xử lý" (mới tạo, chưa mở, còn hạn) — dựng lệch hạn để kiểm tầng 2.
        cho_xa = self.make_task(due_offset=10, title="Chờ xử lý - hạn xa")
        cho_gan = self.make_task(due_offset=2, title="Chờ xử lý - hạn gần")
        cho_giua = self.make_task(due_offset=5, title="Chờ xử lý - hạn giữa")
        # Nhóm trạng thái khác: đã mở + còn hạn → Đang xử lý.
        dang_xa = self.make_task(due_offset=3, title="Đang xử lý - hạn xa", first_opened_at=timezone.now())
        dang_gan = self.make_task(due_offset=1, title="Đang xử lý - hạn gần", first_opened_at=timezone.now())

        # Xác nhận trạng thái đúng như dàn dựng trước khi kiểm thứ tự.
        self.assertEqual(self.status_of(cho_gan), TaskStatus.CHO_XU_LY)
        self.assertEqual(self.status_of(dang_gan), TaskStatus.DANG_XU_LY)

        self.login(self.member)
        response = self.client.get("/api/work/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Tầng 1: cả 3 "Chờ xử lý" đứng trước 2 việc còn lại.
        # Tầng 2: trong mỗi nhóm, hạn gần đứng trước hạn xa.
        self.assertEqual(
            self.ids(response),
            [cho_gan.pk, cho_giua.pk, cho_xa.pk, dang_gan.pk, dang_xa.pk],
        )

    def test_cung_trang_thai_cung_han_sap_theo_id_giam_dan(self):
        first = self.make_task(due_offset=4, title="Cùng hạn - tạo trước")
        second = self.make_task(due_offset=4, title="Cùng hạn - tạo sau")

        self.login(self.member)
        response = self.client.get("/api/work/tasks/")
        # Cùng "Chờ xử lý" + cùng due_date → tie-break cuối cùng -id: id lớn (mới) lên trước.
        self.assertEqual(self.ids(response), [second.pk, first.pk])

    def test_request_ordering_thang_mac_dinh(self):
        cho_xa = self.make_task(due_offset=10)
        cho_gan = self.make_task(due_offset=2)
        cho_giua = self.make_task(due_offset=5)
        dang_xa = self.make_task(due_offset=3, first_opened_at=timezone.now())
        dang_gan = self.make_task(due_offset=1, first_opened_at=timezone.now())

        self.login(self.member)
        # ?ordering=due_date → sắp thuần theo hạn tăng dần, BỎ QUA nhóm "Chờ xử lý".
        response = self.client.get("/api/work/tasks/", {"ordering": "due_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.ids(response),
            [dang_gan.pk, cho_gan.pk, dang_xa.pk, cho_giua.pk, cho_xa.pk],
        )


class EmployeeInfoSerializerTests(WorkTestBase):
    """VIỆC 4: CBNV trả về Họ tên — Chức vụ — Phòng ban thật, an toàn khi thiếu FK."""

    def test_api_employees_tra_chuc_vu_va_phong_ban_that(self):
        self.login(self.creator)
        response = self.client.get("/api/work/employees/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        me = next(item for item in response.data if item["id"] == self.creator.pk)
        self.assertEqual(me["fullName"], "Trần Phương Duy")
        self.assertEqual(me["position"], self.creator.chuc_vu.name)
        self.assertEqual(me["department"], self.creator.don_vi.ten)
        # Không còn placeholder cứng "Nhân viên".
        self.assertNotEqual(me["position"], "")

    def test_chi_tiet_cong_viec_co_chuc_vu_phong_ban(self):
        task = self.make_task()
        self.login(self.host)
        data = self.client.get(self.task_url(task)).data
        self.assertEqual(data["creator"]["position"], self.creator.chuc_vu.name)
        self.assertEqual(data["creator"]["department"], self.creator.don_vi.ten)
        self.assertEqual(data["host"]["department"], self.host.don_vi.ten)

    def test_thieu_fk_tra_chuoi_rong_khong_raise(self):
        from work.serializers import EmployeeBriefSerializer

        # Model khai NOT NULL nhưng record seed cũ có thể thiếu FK: serializer phải trả ""
        # chứ không ném lỗi làm vỡ cả danh sách.
        user = self.outsider
        user.chuc_vu = None
        user.don_vi = None
        data = EmployeeBriefSerializer(user).data
        self.assertEqual(data["position"], "")
        self.assertEqual(data["department"], "")


class TaskCreateApiTests(WorkTestBase):
    def payload(self, **overrides):
        data = {
            "title": "Chuẩn bị báo cáo tiến độ",
            "createdDate": self.today.isoformat(),
            "dueDate": self.days(5).isoformat(),
            "requirement": "Tổng hợp số liệu",
            "hostId": self.host.pk,
            "directorIds": [self.director.pk],
            "participantIds": [self.member.pk],
        }
        data.update(overrides)
        return data

    def test_tao_thanh_cong_kem_file(self):
        self.login(self.creator)
        data = self.payload(attachments=[pdf_file("Kế hoạch.pdf"), pdf_file("Phụ lục.pdf")])
        response = self.client.post("/api/work/tasks/", data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], "CHO_XU_LY")
        self.assertTrue(response.data["isPublic"])
        self.assertEqual(response.data["creator"]["id"], self.creator.pk)
        self.assertEqual([f["fileName"] for f in response.data["attachments"]], ["Kế hoạch.pdf", "Phụ lục.pdf"])
        self.assertEqual(response.data["evidences"], [])

    def test_tao_cong_viec_thieu_quyen_add_congviec_bi_chan(self):
        self.login(self.outsider)
        response = self.client.post("/api/work/tasks/", self.payload(), format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Task.objects.exists())

    def test_file_luu_theo_thu_muc_nam_thang(self):
        self.login(self.creator)
        self.client.post("/api/work/tasks/", self.payload(attachments=[pdf_file("Kế hoạch.pdf")]), format="multipart")
        stored = TaskAttachment.objects.get().file.name
        self.assertRegex(stored, rf"^cong-viec/{self.today:%Y/%m/%d}/[0-9a-f]{{32}}\.pdf$")
        self.assertTrue((Path(TEMP_STORAGE_ROOT) / stored).is_file())

    def test_khong_bat_buoc_file_dinh_kem(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_isPublic_false_duoc_luu(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(isPublic="false"), format="multipart")
        self.assertFalse(response.data["isPublic"])

    def test_ngay_tao_trong_qua_khu_bi_chan(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(createdDate=self.days(-1).isoformat()), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Hãy chọn hôm nay", response.data["createdDate"][0])

    def test_ngay_xu_ly_truoc_ngay_tao_bi_chan(self):
        self.login(self.creator)
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(createdDate=self.days(3).isoformat(), dueDate=self.days(2).isoformat()),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bằng hoặc sau ngày tạo", response.data["dueDate"][0])

    def test_mot_nguoi_hai_vai_tro_bi_chan(self):
        self.login(self.creator)
        response = self.client.post(
            "/api/work/tasks/",
            self.payload(participantIds=[self.member.pk, self.director.pk]),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("chỉ giữ một vai trò", response.data["participantIds"][0])

    def test_nguoi_tao_duoc_tu_lam_chu_tri(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(hostId=self.creator.pk), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(sorted(response.data["myRoles"]), ["CHU_TRI", "NGUOI_TAO"])

    def test_thieu_chi_dao_va_tham_gia_bi_chan(self):
        self.login(self.creator)
        data = self.payload()
        del data["directorIds"], data["participantIds"]
        response = self.client.post("/api/work/tasks/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("directorIds", response.data)
        self.assertIn("participantIds", response.data)

    def test_file_sai_dinh_dang_bi_chan(self):
        self.login(self.creator)
        bad = SimpleUploadedFile("chay-thu.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post("/api/work/tasks/", self.payload(attachments=[bad]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PDF, DOC/DOCX, JPG, JPEG hoặc PNG", str(response.data["attachments"]))
        self.assertFalse(Task.objects.exists())

    def test_file_tu_20mb_bi_chan(self):
        self.login(self.creator)
        big = SimpleUploadedFile("lon.pdf", b"0" * (20 * 1024 * 1024), content_type="application/pdf")
        response = self.client.post("/api/work/tasks/", self.payload(attachments=[big]), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dưới 20 MB", str(response.data["attachments"]))


class NewTaskMailTests(WorkTestBase):
    """Gửi mail khi tạo mới: cho chủ trì, chỉ đạo, tham gia; trừ người tạo; không gửi khi sửa."""

    def setUp(self):
        super().setUp()
        for user in (self.creator, self.host, self.director, self.member):
            user.email = f"{user.username}@example.com"
            user.save(update_fields=["email"])

    def payload(self, **overrides):
        data = {
            "title": "Chuẩn bị báo cáo quý",
            "createdDate": self.today.isoformat(),
            "dueDate": self.days(5).isoformat(),
            "requirement": "Tổng hợp số liệu",
            "hostId": self.host.pk,
            "directorIds": [self.director.pk],
            "participantIds": [self.member.pk],
        }
        data.update(overrides)
        return data

    def create(self, **overrides):
        self.login(self.creator)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/work/tasks/", self.payload(**overrides), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response

    def test_gui_moi_nguoi_lien_quan_tru_nguoi_tao(self):
        self.create()
        recipients = sorted(message.to[0] for message in mail.outbox)
        self.assertEqual(recipients, ["chidao@example.com", "chutri@example.com", "thamgia@example.com"])
        host_mail = next(m for m in mail.outbox if m.to == ["chutri@example.com"])
        self.assertIn("Chuẩn bị báo cáo quý", host_mail.subject)
        self.assertIn("Vai trò của bạn: Chủ trì giải quyết công việc", host_mail.body)
        self.assertIn(f"Hạn xử lý: {self.days(5):%d/%m/%Y}", host_mail.body)
        self.assertIn("Trần Phương Duy vừa giao", host_mail.body)

    def test_nguoi_tao_kiem_chu_tri_thi_khong_tu_gui_cho_minh(self):
        self.create(hostId=self.creator.pk)
        self.assertNotIn("nguoitao@example.com", [m.to[0] for m in mail.outbox])
        self.assertEqual(len(mail.outbox), 2)

    def test_bo_qua_nguoi_chua_co_email(self):
        self.member.email = ""
        self.member.save(update_fields=["email"])
        self.create()
        self.assertEqual(len(mail.outbox), 2)

    def test_cong_viec_dang_an_thi_khong_gui(self):
        self.create(isPublic="false")
        self.assertEqual(mail.outbox, [])

    def test_sua_cong_viec_khong_gui_mail(self):
        response = self.create()
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/work/tasks/{response.data['id']}/", {"title": "Đổi tên"}, format="multipart")
        self.assertEqual(mail.outbox, [])

    def test_loi_gui_mail_khong_lam_hong_viec_tao(self):
        with override_settings(MAILERS={"default": {"BACKEND": "work.tests.BrokenEmailBackend"}}):
            response = self.create()
        self.assertTrue(Task.objects.filter(pk=response.data["id"]).exists())

    def test_gui_dung_dia_chi_leader_email_that_khong_gui_nguoi_tao(self):
        """Thư tới email hiện tại của người được giao, không gửi nhầm người tạo."""
        leader_email = self.host.email
        self.create()

        # Có đúng 1 thư gửi tới email của người được giao.
        leader_mails = [m for m in mail.outbox if m.to == [leader_email]]
        self.assertEqual(len(leader_mails), 1)
        # Người tạo KHÔNG nằm trong danh sách nhận.
        all_recipients = [address for m in mail.outbox for address in m.to]
        self.assertNotIn(self.creator.email, all_recipients)
        # Mỗi thư gửi đích danh đúng một người (to có đúng 1 địa chỉ).
        self.assertTrue(all(len(m.to) == 1 for m in mail.outbox))


class BrokenEmailBackend:
    """Backend giả luôn lỗi, để kiểm tra việc tạo công việc không phụ thuộc vào mail."""

    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionRefusedError("SMTP server không phản hồi")


class TaskUpdateDeleteApiTests(WorkTestBase):
    def test_chu_tri_sua_duoc_va_giu_ngay_tao_cu(self):
        task = self.make_task(created_offset=-3, due_offset=3)
        self.login(self.host)
        response = self.client.patch(self.task_url(task), {"title": "Tiêu đề mới"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["title"], "Tiêu đề mới")
        self.assertEqual(response.data["createdDate"], self.days(-3).isoformat())

    def test_chi_dao_khong_duoc_sua(self):
        task = self.make_task()
        self.login(self.director)
        response = self.client.patch(self.task_url(task), {"title": "X"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("liên hệ người tạo hoặc người chủ trì", response.data["detail"])

    def test_admin_khong_lien_quan_chi_xem(self):
        task = self.make_task(is_public=False)
        self.login(self.admin)
        detail = self.client.get(self.task_url(task))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertFalse(any(detail.data["permissions"].values()))
        self.assertEqual(self.client.patch(self.task_url(task), {"title": "X"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(self.task_url(task)).status_code, status.HTTP_403_FORBIDDEN)

    def test_dang_cho_duyet_khong_sua_duoc(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.add_evidence(task)
        self.login(self.creator)
        response = self.client.patch(self.task_url(task), {"title": "X"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("xóa công việc và tạo lại", response.data["detail"])

    def test_han_xu_ly_khi_sua_phai_tu_hom_nay(self):
        task = self.make_task(created_offset=-3, due_offset=3)
        self.login(self.creator)
        response = self.client.patch(self.task_url(task), {"dueDate": self.days(-1).isoformat()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("từ hôm nay trở đi", response.data["dueDate"][0])

    def test_doi_nguoi_lien_quan_va_them_bot_file(self):
        task = self.make_task()
        old_file = TaskAttachment.objects.create(
            task=task, kind=AttachmentKind.GIAO_VIEC, file=pdf_file("cu.pdf"), uploaded_by=self.creator
        )
        old_name = old_file.file.name
        self.login(self.creator)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(self.task_url(task), {
                "hostId": self.director.pk,
                "directorIds": [self.host.pk],
                "participantIds": [self.member.pk, self.outsider.pk],
                "removeAttachmentIds": [old_file.pk],
                "attachments": [pdf_file("moi.pdf")],
            }, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["host"]["id"], self.director.pk)
        self.assertEqual({p["id"] for p in response.data["participants"]}, {self.member.pk, self.outsider.pk})
        self.assertEqual([f["fileName"] for f in response.data["attachments"]], ["moi.pdf"])
        self.assertFalse(get_document_storage().exists(old_name))

    def test_gui_thieu_nhom_nguoi_lien_quan_bi_chan(self):
        task = self.make_task()
        self.login(self.creator)
        response = self.client.patch(self.task_url(task), {"hostId": self.director.pk}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nguoi_tao_xoa_cong_viec_da_dong_bang_va_xoa_file(self):
        task = self.make_task(created_offset=-5, due_offset=-1)
        evidence = self.add_evidence(task)
        file_name = evidence.file.name
        self.login(self.creator)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.task_url(task))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())
        self.assertFalse(get_document_storage().exists(file_name))

    def test_can_bo_tham_gia_khong_duoc_xoa(self):
        task = self.make_task()
        self.login(self.member)
        response = self.client.delete(self.task_url(task))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ==========================================================================
# ===== KHU VỰC: Mở chi tiết, bằng chứng, duyệt, ý kiến, tải file =====
# ==========================================================================

class TaskOpenApiTests(WorkTestBase):
    def test_nguoi_lien_quan_mo_lan_dau_duoc_ghi_nhan(self):
        task = self.make_task()
        self.login(self.member)
        response = self.client.post(self.task_url(task, "open/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "DANG_XU_LY")
        self.assertEqual(response.data["firstOpenedBy"]["id"], self.member.pk)

    def test_mo_lan_sau_khong_ghi_de_nguoi_mo_dau_tien(self):
        task = self.make_task()
        self.login(self.member)
        self.client.post(self.task_url(task, "open/"))
        self.login(self.director)
        response = self.client.post(self.task_url(task, "open/"))
        self.assertEqual(response.data["firstOpenedBy"]["id"], self.member.pk)

    def test_nguoi_tao_mo_khong_tinh_la_da_mo(self):
        task = self.make_task()
        self.login(self.creator)
        response = self.client.post(self.task_url(task, "open/"))
        self.assertEqual(response.data["status"], "CHO_XU_LY")
        self.assertIsNone(response.data["firstOpenedAt"])

    def test_mo_sau_han_khong_doi_qua_han_thanh_chua_hoan_thanh(self):
        task = self.make_task(created_offset=-5, due_offset=-1)
        self.login(self.member)
        response = self.client.post(self.task_url(task, "open/"))
        self.assertEqual(response.data["status"], "QUA_HAN")

    def test_cong_viec_dang_an_nguoi_lien_quan_nhan_404(self):
        task = self.make_task(is_public=False)
        self.login(self.host)
        self.assertEqual(self.client.post(self.task_url(task, "open/")).status_code, status.HTTP_404_NOT_FOUND)


class TaskEvidenceApiTests(WorkTestBase):
    """Nộp kết quả = ghi ý kiến kèm file. File kèm theo là bằng chứng hoàn thành."""

    def submit(self, task, user, *names, content="Đã hoàn thành, gửi kết quả."):
        self.login(user)
        files = [pdf_file(name) for name in (names or ("bang-chung.pdf",))]
        return self.client.post(
            self.task_url(task, "comments/"), {"content": content, "files": files}, format="multipart"
        )

    def detail(self, task):
        return self.client.get(self.task_url(task)).data

    def test_tham_gia_gui_y_kien_kem_file_chuyen_cho_duyet(self):
        task = self.make_task(first_opened_at=timezone.now())
        response = self.submit(task, self.member, "Kết quả.pdf")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["content"], "Đã hoàn thành, gửi kết quả.")
        self.assertEqual([f["fileName"] for f in response.data["attachments"]], ["Kết quả.pdf"])
        self.assertEqual(response.data["attachments"][0]["kind"], "BANG_CHUNG")
        self.assertEqual(response.data["attachments"][0]["commentId"], response.data["id"])
        self.assertTrue(response.data["attachments"][0]["canDelete"])

        detail = self.detail(task)
        self.assertEqual(detail["status"], "CHO_DUYET")
        self.assertEqual(len(detail["evidences"]), 1)
        self.assertEqual(detail["evidences"][0]["uploadedBy"]["id"], self.member.pk)
        self.assertIsNotNone(detail["firstEvidenceAt"])

    def test_y_kien_chi_co_file_khong_can_noi_dung(self):
        task = self.make_task(first_opened_at=timezone.now())
        response = self.submit(task, self.member, content="")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["content"], "")

    def test_y_kien_khong_kem_file_khong_doi_trang_thai(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.login(self.member)
        response = self.client.post(self.task_url(task, "comments/"), {"content": "Đang làm, mai xong."})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["attachments"], [])
        self.assertEqual(self.detail(task)["status"], "DANG_XU_LY")

    def test_nhieu_file_trong_mot_y_kien(self):
        task = self.make_task(first_opened_at=timezone.now())
        response = self.submit(task, self.host, "a.pdf", "b.pdf")
        self.assertEqual(len(response.data["attachments"]), 2)
        self.assertEqual(TaskComment.objects.filter(task=task).count(), 1)

    def test_nguoi_khac_nop_them_khi_dang_cho_duyet(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.submit(task, self.member)
        response = self.submit(task, self.host, "bo-sung.pdf")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(self.detail(task)["evidences"]), 2)

    def test_chi_dao_va_nguoi_tao_chi_ghi_y_kien_chu_khong_kem_file(self):
        task = self.make_task()
        for user in (self.director, self.creator):
            response = self.submit(task, user)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("gửi ý kiến dạng chữ", response.data["detail"])
            response = self.client.post(self.task_url(task, "comments/"), {"content": "Góp ý"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(TaskAttachment.objects.filter(task=task).exists())

    def test_dong_bang_khong_nop_duoc(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        response = self.submit(task, self.member)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("đã bị khóa", response.data["detail"])
        self.assertFalse(TaskComment.objects.filter(task=task).exists())

    def test_da_hoan_thanh_khong_kem_file_nhung_van_ghi_y_kien_duoc(self):
        task = self.make_task(approved_at=timezone.now(), approved_by=self.host)
        self.add_evidence(task)
        response = self.submit(task, self.member)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("hủy duyệt trước", response.data["detail"])
        self.assertEqual(TaskComment.objects.filter(task=task).count(), 1)
        response = self.client.post(self.task_url(task, "comments/"), {"content": "Cảm ơn đã duyệt"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_file_sai_dinh_dang_trong_y_kien_bi_chan_va_khong_luu_gi(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.login(self.member)
        bad = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post(
            self.task_url(task, "comments/"), {"content": "Kết quả", "files": [bad]}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PDF, DOC/DOCX, JPG, JPEG hoặc PNG", str(response.data["files"]))
        self.assertFalse(TaskComment.objects.filter(task=task).exists())

    def test_khong_con_api_nop_bang_chung_rieng(self):
        task = self.make_task()
        self.login(self.member)
        response = self.client.post(self.task_url(task, "evidences/"), {"files": [pdf_file()]}, format="multipart")
        self.assertIn(response.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED))

    def test_xoa_file_thi_y_kien_van_con(self):
        task = self.make_task(first_opened_at=timezone.now())
        evidence = self.add_evidence(task, user=self.member)
        comment_id = evidence.comment_id
        self.login(self.member)
        response = self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(TaskComment.objects.filter(pk=comment_id).exists())
        comments = self.client.get(self.task_url(task, "comments/")).data
        self.assertEqual(comments[0]["content"], "Nộp kết quả")
        self.assertEqual(comments[0]["attachments"], [])

    def test_rang_buoc_db_file_bang_chung_phai_nam_trong_y_kien(self):
        from django.db import IntegrityError, transaction

        task = self.make_task()
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskAttachment.objects.create(
                task=task, kind=AttachmentKind.BANG_CHUNG, file=pdf_file(), uploaded_by=self.member
            )

    def test_chi_nguoi_upload_xoa_duoc_file_cua_minh(self):
        task = self.make_task(first_opened_at=timezone.now())
        evidence = self.add_evidence(task, user=self.member)
        self.login(self.host)
        response = self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("do chính mình tải lên", response.data["detail"])

    def test_xoa_file_cuoi_truoc_han_quay_ve_dang_xu_ly(self):
        task = self.make_task(first_opened_at=timezone.now())
        evidence = self.add_evidence(task, user=self.member)
        file_name = evidence.file.name
        self.login(self.member)

        response = self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DANG_XU_LY")
        self.assertEqual(response.data["evidences"], [])
        # Xóa mềm: bản ghi và file vẫn còn, chỉ thôi hiển thị và thôi tính vào trạng thái.
        evidence.refresh_from_db()
        self.assertTrue(evidence.is_deleted)
        self.assertTrue(get_document_storage().exists(file_name))

    def test_file_da_xoa_mem_thi_khong_tai_xuong_duoc(self):
        task = self.make_task(first_opened_at=timezone.now())
        evidence = self.add_evidence(task, user=self.member)
        self.login(self.member)
        self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))
        response = self.client.get(reverse("work:attachment-download", kwargs={"pk": evidence.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_qua_han_khong_xoa_duoc_file_bang_chung_cuoi_cung(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        evidence = self.add_evidence(task, user=self.member)
        self.login(self.member)
        response = self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Công việc đã quá hạn, không thể xóa file bằng chứng cuối cùng. Hãy nộp file mới trước rồi xóa file cũ sau.",
        )

    def test_file_cuoi_sau_han_tra_ve_ly_do_khong_xoa_duoc(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        self.add_evidence(task, user=self.member)
        self.login(self.member)
        evidence = self.client.get(self.task_url(task)).data["evidences"][0]
        self.assertFalse(evidence["canDelete"])
        self.assertIn("Hãy nộp file mới trước rồi xóa file cũ sau", evidence["deleteBlockedReason"])
        self.login(self.host)
        self.assertIsNone(self.client.get(self.task_url(task)).data["evidences"][0]["deleteBlockedReason"])

    def test_qua_han_con_hai_file_thi_xoa_duoc_mot(self):
        task = self.make_task(created_offset=-5, due_offset=-1, first_opened_at=timezone.now())
        old = self.add_evidence(task, user=self.member, name="cu.pdf")
        self.add_evidence(task, user=self.member, name="moi.pdf")
        self.login(self.member)
        response = self.client.delete(self.task_url(task, f"evidences/{old.pk}/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CHO_DUYET")

    def test_da_duyet_khong_xoa_duoc_bang_chung(self):
        task = self.make_task(approved_at=timezone.now(), approved_by=self.host)
        evidence = self.add_evidence(task, user=self.member)
        self.login(self.member)
        response = self.client.delete(self.task_url(task, f"evidences/{evidence.pk}/"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_co_delete_cho_file_cua_chinh_minh(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.add_evidence(task, user=self.member)
        self.login(self.member)
        response = self.client.get(self.task_url(task))
        self.assertTrue(response.data["evidences"][0]["canDelete"])


class TaskApprovalApiTests(WorkTestBase):
    def waiting_task(self, **extra):
        task = self.make_task(first_opened_at=timezone.now(), **extra)
        self.add_evidence(task)
        return task

    def test_chi_dao_duyet_thanh_hoan_thanh(self):
        task = self.waiting_task()
        self.login(self.director)
        response = self.client.post(self.task_url(task, "approve/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "HOAN_THANH")
        self.assertEqual(response.data["approvedBy"]["id"], self.director.pk)

    def test_tham_gia_va_admin_khong_lien_quan_khong_duoc_duyet(self):
        task = self.waiting_task()
        for user in (self.member, self.admin):
            self.login(user)
            response = self.client.post(self.task_url(task, "approve/"))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("người tạo, người chủ trì hoặc người chỉ đạo", response.data["detail"])

    def test_nguoi_tao_duyet_va_huy_duyet_duoc(self):
        task = self.waiting_task()
        self.login(self.creator)
        response = self.client.post(self.task_url(task, "approve/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["approvedBy"]["id"], self.creator.pk)
        self.assertTrue(response.data["permissions"]["canUnapprove"])
        response = self.client.post(self.task_url(task, "unapprove/"))
        self.assertEqual(response.data["status"], "CHO_DUYET")

    def test_chua_co_bang_chung_khong_duyet_duoc(self):
        task = self.make_task(first_opened_at=timezone.now())
        self.login(self.host)
        response = self.client.post(self.task_url(task, "approve/"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gửi ý kiến kèm file kết quả", response.data["detail"])

    def test_cho_duyet_qua_han_van_duyet_duoc(self):
        task = self.waiting_task(created_offset=-5, due_offset=-1)
        self.login(self.host)
        response = self.client.post(self.task_url(task, "approve/"))
        self.assertEqual(response.data["status"], "HOAN_THANH")

    def test_huy_duyet_quay_ve_cho_duyet_roi_duyet_lai_khi_qua_han(self):
        task = self.waiting_task(created_offset=-5, due_offset=-1)
        self.login(self.host)
        self.client.post(self.task_url(task, "approve/"))

        response = self.client.post(self.task_url(task, "unapprove/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CHO_DUYET")
        self.assertIsNone(response.data["approvedAt"])

        response = self.client.post(self.task_url(task, "approve/"))
        self.assertEqual(response.data["status"], "HOAN_THANH")

    def test_huy_duyet_khi_chua_duyet_bao_loi(self):
        task = self.waiting_task()
        self.login(self.host)
        response = self.client.post(self.task_url(task, "unapprove/"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_co_quyen_trong_danh_sach_theo_trang_thai(self):
        task = self.waiting_task()
        self.login(self.director)
        item = self.client.get("/api/work/tasks/").data["results"][0]
        self.assertTrue(item["permissions"]["canApprove"])
        self.assertFalse(item["permissions"]["canUnapprove"])
        self.client.post(self.task_url(task, "approve/"))
        item = self.client.get("/api/work/tasks/").data["results"][0]
        self.assertFalse(item["permissions"]["canApprove"])
        self.assertTrue(item["permissions"]["canUnapprove"])


class TaskCommentApiTests(WorkTestBase):
    def test_nguoi_lien_quan_ghi_va_xem_y_kien_theo_thu_tu(self):
        task = self.make_task()
        self.login(self.member)
        self.client.post(self.task_url(task, "comments/"), {"content": "Ý kiến 1"})
        self.login(self.creator)
        created = self.client.post(self.task_url(task, "comments/"), {"content": "Ý kiến 2"})
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["author"]["id"], self.creator.pk)

        response = self.client.get(self.task_url(task, "comments/"))
        self.assertEqual([item["content"] for item in response.data], ["Ý kiến 1", "Ý kiến 2"])
        self.assertIn("createdAt", response.data[0])

    def test_y_kien_trong_bi_chan(self):
        task = self.make_task()
        self.login(self.member)
        response = self.client.post(self.task_url(task, "comments/"), {"content": "   "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Hãy nhập nội dung", response.data["content"][0])

    def test_dong_bang_khong_ghi_y_kien(self):
        task = self.make_task(created_offset=-5, due_offset=-1)
        self.login(self.host)
        response = self.client.post(self.task_url(task, "comments/"), {"content": "Muộn rồi"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(TaskComment.objects.exists())

    def test_admin_xem_duoc_nhung_khong_ghi_y_kien(self):
        task = self.make_task()
        self.login(self.admin)
        self.assertEqual(self.client.get(self.task_url(task, "comments/")).status_code, status.HTTP_200_OK)
        response = self.client.post(self.task_url(task, "comments/"), {"content": "Admin góp ý"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_khong_co_api_sua_xoa_y_kien(self):
        task = self.make_task()
        self.login(self.member)
        self.assertEqual(self.client.patch(self.task_url(task, "comments/"), {}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(self.task_url(task, "comments/")).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AttachmentDownloadApiTests(WorkTestBase):
    def test_nguoi_duoc_xem_tai_duoc_file_voi_ten_goc(self):
        task = self.make_task()
        evidence = self.add_evidence(task, name="Báo cáo.pdf")
        self.login(self.director)
        response = self.client.get(reverse("work:attachment-download", kwargs={"pk": evidence.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 noi dung thu")
        self.assertIn("attachment", response["Content-Disposition"])
        # response.close() phát tín hiệu request_finished làm Django đóng luôn kết nối DB,
        # khiến test chạy sau đó lỗi trên PostgreSQL. Ngắt tạm tín hiệu khi đóng file.
        request_finished.disconnect(close_old_connections)
        try:
            response.close()
        finally:
            request_finished.connect(close_old_connections)

    def test_nguoi_ngoai_khong_tai_duoc(self):
        task = self.make_task()
        evidence = self.add_evidence(task)
        self.login(self.outsider)
        response = self.client.get(reverse("work:attachment-download", kwargs={"pk": evidence.pk}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ==========================================================================
# ===== KHU VỰC: Cán bộ nhân viên, người dùng hiện tại, header giả lập =====
# ==========================================================================

class EmployeeApiTests(WorkTestBase):
    def test_danh_sach_can_bo_co_tim_kiem(self):
        self.login(self.creator)
        response = self.client.get("/api/work/employees/", {"search": "nguyễn"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        employees = {item["id"]: item for item in response.data}
        self.assertIn(self.member.pk, employees)
        self.assertIn(self.director.pk, employees)
        member = employees[self.member.pk]
        self.assertEqual(member["position"], self.member.chuc_vu.name)
        self.assertEqual(member["department"], self.member.don_vi.ten)

    def test_can_bo_chua_khai_ten_thi_dung_username(self):
        self.login(self.creator)
        response = self.client.get("/api/work/employees/", {"search": "nguoingoai"})
        self.assertEqual(response.data[0]["fullName"], "nguoingoai")

    def test_me_tra_ve_co_isAdmin(self):
        self.login(self.admin)
        response = self.client.get("/api/work/me/")
        self.assertEqual(response.data["id"], self.admin.pk)
        self.assertTrue(response.data["isAdmin"])


class AnonymousAccessTests(WorkTestBase):
    """
    Issue #65-1 và #65-2: không còn lớp xác thực giả lập, không còn tự đăng nhập superuser.
    Request không có token phải bị từ chối ở mọi endpoint, kể cả khi DEBUG=True.
    """

    def payload(self):
        return {
            "title": "Việc do khách tạo",
            "createdDate": self.today.isoformat(),
            "dueDate": self.days(3).isoformat(),
            "requirement": "Yêu cầu",
            "hostId": self.host.pk,
            "directorIds": [self.director.pk],
            "participantIds": [self.member.pk],
        }

    def test_khong_co_token_thi_khong_doc_duoc(self):
        for url in ("/api/work/tasks/", "/api/work/me/", "/api/work/employees/", "/api/work/tasks/latest/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, url)
            self.assertIn("Hãy đăng nhập", response.data["detail"])

    def test_khong_co_token_thi_khong_tao_duoc_cong_viec(self):
        response = self.client.post("/api/work/tasks/", self.payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Task.objects.filter(title="Việc do khách tạo").exists())

    @override_settings(DEBUG=True)
    def test_debug_true_cung_khong_duoc_mien_dang_nhap(self):
        """Trước đây bật DEBUG là tự đăng nhập bằng superuser — lỗ hổng đã bị gỡ."""
        response = self.client.get("/api/work/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(DEBUG=True)
    def test_header_gia_lap_cu_khong_con_tac_dung(self):
        response = self.client.get("/api/work/me/", HTTP_X_MOCK_USER_ID=str(self.admin.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cac_thao_tac_ghi_deu_chan_nguoi_an_danh(self):
        task = self.make_task()
        evidence = self.add_evidence(task, user=self.member)
        thao_tac = [
            ("patch", self.task_url(task), {"title": "Đổi"}),
            ("delete", self.task_url(task), None),
            ("post", self.task_url(task, "open/"), None),
            ("post", self.task_url(task, "comments/"), {"content": "Ý kiến"}),
            ("delete", self.task_url(task, f"evidences/{evidence.pk}/"), None),
            ("post", self.task_url(task, "approve/"), None),
            ("post", self.task_url(task, "unapprove/"), None),
        ]
        for method, url, data in thao_tac:
            response = getattr(self.client, method)(url, data) if data else getattr(self.client, method)(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, f"{method} {url}")

    def test_dang_nhap_roi_thi_tao_duoc(self):
        self.login(self.creator)
        response = self.client.post("/api/work/tasks/", self.payload(), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


class SeedWorkDemoCommandTests(TestCase):
    """VIỆC 5: management command seed dữ liệu demo — guard dry-run, idempotent, dọn dẹp."""

    def run_seed(self, *args):
        from io import StringIO

        out = StringIO()
        call_command("seed_work_demo", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_dry_run_mac_dinh_khong_ghi_gi(self):
        out = self.run_seed()  # không có cờ --yes-i-know
        self.assertIn("DRY-RUN", out)
        self.assertEqual(User.objects.filter(username__startswith="test_").count(), 0)
        self.assertEqual(Task.objects.filter(title__startswith="[TEST]").count(), 0)

    def test_thuc_thi_va_chay_lai_khong_nhan_ban(self):
        from accounts.models import Position

        position_ids_before = set(Position.objects.values_list("pk", flat=True))
        unit_ids_before = set(DonVi.objects.values_list("pk", flat=True))
        self.run_seed("--yes-i-know")
        emp_count = User.objects.filter(username__startswith="test_").count()
        task_count = Task.objects.filter(title__startswith="[TEST]").count()
        self.assertEqual(emp_count, 5)
        self.assertEqual(task_count, 7)

        # Tài khoản leader dùng email demo thuộc miền .test.
        from work.management.commands.seed_work_demo import LEADER_EMAIL

        leader = User.objects.get(username="test_truongnhom6")
        self.assertEqual(leader.email, LEADER_EMAIL)
        self.assertTrue(
            User.objects.filter(username="test_cbnv_1", email__endswith="@test.local").exists()
        )
        # Có danh mục nền thì command tái sử dụng; DB trống mới tạo danh mục [TEST].
        demo_employees = User.objects.filter(username__startswith="test_")
        used_position_ids = set(demo_employees.values_list("chuc_vu_id", flat=True))
        used_unit_ids = set(demo_employees.values_list("don_vi_id", flat=True))
        if position_ids_before:
            self.assertTrue(used_position_ids.issubset(position_ids_before))
        else:
            self.assertTrue(Position.objects.filter(name__startswith="[TEST]").exists())
        if unit_ids_before:
            self.assertTrue(used_unit_ids.issubset(unit_ids_before))
        else:
            self.assertTrue(DonVi.objects.filter(ten__startswith="[TEST]").exists())
        # Mỗi CBNV đều có chức vụ + phòng ban (không thiếu FK).
        self.assertTrue(all(e.chuc_vu_id and e.don_vi_id for e in User.objects.filter(username__startswith="test_")))

        # Chạy lại: idempotent, không nhân bản.
        self.run_seed("--yes-i-know")
        self.assertEqual(User.objects.filter(username__startswith="test_").count(), emp_count)
        self.assertEqual(Task.objects.filter(title__startswith="[TEST]").count(), task_count)

    def test_clear_xoa_dung_du_lieu_demo(self):
        from io import StringIO

        self.run_seed("--yes-i-know")
        out = StringIO()
        call_command("clear_work_demo", "--yes-i-know", stdout=out, stderr=out)
        self.assertEqual(User.objects.filter(username__startswith="test_").count(), 0)
        self.assertEqual(Task.objects.filter(title__startswith="[TEST]").count(), 0)


class TaskReminderMailTests(WorkTestBase):
    """VIỆC 6: nhắc việc sắp đến hạn / quá hạn — gửi đích danh host + tham gia, không gửi người tạo/chỉ đạo."""

    def setUp(self):
        super().setUp()
        for user in (self.creator, self.host, self.director, self.member):
            user.email = f"{user.username}@test.local"
            user.save(update_fields=["email"])

    def recipients(self):
        return sorted(address for message in mail.outbox for address in message.to)

    def test_nhac_sap_den_han_gui_host_va_tham_gia(self):
        from work.services.email import send_due_soon_reminders

        self.make_task(due_offset=2)  # CHO_XU_LY, còn hạn 2 ngày → nằm trong cửa sổ 3 ngày
        sent = send_due_soon_reminders(today=self.today)

        self.assertEqual(sent, 2)
        self.assertEqual(self.recipients(), sorted([self.host.email, self.member.email]))
        self.assertNotIn(self.creator.email, self.recipients())  # không gửi người tạo
        self.assertNotIn(self.director.email, self.recipients())  # không gửi chỉ đạo
        self.assertTrue(all(len(m.to) == 1 for m in mail.outbox))  # đích danh từng người
        self.assertTrue(all("Sắp đến hạn" in m.subject for m in mail.outbox))

    def test_nhac_qua_han_gui_host_va_tham_gia(self):
        from work.services.email import send_overdue_reminders

        self.make_task(created_offset=-10, due_offset=-5)  # chưa mở + quá hạn → QUA_HAN
        sent = send_overdue_reminders(today=self.today)

        self.assertEqual(sent, 2)
        self.assertEqual(self.recipients(), sorted([self.host.email, self.member.email]))
        self.assertNotIn(self.creator.email, self.recipients())
        self.assertNotIn(self.director.email, self.recipients())
        self.assertTrue(all("QUÁ HẠN" in m.subject for m in mail.outbox))

    def test_khong_nhac_viec_da_nop_bang_chung(self):
        from work.services.email import send_due_soon_reminders

        # Còn hạn 2 ngày nhưng đã nộp bằng chứng → CHO_DUYET, không còn phải xử lý → không nhắc.
        task = self.make_task(due_offset=2, first_opened_at=timezone.now())
        self.add_evidence(task)
        sent = send_due_soon_reminders(today=self.today)

        self.assertEqual(sent, 0)
        self.assertEqual(mail.outbox, [])

    def test_bo_qua_nguoi_khong_co_email(self):
        from work.services.email import send_due_soon_reminders

        self.member.email = ""
        self.member.save(update_fields=["email"])
        self.make_task(due_offset=1)
        send_due_soon_reminders(today=self.today)
        # Chỉ còn host nhận (member thiếu email bị bỏ qua).
        self.assertEqual(self.recipients(), [self.host.email])

    def test_command_dry_run_khong_gui_gi(self):
        from io import StringIO

        self.make_task(due_offset=2)
        out = StringIO()
        call_command("send_task_reminders", "--dry-run", stdout=out, stderr=out)
        self.assertIn("DRY-RUN", out.getvalue())
        self.assertEqual(mail.outbox, [])  # dry-run dùng dummy backend, không vào outbox

    def test_command_gui_that_qua_backend_an_toan(self):
        from io import StringIO

        self.make_task(due_offset=2)  # 1 việc sắp đến hạn
        out = StringIO()
        # Backend trong test là locmem (không phải SMTP thật) → gửi luôn, không cần --yes-send-real.
        call_command("send_task_reminders", stdout=out, stderr=out)
        self.assertEqual(len(mail.outbox), 2)  # host + tham gia


class JwtAuthenticationTests(WorkTestBase):
    """Module dùng đúng cơ chế đăng nhập chung của dự án: JWT do accounts/login/ cấp."""

    def test_token_hop_le_goi_duoc_api(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(self.member).access_token
        response = self.client.get("/api/work/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.member.pk)

    def test_token_rac_bi_tu_choi(self):
        response = self.client.get("/api/work/me/", HTTP_AUTHORIZATION="Bearer khong-phai-token")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
