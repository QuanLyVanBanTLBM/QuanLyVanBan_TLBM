"""Quyền Danh mục hồ sơ và Loại văn bản theo bảng nhóm Hồ sơ (issue #647, release_DDL.sql [VTHS]):
BGD, CV, TP chỉ xem; VT xem, thêm, sửa, không xóa; ADMIN đủ bốn quyền; tài khoản không nhóm không có quyền nào."""
import re
from importlib import import_module
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from records.models import HoSo, LoaiVanBan

migration = import_module("authorization.migrations.0019_van_thu_them_sua_ho_so")
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"
HOSO_CODES = ["view_hoso", "add_hoso", "change_hoso", "delete_hoso"]
EXPECTED = {
    "BGD": {"view_hoso"},
    "VT": {"view_hoso", "add_hoso", "change_hoso"},
    "CV": {"view_hoso"},
    "TP": {"view_hoso"},
    "ADMIN": set(HOSO_CODES),
}


class SchemaEditorStub:
    connection = connection


def hoso_codes_of(code):
    group = Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)
    return set(group.permissions.filter(codename__in=HOSO_CODES).values_list("codename", flat=True))


class HoSoPermissionMatrixTest(TestCase):
    def test_database_matches_table_of_group_3(self):
        for code, expected in EXPECTED.items():
            self.assertEqual(hoso_codes_of(code), expected, code)

    def test_release_ddl_grants_add_change_to_vt_only(self):
        ddl = DDL_PATH.read_text(encoding="utf-8")
        block = ddl[ddl.index("g.ma_nhom_quyen = 'VT'"):]
        block = block[: block.index(";")]
        self.assertTrue({"add_hoso", "change_hoso"} <= set(re.findall(r"'(\w+)'", block)))
        self.assertNotIn("delete_hoso", block)

    def test_migration_is_idempotent_and_reversible(self):
        migration.revoke_from_van_thu(django_apps, SchemaEditorStub())
        self.assertEqual(hoso_codes_of("VT"), {"view_hoso"})
        migration.grant_to_van_thu(django_apps, SchemaEditorStub())
        migration.grant_to_van_thu(django_apps, SchemaEditorStub())
        self.assertEqual(hoso_codes_of("VT"), EXPECTED["VT"])
        for code in ("BGD", "CV", "TP", "ADMIN"):
            self.assertEqual(hoso_codes_of(code), EXPECTED[code], code)


class HoSoApiByRoleTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="hs_owner", password="TestOnly12345")
        self.dossier = HoSo.objects.create(so_ky_hieu="HS-TEST", ten_ho_so="Hồ sơ thử", nguoi_lap=self.owner)
        self.doc_type = LoaiVanBan.objects.create(ho_so=self.dossier, ten_loai="Loại thử")
        self.clients = {}
        for code in list(EXPECTED) + ["NONE"]:
            user = User.objects.create_user(username=f"hs_{code.lower()}", password="TestOnly12345")
            if code != "NONE":
                user.groups.add(Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk))
            client = APIClient()
            client.force_authenticate(user=user)
            self.clients[code] = client

    def status_of(self, code, method, url, body=None):
        return getattr(self.clients[code], method)(url, body, format="json").status_code

    def test_dossier_create_update_by_role(self):
        for i, (code, can_write) in enumerate({"BGD": 0, "VT": 1, "CV": 0, "TP": 0, "ADMIN": 1, "NONE": 0}.items()):
            created = self.status_of(code, "post", "/api/records/dossiers/", {"so_ky_hieu": f"HS-{i}", "ten_ho_so": f"Hồ sơ {i}"})
            self.assertEqual(created, 201 if can_write else 403, code)
            changed = self.status_of(code, "patch", f"/api/records/dossiers/{self.dossier.pk}/", {"ghi_chu": f"sửa {code}"})
            self.assertEqual(changed, 200 if can_write else 403, code)

    def test_document_type_create_update_by_role(self):
        for i, (code, can_write) in enumerate({"BGD": 0, "VT": 1, "CV": 0, "TP": 0, "ADMIN": 1, "NONE": 0}.items()):
            created = self.status_of(code, "post", f"/api/records/dossiers/{self.dossier.pk}/document-types/", {"ten_loai": f"Loại {i}"})
            self.assertEqual(created, 201 if can_write else 403, code)
            changed = self.status_of(code, "patch", f"/api/records/document-types/{self.doc_type.pk}/", {"ghi_chu": f"sửa {code}"})
            self.assertEqual(changed, 200 if can_write else 403, code)

    def test_read_by_role(self):
        for code in EXPECTED:
            self.assertEqual(self.status_of(code, "get", "/api/records/dossiers/"), 200, code)
            self.assertEqual(self.status_of(code, "get", f"/api/records/dossiers/{self.dossier.pk}/document-types/"), 200, code)
        self.assertEqual(self.status_of("NONE", "get", "/api/records/dossiers/"), 403)

    def test_only_admin_deletes(self):
        for code in ("BGD", "VT", "CV", "TP", "NONE"):
            self.assertEqual(self.status_of(code, "delete", f"/api/records/document-types/{self.doc_type.pk}/"), 403, code)
            self.assertEqual(self.status_of(code, "delete", f"/api/records/dossiers/{self.dossier.pk}/"), 403, code)
        # ADMIN: hồ sơ còn loại văn bản tham chiếu -> 409; xóa loại rồi xóa hồ sơ -> 204
        self.assertEqual(self.status_of("ADMIN", "delete", f"/api/records/dossiers/{self.dossier.pk}/"), 409)
        self.assertEqual(self.status_of("ADMIN", "delete", f"/api/records/document-types/{self.doc_type.pk}/"), 204)
        self.assertEqual(self.status_of("ADMIN", "delete", f"/api/records/dossiers/{self.dossier.pk}/"), 204)

    def test_admin_cannot_delete_system_dossier(self):
        system = HoSo.objects.get(is_he_thong=True)
        self.assertEqual(self.status_of("ADMIN", "delete", f"/api/records/dossiers/{system.pk}/"), 409)
        self.assertTrue(HoSo.objects.filter(pk=system.pk).exists())
