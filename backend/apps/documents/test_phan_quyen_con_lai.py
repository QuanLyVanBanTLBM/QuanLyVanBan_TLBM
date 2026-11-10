"""Văn bản: cổng quyền xuất/nhập Excel, xóa theo đúng loại, đổi phạm vi, tạo hồ sơ ngầm, is_staff không là quản trị (#683)."""
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents import selectors, views
from documents.models import Folder, FolderFile, PhamVi, VanBanDen, VanBanDi
from records.models import HoSo

User = get_user_model()
TEMP_STORAGE = tempfile.mkdtemp()


def make_user(username, group_code=None, perms=(), **flags):
    user = User.objects.filter(username=username).first() or User.objects.create_user(
        username=username, password="TestOnly12345"
    )
    user.is_superuser = flags.get("is_superuser", False)
    user.is_staff = flags.get("is_staff", False)
    user.save()
    user.groups.clear()
    user.user_permissions.clear()
    if group_code:
        user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=group_code).pk))
    for codename in perms:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class ExcelGateTest(TestCase):
    """Export/import của route riêng Văn bản đi và Văn bản mật phải có cổng quyền như route chung."""

    def setUp(self):
        self.nobody = make_user("pq_none")
        self.vt = make_user("pq_vt", "VT")  # VT: export_vanbanden, import_vanbanden, import_vanbandi, không export_vanbandi
        self.exp_di = make_user("pq_exp_di", perms=("export_vanbandi", "view_vanbandi"))
        self.imp_di = make_user("pq_imp_di", perms=("import_vanbandi",))
        self.exp_den = make_user("pq_exp_den", perms=("export_vanbanden",))
        self.imp_den = make_user("pq_imp_den", perms=("import_vanbanden",))

    def test_di_export_requires_export_vanbandi(self):
        self.assertEqual(api(self.nobody).get("/api/documents/di/export/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(api(self.vt).get("/api/documents/di/export/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(api(self.exp_den).get("/api/documents/di/export/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(api(self.exp_di).get("/api/documents/di/export/").status_code, status.HTTP_200_OK)

    def test_mat_export_requires_export_den_or_di(self):
        self.assertEqual(api(self.nobody).get("/api/documents/mat/export/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(api(self.exp_den).get("/api/documents/mat/export/").status_code, status.HTTP_200_OK)
        self.assertEqual(api(self.exp_di).get("/api/documents/mat/export/").status_code, status.HTTP_200_OK)

    def test_di_import_requires_import_vanbandi(self):
        # Không kèm file: có quyền thì qua cổng và nhận 400 "chọn file"; thiếu quyền nhận 403 trước đó.
        self.assertEqual(api(self.nobody).post("/api/documents/di/import/", {}, format="multipart").status_code, 403)
        self.assertEqual(api(self.imp_den).post("/api/documents/di/import/", {}, format="multipart").status_code, 403)
        self.assertEqual(api(self.imp_di).post("/api/documents/di/import/", {}, format="multipart").status_code, 400)

    def test_mat_import_requires_import_den_or_di(self):
        self.assertEqual(api(self.nobody).post("/api/documents/mat/import/", {}, format="multipart").status_code, 403)
        self.assertEqual(api(self.imp_den).post("/api/documents/mat/import/", {}, format="multipart").status_code, 400)
        self.assertEqual(api(self.imp_di).post("/api/documents/mat/import/", {}, format="multipart").status_code, 400)

    def test_admin_group_passes_all_four_gates(self):
        admin = make_user("pq_admin", "ADMIN")
        client = api(admin)
        self.assertEqual(client.get("/api/documents/di/export/").status_code, 200)
        self.assertEqual(client.get("/api/documents/mat/export/").status_code, 200)
        self.assertEqual(client.post("/api/documents/di/import/", {}, format="multipart").status_code, 400)
        self.assertEqual(client.post("/api/documents/mat/import/", {}, format="multipart").status_code, 400)


class DeleteByDocumentTypeTest(TestCase):
    """Quyền xóa chỉ có tác dụng đúng loại văn bản; không còn dòng dự phòng delete_vanbanden cho mọi loại."""

    def setUp(self):
        self.owner = make_user("pq_owner", "CV")
        self.del_den = make_user(
            "pq_del_den", perms=("delete_vanbanden", "view_vanbanden", "view_vanbandi")
        )
        self.del_di = make_user("pq_del_di", perms=("delete_vanbandi", "view_vanbanden", "view_vanbandi"))
        self.den = VanBanDen.objects.create(nam=2026, so_hieu="1/PQ", so_thu_tu=801, trich_yeu="den", nguoi_tao=self.owner)
        self.di = VanBanDi.objects.create(nam=2026, so_hieu="2/PQ", so_thu_tu=802, trich_yeu="di", nguoi_tao=self.owner)

    def test_delete_vanbanden_cannot_delete_outbound_document_of_others(self):
        for url in (f"/api/documents/di/{self.di.pk}/", f"/api/documents/{self.di.pk}/?loai=DI"):
            res = api(self.del_den).delete(url)
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, url)
        self.assertTrue(VanBanDi.objects.filter(pk=self.di.pk).exists())

    def test_delete_vanbanden_still_deletes_inbound_document(self):
        res = api(self.del_den).delete(f"/api/documents/den/{self.den.pk}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_vanbandi_deletes_outbound_but_not_inbound(self):
        self.assertEqual(api(self.del_di).delete(f"/api/documents/den/{self.den.pk}/").status_code, 403)
        self.assertEqual(api(self.del_di).delete(f"/api/documents/di/{self.di.pk}/").status_code, 204)

    def test_creator_can_still_delete_own_document(self):
        self.assertEqual(api(self.owner).delete(f"/api/documents/di/{self.di.pk}/").status_code, 204)


class ScopeChangeTest(TestCase):
    """pham_vi bất biến sau khi tạo (trigger CSDL): mọi route trả 400, không để lỗi CSDL thành 500."""

    def setUp(self):
        self.owner = make_user("pq_scope_owner", "CV")
        self.recipient = make_user("pq_scope_recipient", "CV")
        self.admin = make_user("pq_scope_admin", "ADMIN")
        self.root = make_user("pq_scope_root", is_superuser=True, is_staff=True)

    def _den(self, n):
        return VanBanDen.objects.create(nam=2026, so_hieu=f"{n}/SC", so_thu_tu=820 + n, trich_yeu="sc", nguoi_tao=self.owner)

    def _body(self):
        return {"pham_vi": "HAN_CHE", "nguoi_nhan": [self.recipient.pk]}

    def test_admin_changing_scope_gets_400_on_every_route(self):
        for user in (self.admin, self.root):
            client = api(user)
            doc = self._den(1)
            for url in (
                f"/api/documents/den/{doc.pk}/",
                f"/api/documents/{doc.pk}/?loai=DEN",
            ):
                res = client.patch(url, self._body(), format="json")
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, (user.username, url, res.content))
                self.assertIn("pham_vi", res.json())
            di = VanBanDi.objects.create(nam=2026, so_hieu="9/SC", so_thu_tu=830, trich_yeu="di", nguoi_tao=self.owner)
            res = client.patch(f"/api/documents/di/{di.pk}/", self._body(), format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.content)
            doc.refresh_from_db()
            self.assertEqual(doc.pham_vi, PhamVi.NOI_BO)

    def test_sending_same_scope_is_allowed(self):
        doc = self._den(2)
        res = api(self.admin).patch(
            f"/api/documents/den/{doc.pk}/", {"pham_vi": "NOI_BO", "trich_yeu": "doi trich yeu"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)


class HiddenRecordCreationTest(TestCase):
    """Gửi văn bản kèm hồ sơ chưa có chỉ tạo hồ sơ mới khi người gửi có add_hoso."""

    def _payload(self, ho_so):
        return {
            "loai": "DEN",
            "so_hieu": f"HS/{ho_so[-3:]}",
            "trich_yeu": "kèm hồ sơ",
            "danh_muc_ho_so": ho_so,
            "ten_loai_van_ban": "Công văn",
            "ngay_van_ban": timezone.now().isoformat(),
            "noi_ban_hanh": "Cơ quan A",
        }

    def test_user_without_add_hoso_cannot_create_new_record(self):
        user = make_user("pq_addvb", perms=("add_vanbanden", "view_vanbanden"))
        res = api(user).post("/api/documents/", self._payload("Hồ sơ ngầm số 001"), format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, res.content)
        self.assertFalse(HoSo.objects.filter(ten_ho_so="Hồ sơ ngầm số 001").exists())
        self.assertFalse(VanBanDen.objects.filter(so_hieu="HS/001").exists())

    def test_user_without_add_hoso_can_use_existing_record(self):
        owner = make_user("pq_hs_owner", "VT")
        HoSo.objects.create(so_ky_hieu="HS-PQ", ten_ho_so="Hồ sơ có sẵn 002", nguoi_lap=owner)
        user = make_user("pq_addvb2", perms=("add_vanbanden", "view_vanbanden"))
        res = api(user).post("/api/documents/", self._payload("Hồ sơ có sẵn 002"), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)

    def test_user_with_add_hoso_creates_new_record(self):
        user = make_user("pq_vt_hs", "VT")  # VT có add_vanbanden và add_hoso
        res = api(user).post("/api/documents/", self._payload("Hồ sơ mới 003"), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)
        self.assertTrue(HoSo.objects.filter(ten_ho_so="Hồ sơ mới 003").exists())


class IsStaffIsNotAdminTest(TestCase):
    """is_staff không còn tự coi là quản trị văn bản; chỉ superuser và nhóm ADMIN."""

    def test_staff_flag_without_admin_group_has_no_privilege(self):
        owner = make_user("pq_st_owner", "CV")
        doc = VanBanDen.objects.create(nam=2026, so_hieu="3/ST", so_thu_tu=840, trich_yeu="st", nguoi_tao=owner)
        staff = make_user("pq_staff_only", is_staff=True)
        self.assertFalse(selectors.is_admin_user(staff))
        self.assertFalse(views.is_admin_user(staff))
        self.assertFalse(views.can_edit_document(staff, doc))
        self.assertFalse(views.can_delete_document(staff, doc))
        self.assertEqual(api(staff).patch(f"/api/documents/den/{doc.pk}/", {"trich_yeu": "x"}, format="json").status_code, 403)

    def test_admin_group_and_superuser_still_admin(self):
        self.assertTrue(views.is_admin_user(make_user("pq_adm_grp", "ADMIN")))
        self.assertTrue(views.is_admin_user(make_user("pq_adm_root", is_superuser=True, is_staff=True)))


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE, MEDIA_ROOT=TEMP_STORAGE)
class FolderPermissionTest(TestCase):
    """Cây thư mục theo quyền Tài liệu: view/add/change/delete_tailieu."""

    def setUp(self):
        self.nobody = make_user("pq_f_none")
        self.viewer = make_user("pq_f_view", perms=("view_tailieu",))
        self.adder = make_user("pq_f_add", perms=("view_tailieu", "add_tailieu"))
        self.changer = make_user("pq_f_change", perms=("view_tailieu", "change_tailieu"))
        self.deleter = make_user("pq_f_delete", perms=("view_tailieu", "delete_tailieu"))
        self.admin = make_user("pq_f_admin", "ADMIN")
        self.folder = Folder.objects.create(name="Thư mục gốc", created_by=self.admin)
        self.file = FolderFile.objects.create(folder=self.folder, file_name="a.pdf", file_path="a.pdf", file_size=1)

    def test_no_permission_blocks_every_folder_api(self):
        client = api(self.nobody)
        self.assertEqual(client.get("/api/folders/").status_code, 403)
        self.assertEqual(client.get("/api/folders/tree/").status_code, 403)
        self.assertEqual(client.get(f"/api/folders/{self.folder.pk}/files/").status_code, 403)
        self.assertEqual(client.get("/api/folder-files/").status_code, 403)
        self.assertEqual(client.get(f"/api/folder-files/{self.file.pk}/download/").status_code, 403)
        self.assertEqual(client.post("/api/folders/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(client.patch(f"/api/folders/{self.folder.pk}/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(client.delete(f"/api/folders/{self.folder.pk}/").status_code, 403)
        self.assertTrue(Folder.objects.filter(pk=self.folder.pk).exists())

    def test_view_only_can_read_but_not_write(self):
        client = api(self.viewer)
        self.assertEqual(client.get("/api/folders/").status_code, 200)
        self.assertEqual(client.get("/api/folders/tree/").status_code, 200)
        self.assertEqual(client.post("/api/folders/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(client.post(f"/api/folders/{self.folder.pk}/children/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(client.patch(f"/api/folders/{self.folder.pk}/", {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(client.patch(f"/api/folders/{self.folder.pk}/move/", {"target_parent_id": None}, format="json").status_code, 403)
        self.assertEqual(client.delete(f"/api/folders/{self.folder.pk}/").status_code, 403)

    def test_add_change_delete_each_map_to_own_permission(self):
        created = api(self.adder).post("/api/folders/", {"name": "Mới"}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(api(self.adder).delete(f"/api/folders/{created.json()['id']}/").status_code, 403)
        self.assertEqual(
            api(self.changer).patch(f"/api/folders/{self.folder.pk}/", {"name": "Đổi tên"}, format="json").status_code, 200
        )
        self.assertEqual(api(self.changer).post("/api/folders/", {"name": "y"}, format="json").status_code, 403)
        # delete_tailieu cho phép xóa; đối tượng vẫn giới hạn người tạo hoặc quản trị (quy tắc cũ của thư mục).
        self.assertEqual(api(self.deleter).delete(f"/api/folders/{created.json()['id']}/").status_code, 403)
        own = Folder.objects.create(name="Của người xóa", created_by=self.deleter)
        self.assertEqual(api(self.deleter).delete(f"/api/folders/{own.pk}/").status_code, 204)

    def test_admin_group_has_full_access(self):
        client = api(self.admin)
        created = client.post("/api/folders/", {"name": "Admin tạo"}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(client.delete(f"/api/folders/{created.json()['id']}/").status_code, 204)
