"""
Thêm văn bản đến/đi phạm vi Hạn chế (HAN_CHE) cần quyền riêng add_han_che_vanbanden / add_han_che_vanbandi
(nhóm ADMIN, VT); quyền add_vanbanden / add_vanbandi chỉ đủ để thêm văn bản Nội bộ.
Áp dụng cho tạo trực tiếp (POST /api/documents/) và import Excel.
"""
import io

import openpyxl
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents.models import PhamVi, VanBanDen, VanBanDi
from documents.services import ensure_standard_hoso_and_doc_types, generate_excel_template, import_from_excel
from organizations.models import DonVi, KhoiKhuVuc
from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan

MODELS = {"DEN": VanBanDen, "DI": VanBanDi}


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


class ThemVanBanHanCheTest(TestCase):
    def setUp(self):
        User = get_user_model()

        def user_with(username, *codenames, group=None):
            user = User.objects.create_user(username=username, password="TestOnly12345")
            if group:
                user.groups.add(group_of(group))
            if codenames:
                user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
            return user

        # Có quyền thêm văn bản (Nội bộ) và import, chưa có quyền thêm văn bản hạn chế.
        self.adder = user_with(
            "thc_them", "add_vanbanden", "add_vanbandi", "import_vanbanden", "import_vanbandi"
        )
        self.adder_den_only = user_with("thc_hc_den", "add_vanbanden", "add_vanbandi", "add_han_che_vanbanden")
        self.clerk = user_with("thc_vt", group="VT")
        self.admin_group_user = user_with("thc_admin", group="ADMIN")
        self.specialist = user_with("thc_cv", group="CV")
        self.staff = user_with("thc_staff")
        self.staff.is_staff = True
        self.staff.save()
        self.recipient = user_with("thc_nhan", group="CV")

        khoi = KhoiKhuVuc.objects.first() or KhoiKhuVuc.objects.create(ten="KHỐI HÀNH CHÍNH")
        self.dv_hdt = DonVi.objects.filter(ten="Hội đồng trường").first()
        if not self.dv_hdt:
            max_stt = (DonVi.objects.aggregate(m=models.Max("stt_uu_tien"))["m"] or 0) + 1
            self.dv_hdt = DonVi.objects.create(khoi=khoi, ten="Hội đồng trường", stt_uu_tien=max_stt)
        self.recipient.don_vi = self.dv_hdt
        self.recipient.save(update_fields=["don_vi"])

        ensure_standard_hoso_and_doc_types()
        self.hs_tlm = HoSo.objects.filter(so_ky_hieu="HS-TLM").first()
        if not self.hs_tlm:
            self.hs_tlm = HoSo.objects.create(
                ten_ho_so="Hồ sơ tài liệu mật",
                so_ky_hieu="HS-TLM",
                nguoi_lap=self.admin_group_user,
            )
        RecordLoaiVanBan.objects.get_or_create(ho_so=self.hs_tlm, ten_loai="Báo cáo")

    def post_document(self, user, loai, pham_vi, so_hieu):
        client = APIClient()
        client.force_authenticate(user=user)
        body = {
            "loai": loai,
            "nam": 2026,
            "so_hieu": so_hieu,
            "trich_yeu": f"Thử thêm {pham_vi}",
            "pham_vi": pham_vi,
            "ngay_ban_hanh": "2026-09-22T09:00:00Z",
        }
        if pham_vi == "HAN_CHE":
            body["nguoi_nhan"] = [self.recipient.id]
        return client.post("/api/documents/", body, format="json")

    def test_user_with_only_add_permission_cannot_create_restricted_document(self):
        for loai in ("DEN", "DI"):
            response = self.post_document(self.adder, loai, "HAN_CHE", f"01/{loai}-HC-TU-CHOI")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, loai)
            self.assertIn("văn bản hạn chế", str(response.data["detail"]), loai)
            self.assertFalse(MODELS[loai].objects.filter(so_hieu=f"01/{loai}-HC-TU-CHOI").exists(), loai)

    def test_user_with_only_add_permission_still_creates_internal_document(self):
        for loai in ("DEN", "DI"):
            response = self.post_document(self.adder, loai, "NOI_BO", f"02/{loai}-NB-OK")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, (loai, response.data))
            self.assertEqual(response.data["pham_vi"], "NOI_BO")

    def test_default_scope_is_internal_and_needs_no_restricted_permission(self):
        client = APIClient()
        client.force_authenticate(user=self.adder)
        response = client.post(
            "/api/documents/",
            {"loai": "DEN", "nam": 2026, "so_hieu": "03/DEN-MAC-DINH", "trich_yeu": "Không gửi pham_vi"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["pham_vi"], "NOI_BO")

    def test_restricted_permission_is_per_document_kind(self):
        response = self.post_document(self.adder_den_only, "DEN", "HAN_CHE", "04/DEN-HC-OK")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["pham_vi"], "HAN_CHE")
        # Quyền của văn bản đến không dùng được cho văn bản đi dù người này có add_vanbandi.
        denied = self.post_document(self.adder_den_only, "DI", "HAN_CHE", "04/DI-HC-TU-CHOI")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_clerk_and_admin_group_create_restricted_documents(self):
        for user in (self.clerk, self.admin_group_user):
            for loai in ("DEN", "DI"):
                so_hieu = f"05/{loai}-HC-{user.username}"
                response = self.post_document(user, loai, "HAN_CHE", so_hieu)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, (user.username, loai, response.data))
                self.assertEqual(response.data["pham_vi"], "HAN_CHE")

    def test_is_staff_flag_alone_does_not_grant_restricted_creation(self):
        for loai in ("DEN", "DI"):
            response = self.post_document(self.staff, loai, "HAN_CHE", f"05/{loai}-HC-staff")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, (loai, response.data))

    def test_user_without_any_add_permission_is_forbidden_for_both_scopes(self):
        for pham_vi in ("NOI_BO", "HAN_CHE"):
            response = self.post_document(self.specialist, "DEN", pham_vi, f"06/DEN-{pham_vi}")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, pham_vi)

    # ── Import Excel ──────────────────────────────────────────────

    def restricted_di_workbook(self, so_hieu):
        wb = openpyxl.load_workbook(generate_excel_template("DI", "HAN_CHE"))
        wb.active.append([
            2026, so_hieu, "Hạn chế", "22/09/2026", "22/09/2026",
            "Trích yếu hợp lệ cho văn bản hạn chế", "HS-TLM", "Báo cáo", "Ban Giám hiệu",
            self.dv_hdt.ten, self.recipient.username, "Hiệu trưởng", "Hiệu trưởng",
            "CON_HIEU_LUC", "", "tai_lieu_hc.pdf", "", "",
        ])
        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream

    def test_import_restricted_template_requires_permission(self):
        for loai in ("DEN", "DI"):
            result = import_from_excel(generate_excel_template(loai, "HAN_CHE"), loai, self.adder, pham_vi="HAN_CHE")
            self.assertEqual(result["created"], 0, loai)
            self.assertIn("quyền thêm văn bản hạn chế", result["errors"][0]["message"], loai)

    def test_import_restricted_rows_creates_nothing_without_permission(self):
        result = import_from_excel(self.restricted_di_workbook("07/DI-HC-TU-CHOI"), "DI", self.adder, pham_vi="HAN_CHE")
        self.assertEqual(result["created"], 0)
        self.assertFalse(VanBanDi.objects.filter(so_hieu="07/DI-HC-TU-CHOI").exists())

    def test_import_restricted_rows_with_permission(self):
        for user in (self.clerk, self.admin_group_user):
            so_hieu = f"08/DI-HC-{user.username}"
            result = import_from_excel(self.restricted_di_workbook(so_hieu), "DI", user, pham_vi="HAN_CHE")
            self.assertEqual(result["created"], 1, (user.username, result))
            self.assertEqual(VanBanDi.objects.get(so_hieu=so_hieu).pham_vi, PhamVi.HAN_CHE)

    def test_import_internal_still_allowed_without_restricted_permission(self):
        wb = openpyxl.load_workbook(generate_excel_template("DI", "NOI_BO"))
        wb.active.append([
            2026, "09/DI-NB-OK", "Nội bộ", "22/09/2026", "22/09/2026",
            "Trích yếu hợp lệ cho văn bản nội bộ", "HS-HCQT", "Công văn", "Ban Giám hiệu",
            self.dv_hdt.ten, self.recipient.username, "Hiệu trưởng", "Hiệu trưởng",
            "CON_HIEU_LUC", "", "tai_lieu_nb.pdf", "", "",
        ])
        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        result = import_from_excel(stream, "DI", self.adder, pham_vi="NOI_BO")
        self.assertEqual(result["created"], 1, result)

    def test_import_api_returns_error_message_without_permission(self):
        client = APIClient()
        client.force_authenticate(user=self.adder)
        upload = SimpleUploadedFile(
            "hc.xlsx",
            self.restricted_di_workbook("10/DI-HC-API").read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = client.post(
            "/api/documents/import/",
            {"file": upload, "loai": "DI", "pham_vi": "HAN_CHE"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quyền thêm văn bản hạn chế", response.data["error"])
        self.assertFalse(VanBanDi.objects.filter(so_hieu="10/DI-HC-API").exists())
