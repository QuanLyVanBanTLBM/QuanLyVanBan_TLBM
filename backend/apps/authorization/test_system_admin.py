"""
is_system_admin: superuser hoặc thành viên nhóm ADMIN (đang hoạt động); không suy ra từ username, role hay nhóm khác.
Các chỗ từng chỉ nhận superuser hoặc username ghi cứng (Tài liệu, nhật ký email sinh nhật) nhận nhóm ADMIN.
"""
import atexit
import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from authorization.permissions import is_system_admin
from document_templates.models import DanhMucTaiLieu, TaiLieuChiTiet
from document_templates.selectors import visible_resources
from document_templates.views import can_user_modify_document
from organizations.models import DonVi, KhoiKhuVuc

User = get_user_model()
TEMP_STORAGE_ROOT = tempfile.mkdtemp(prefix="sysadmin_test_")
atexit.register(shutil.rmtree, TEMP_STORAGE_ROOT, ignore_errors=True)


def plain_user_named(username, **extra):
    """Tài khoản mang tên ghi cứng cũ; bản seed có thể đã có sẵn nên đặt lại thành người thường không nhóm."""
    user = User.objects.filter(username=username).first() or User.objects.create_user(
        username=username, password="TestOnly12345", **extra
    )
    user.is_superuser = user.is_staff = False
    user.is_active = True
    user.save()
    user.groups.clear()
    user.user_permissions.clear()
    return user


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


class IsSystemAdminTest(TestCase):
    def make(self, username, group=None, **extra):
        user = User.objects.create_user(username=username, password="TestOnly12345", **extra)
        if group:
            user.groups.add(group_of(group))
        return user

    def test_superuser_and_admin_group_are_admin(self):
        root = User.objects.create_superuser(username="sa_root", password="TestOnly12345", email="r@example.com")
        self.assertTrue(is_system_admin(root))
        self.assertTrue(is_system_admin(self.make("sa_member", "ADMIN")))

    def test_other_groups_and_plain_users_are_not_admin(self):
        for code in ("VT", "CV", "TP", "BGD"):
            self.assertFalse(is_system_admin(self.make(f"sa_{code}", code)), code)
        self.assertFalse(is_system_admin(self.make("sa_plain")))

    def test_username_admin_or_quantri_is_not_admin(self):
        self.assertFalse(is_system_admin(plain_user_named("admin")))
        self.assertFalse(is_system_admin(plain_user_named("quantri")))

    def test_inactive_and_anonymous_are_not_admin(self):
        self.assertFalse(is_system_admin(self.make("sa_off", "ADMIN", is_active=False)))
        self.assertFalse(is_system_admin(AnonymousUser()))
        self.assertFalse(is_system_admin(None))

    def test_group_change_is_seen_on_a_fresh_user_object(self):
        user = self.make("sa_fresh")
        self.assertFalse(is_system_admin(user))
        user.groups.add(group_of("ADMIN"))
        self.assertTrue(is_system_admin(User.objects.get(pk=user.pk)))


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
class ResourcesAdminGroupTest(TestCase):
    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối quản trị thử")
        stt = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        self.unit_a = DonVi.objects.create(khoi=khoi, stt_uu_tien=stt + 1, ten="Phòng A thử")
        self.unit_b = DonVi.objects.create(khoi=khoi, stt_uu_tien=stt + 2, ten="Phòng B thử")
        self.owner = User.objects.create_user(username="res_owner", password="TestOnly12345", don_vi=self.unit_a)
        self.cat = DanhMucTaiLieu.objects.create(
            stt_uu_tien=1, ky_hieu="CAT-SA", ten_tai_lieu="Danh mục quản trị thử", nguoi_lap=self.owner
        )
        self.doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat, ky_hieu="01/SA", tieu_de="Tài liệu nội bộ phòng A", ngay_dang=date(2026, 1, 1),
            hieu_luc="CON_HIEU_LUC", hien_thi="NOI_BO_PHONG_BAN", don_vi_id=self.unit_a.pk,
            file_dinh_kem=SimpleUploadedFile("sa.pdf", b"%PDF content"), nguoi_tao=self.owner,
        )
        self.client = APIClient()

    def member(self, username, group, **extra):
        user = User.objects.create_user(username=username, password="TestOnly12345", don_vi=self.unit_b, **extra)
        if group:
            user.groups.add(group_of(group))
        return user

    def test_admin_group_sees_and_edits_resource_of_another_unit(self):
        admin = self.member("res_admin", "ADMIN")
        self.assertIn(self.doc.pk, set(visible_resources(TaiLieuChiTiet.objects.all(), admin).values_list("pk", flat=True)))
        self.client.force_authenticate(user=admin)
        res = self.client.patch(f"/api/resources/documents/{self.doc.pk}/", {"tieu_de": "Quản trị sửa"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)

    def test_username_admin_without_admin_group_is_not_privileged(self):
        fake = plain_user_named("admin", don_vi=self.unit_b)
        fake.don_vi = self.unit_b
        fake.save()
        fake.user_permissions.add(Permission.objects.get(codename="change_tailieu"))
        self.assertNotIn(self.doc.pk, set(visible_resources(TaiLieuChiTiet.objects.all(), fake).values_list("pk", flat=True)))
        self.assertFalse(can_user_modify_document(fake, self.doc, "change_tailieu"))
        self.client.force_authenticate(user=fake)
        res = self.client.patch(f"/api/resources/documents/{self.doc.pk}/", {"tieu_de": "Giả danh"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND, res.content)  # tài liệu nội bộ phòng khác: không thấy


class BirthdayLogsAdminGroupTest(TestCase):
    def test_admin_group_reads_email_logs_but_other_groups_do_not(self):
        client = APIClient()
        url = reverse("birthdays:logs")
        admin = User.objects.create_user(username="log_admin", password="TestOnly12345")
        admin.groups.add(group_of("ADMIN"))
        tp = User.objects.create_user(username="log_tp", password="TestOnly12345")
        tp.groups.add(group_of("TP"))

        client.force_authenticate(user=tp)
        self.assertEqual(client.get(url).status_code, status.HTTP_403_FORBIDDEN)
        client.force_authenticate(user=admin)
        self.assertEqual(client.get(url).status_code, status.HTTP_200_OK)


class MyPermissionsSystemAdminFlagTest(TestCase):
    def flag_of(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get("/api/auth/me/permissions/").data["is_system_admin"]

    def test_flag_true_for_superuser_and_admin_group_only(self):
        root = User.objects.create_superuser(username="flag_root", password="TestOnly12345", email="f@example.com")
        member = User.objects.create_user(username="flag_member", password="TestOnly12345")
        member.groups.add(group_of("ADMIN"))
        other = User.objects.create_user(username="flag_other", password="TestOnly12345")
        other.groups.add(group_of("BGD"))
        self.assertTrue(self.flag_of(root))
        self.assertTrue(self.flag_of(member))
        self.assertFalse(self.flag_of(other))
