"""
Nhóm Văn thư đúng 35 quyền (release_DDL.sql [VTQ], [XHHL], [TVHC], [VTHS]): DB dựng bằng migration, rbac_seed và DDL khớp nhau;
Văn thư không sửa/xóa văn bản đến của người khác; migration 0014 đặt lại đúng 30 quyền lúc đó, gỡ quyền gán tay,
chạy lại không đổi thêm, không đụng nhóm khác, reverse trả về seed cũ; 0016 thêm 2 quyền xem văn bản hết hiệu lực,
0017 thêm 2 quyền thêm văn bản hạn chế.
"""
import re
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from authorization.rbac_seed import GROUP_PERMISSIONS
from documents.models import VanBanDen

migration = import_module("authorization.migrations.0014_van_thu_permissions")
DDL_PATH = Path(settings.BASE_DIR).parent / "docs" / "common" / "database" / "release_DDL.sql"

# Danh sách 30 quyền do migration 0014 đặt lại.
EXPECTED_0014 = {
    "view_donvi", "view_chucvu", "view_loaitailieubieumau", "view_list_cbnv", "change_self_cbnv",
    "view_vanbanden", "add_vanbanden", "import_vanbanden", "export_vanbanden", "change_hieu_luc_vanbanden",
    "view_vanbandi", "add_vanbandi", "import_vanbandi", "change_hieu_luc_vanbandi",
    "view_hoso", "view_tailieu", "view_trinhky", "send_trinhky", "add_trinhky", "view_all_trinhky",
    "view_congviec", "view_dept_congviec", "add_congviec", "change_congviec",
    "view_schedule_phonghop", "add_datphonghop", "change_own_datphonghop",
    "view_sinhnhat", "send_wish_sinhnhat", "use_aiassistant",
}
REMOVED = {
    "change_vanbanden", "delete_vanbanden", "send_mail_all_vanbanden",
    "change_vanbandi", "delete_vanbandi", "export_vanbandi", "send_mail_all_vanbandi",
    "add_hoso", "change_hoso", "toggle_status_hoso", "manage_documents_hoso", "add_tailieu", "change_tailieu",
}
# Quyền thêm sau 0014 (migration 0016_het_hieu_luc_permissions, 0017_them_van_ban_han_che_permissions).
AFTER_0014 = {
    "view_het_hieu_luc_vanbanden", "view_het_hieu_luc_vanbandi",
    "add_han_che_vanbanden", "add_han_che_vanbandi",
}
# Migration 0019 cấp lại add_hoso, change_hoso cho VT (đảo quyết định gỡ ở 0014, issue #647).
AFTER_0018 = {"add_hoso", "change_hoso"}
# send_wish_sinhnhat đã bị migration 0018 gỡ khỏi DB, chỉ còn trong danh sách lịch sử của migration 0014.
CURRENT_0014 = EXPECTED_0014 - {"send_wish_sinhnhat"}
GONE_BY_0018 = {"toggle_status_hoso", "manage_documents_hoso"}
EXPECTED = CURRENT_0014 | AFTER_0014 | AFTER_0018
STILL_REMOVED = REMOVED - AFTER_0018
# Quyền tạo sau 0002 nên không nằm trong rbac_seed, được gán bởi migration riêng.
LATER_MIGRATION_GRANTS = {"change_hieu_luc_vanbanden", "change_hieu_luc_vanbandi", "view_all_trinhky"} | AFTER_0014


class SchemaEditorStub:
    connection = connection


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


def codenames_of(code):
    return set(group_of(code).permissions.values_list("codename", flat=True))


def ddl_codenames_of(code):
    ddl = DDL_PATH.read_text(encoding="utf-8")
    block = ddl[ddl.index(f"g.ma_nhom_quyen = '{code}'"):]
    block = block[: block.index(";")]
    return set(re.findall(r"'(\w+)'", block)) - {code}


class VanThuPermissionTest(TestCase):
    def test_database_after_migrate_has_exactly_thirty_five_permissions(self):
        self.assertEqual(codenames_of("VT"), EXPECTED)
        self.assertEqual(len(EXPECTED_0014), 30)
        self.assertEqual(len(EXPECTED), 35)

    def test_release_ddl_seeds_the_same_list(self):
        self.assertEqual(ddl_codenames_of("VT"), EXPECTED)

    def test_rbac_seed_plus_later_grants_match(self):
        seed = GROUP_PERMISSIONS["Văn thư"]
        self.assertEqual(len(seed), len(set(seed)))
        self.assertEqual(set(seed) | LATER_MIGRATION_GRANTS, EXPECTED)
        self.assertFalse(set(seed) & STILL_REMOVED)

    def test_migration_list_matches_expected(self):
        self.assertEqual(set(migration.VAN_THU_PERMISSIONS), EXPECTED_0014)
        self.assertEqual(set(migration.OLD_VAN_THU_PERMISSIONS), EXPECTED_0014 | REMOVED)

    def test_migration_removes_hand_grants_and_is_idempotent(self):
        vt = group_of("VT")
        vt.permissions.add(*Permission.objects.filter(codename__in=REMOVED | {"view_nhomquyen"}))
        vt.permissions.remove(Permission.objects.get(codename="use_aiassistant"))
        others = {code: codenames_of(code) for code in ("CV", "TP", "BGD", "ADMIN", "TLBGD", "KT")}

        migration.apply_van_thu_permissions(None, SchemaEditorStub)
        migration.apply_van_thu_permissions(None, SchemaEditorStub)

        self.assertEqual(codenames_of("VT"), CURRENT_0014)
        for code, before in others.items():
            self.assertEqual(codenames_of(code), before, code)

    def test_reverse_restores_previous_seed(self):
        migration.restore_old_van_thu_permissions(None, SchemaEditorStub)
        self.assertEqual(codenames_of("VT"), CURRENT_0014 | (REMOVED - GONE_BY_0018))
        migration.apply_van_thu_permissions(None, SchemaEditorStub)
        self.assertEqual(codenames_of("VT"), CURRENT_0014)


class VanThuDocumentApiTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.clerk = User.objects.create_user(username="vt_api", password="TestOnly12345")
        self.clerk.groups.add(group_of("VT"))
        owner = User.objects.create_user(username="vt_owner", password="TestOnly12345")
        self.other_doc = VanBanDen.objects.create(
            nam=2026, so_hieu="1/VT-KHAC", so_thu_tu=1, trich_yeu="Văn bản của người khác", nguoi_tao=owner,
        )
        self.own_doc = VanBanDen.objects.create(
            nam=2026, so_hieu="2/VT-MINH", so_thu_tu=2, trich_yeu="Văn bản do Văn thư tạo", nguoi_tao=self.clerk,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.clerk)

    def test_cannot_edit_or_delete_document_of_another_user(self):
        res = self.client.patch(f"/api/documents/{self.other_doc.id}/", {"trich_yeu": "Sửa"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.delete(f"/api/documents/{self.other_doc.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.other_doc.refresh_from_db()
        self.assertEqual(self.other_doc.trich_yeu, "Văn bản của người khác")

    def test_can_still_edit_own_document(self):
        res = self.client.patch(f"/api/documents/{self.own_doc.id}/", {"trich_yeu": "Văn thư sửa"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
