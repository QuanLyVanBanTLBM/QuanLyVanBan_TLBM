import importlib
from datetime import datetime, timezone
from unittest.mock import patch

from django.apps import apps as global_apps
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase

from records.models import HoSo, LoaiVanBan


organizations_seed = importlib.import_module("organizations.migrations.0005_reference_data_ddl")
accounts_seed = importlib.import_module("accounts.migrations.0006_reference_data_ddl")
account_password_fix = importlib.import_module("accounts.migrations.0007_normalize_system_account_password")
records_seed = importlib.import_module("records.migrations.0003_reference_data_ddl")


def seed_reference_data():
    with connection.schema_editor() as editor:
        organizations_seed.seed(global_apps, editor)
        accounts_seed.seed(global_apps, editor)
        account_password_fix.normalize_system_seed_password(global_apps, editor)
        records_seed.seed(global_apps, editor)



class RecordsModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_reference_data()
        user_model = get_user_model()
        cls.user = user_model._default_manager.create_user(username="records_admin_test", password="test-only")

    def make_hsc_non_system(self, **updates):
        existing = HoSo.objects.get(so_ky_hieu="HSC")
        changes = {"is_he_thong": False, **updates}

        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE records_hoso "
                "DISABLE TRIGGER trg_hoso_prevent_update_he_thong"
            )
        try:
            HoSo.objects.filter(pk=existing.pk).update(**changes)
        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE records_hoso "
                    "ENABLE TRIGGER trg_hoso_prevent_update_he_thong"
                )

        existing.refresh_from_db()
        return existing

    def test_priority_is_assigned_in_order(self):
        first = HoSo.objects.create(so_ky_hieu="A", ten_ho_so="A", nguoi_lap=self.user)
        second = HoSo.objects.create(so_ky_hieu="B", ten_ho_so="B", nguoi_lap=self.user)
        self.assertEqual(second.stt_uu_tien, first.stt_uu_tien + 1)

    def test_system_dossier_seed_is_idempotent_and_protected(self):
        call_command("ensure_common_hoso", verbosity=0)
        call_command("ensure_common_hoso", verbosity=0)
        self.assertEqual(HoSo.objects.filter(is_he_thong=True).count(), 1)
        dossier = HoSo.objects.get(is_he_thong=True)
        with transaction.atomic():
            with self.assertRaises(DatabaseError):
                HoSo.objects.filter(pk=dossier.pk).delete()
        self.assertTrue(HoSo.objects.filter(pk=dossier.pk).exists())

    def test_system_dossier_seed_uses_next_priority_when_first_is_occupied(self):
        highest_priority = HoSo.objects.order_by("-stt_uu_tien").values_list(
            "stt_uu_tien", flat=True
        ).first() or 0
        legacy_hsc = self.make_hsc_non_system(
            so_ky_hieu="HSC-LEGACY",
            stt_uu_tien=highest_priority + 1,
        )
        priority_one = HoSo.objects.filter(stt_uu_tien=1).first()
        if priority_one is None:
            priority_one = HoSo.objects.create(
                stt_uu_tien=1,
                so_ky_hieu="HS-FIRST-PRIORITY",
                ten_ho_so="Hồ sơ chiếm ưu tiên đầu tiên",
                nguoi_lap=self.user,
            )

        self.assertFalse(HoSo.objects.filter(is_he_thong=True).exists())
        self.assertFalse(HoSo.objects.filter(so_ky_hieu="HSC").exists())
        self.assertEqual(priority_one.stt_uu_tien, 1)

        call_command("ensure_common_hoso", verbosity=0)

        common = HoSo.objects.get(is_he_thong=True)
        self.assertEqual(common.so_ky_hieu, "HSC")
        self.assertEqual(common.stt_uu_tien, legacy_hsc.stt_uu_tien + 1)
        self.assertEqual(HoSo.objects.filter(is_he_thong=True).count(), 1)

    def test_system_dossier_seed_promotes_existing_hsc(self):
        existing = self.make_hsc_non_system()
        existing.ten_ho_so = "Hồ sơ HSC cần được nâng cờ hệ thống"
        existing.save(update_fields=["ten_ho_so"])

        call_command("ensure_common_hoso", verbosity=0)

        existing.refresh_from_db()
        self.assertTrue(existing.is_he_thong)
        self.assertEqual(existing.ten_ho_so, "Hồ sơ HSC cần được nâng cờ hệ thống")
        self.assertEqual(HoSo.objects.filter(so_ky_hieu="HSC").count(), 1)
        self.assertEqual(HoSo.objects.filter(is_he_thong=True).count(), 1)

    def test_system_dossier_seed_preserves_existing_hsc(self):
        existing = HoSo.objects.get(so_ky_hieu="HSC")
        existing.ten_ho_so = "Hồ sơ chung do kiểm thử chỉnh sửa"
        existing.save(update_fields=["ten_ho_so"])

        call_command("ensure_common_hoso", verbosity=0)

        existing.refresh_from_db()
        self.assertTrue(existing.is_he_thong)
        self.assertEqual(existing.ten_ho_so, "Hồ sơ chung do kiểm thử chỉnh sửa")
        self.assertEqual(HoSo.objects.filter(is_he_thong=True).count(), 1)

    def test_system_dossier_flag_cannot_be_lowered(self):
        call_command("ensure_common_hoso", verbosity=0)
        dossier = HoSo.objects.get(is_he_thong=True)

        dossier.is_he_thong = False
        with self.assertRaises(ValueError):
            dossier.save(update_fields=["is_he_thong"])

        dossier.refresh_from_db()
        self.assertTrue(dossier.is_he_thong)

        with transaction.atomic():
            with self.assertRaises(DatabaseError):
                HoSo.objects.filter(pk=dossier.pk).update(is_he_thong=False)

        dossier.refresh_from_db()
        self.assertTrue(dossier.is_he_thong)

    def test_model_normalizes_codes_and_document_type_names(self):
        dossier = HoSo.objects.create(
            so_ky_hieu="  HS-TRIM  ",
            ten_ho_so="  Hồ sơ chuẩn hóa  ",
            nguoi_lap=self.user,
        )
        document_type = LoaiVanBan.objects.create(
            ho_so=dossier,
            ten_loai="  Quyết định  ",
        )

        self.assertEqual(dossier.so_ky_hieu, "HS-TRIM")
        self.assertEqual(dossier.ten_ho_so, "Hồ sơ chuẩn hóa")
        self.assertEqual(document_type.ten_loai, "Quyết định")

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                HoSo.objects.create(
                    so_ky_hieu=" HS-TRIM ",
                    ten_ho_so="Hồ sơ trùng",
                    nguoi_lap=self.user,
                )

    def test_model_rejects_blank_codes_and_document_type_names(self):
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                HoSo.objects.create(
                    so_ky_hieu="   ",
                    ten_ho_so="Hồ sơ không hợp lệ",
                    nguoi_lap=self.user,
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                HoSo.objects.create(
                    so_ky_hieu="HS-BLANK-NAME",
                    ten_ho_so="   ",
                    nguoi_lap=self.user,
                )

        dossier = HoSo.objects.create(
            so_ky_hieu="HS-VALID",
            ten_ho_so="Hồ sơ hợp lệ",
            nguoi_lap=self.user,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                LoaiVanBan.objects.create(ho_so=dossier, ten_loai="   ")

    def test_document_type_names_are_unique_per_dossier_after_trim_and_lower(self):
        dossier = HoSo.objects.create(so_ky_hieu="A", ten_ho_so="A", nguoi_lap=self.user)
        LoaiVanBan.objects.create(ho_so=dossier, ten_loai="Quyết định")
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                LoaiVanBan.objects.create(ho_so=dossier, ten_loai=" quyết định ")

class RecordsApiTests(APITestCase):
    def setUp(self):
        seed_reference_data()
        user_model = get_user_model()
        self.user = user_model._default_manager.create_user(
            username="api-user",
            password="test-only",
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)
        self.dossier_list_url = reverse(
            "records:dossier-list-create"
        )

    def create_dossier(self, **overrides):
        data = {
            "so_ky_hieu": "HS-001",
            "ten_ho_so": "Hồ sơ kiểm thử",
            "nguoi_lap": self.user,
            "ngay_lap": datetime(
                2026,
                9,
                30,
                tzinfo=timezone.utc,
            ),
        }
        data.update(overrides)
        return HoSo.objects.create(**data)

    def test_authentication_is_required(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.dossier_list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_dossier_rejects_blank_code(self):
        response = self.client.post(
            self.dossier_list_url,
            {
                "so_ky_hieu": "   ",
                "ten_ho_so": "Hồ sơ không hợp lệ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("so_ky_hieu", response.data)

    def test_dossier_crud_and_response_contract(self):
        create_response = self.client.post(
            self.dossier_list_url,
            {
                "stt_uu_tien": None,
                "so_ky_hieu": " HS-API-001 ",
                "ten_ho_so": " Hồ sơ API ",
                "ngay_lap": "2026-09-30",
                "ghi_chu": "",
            },
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            create_response.data["so_ky_hieu"],
            "HS-API-001",
        )
        self.assertEqual(
            create_response.data["nguoi_lap"],
            "api-user",
        )

        dossier_id = create_response.data["id"]
        detail_url = reverse(
            "records:dossier-detail",
            args=[dossier_id],
        )

        detail_response = self.client.get(detail_url)
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
        )

        update_response = self.client.patch(
            detail_url,
            {"ten_ho_so": "Hồ sơ API đã sửa"},
            format="json",
        )
        self.assertEqual(
            update_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            update_response.data["ten_ho_so"],
            "Hồ sơ API đã sửa",
        )

        delete_response = self.client.delete(detail_url)
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_list_supports_search_year_and_pagination(self):
        self.create_dossier(
            so_ky_hieu="HS-2025",
            ten_ho_so="Hồ sơ năm 2025",
            ngay_lap=datetime(
                2025,
                1,
                1,
                tzinfo=timezone.utc,
            ),
        )
        self.create_dossier(
            so_ky_hieu="HS-2026",
            ten_ho_so="Hồ sơ năm 2026",
        )

        response = self.client.get(
            self.dossier_list_url,
            {
                "search": "2025",
                "year": "2025",
                "page_size": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["so_ky_hieu"],
            "HS-2025",
        )

    def test_system_dossier_cannot_be_deleted(self):
        dossier = HoSo.objects.get(is_he_thong=True)

        response = self.client.delete(
            reverse(
                "records:dossier-detail",
                args=[dossier.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertTrue(
            HoSo.objects.filter(pk=dossier.pk).exists()
        )

    def test_dossier_with_document_types_cannot_be_deleted(self):
        dossier = self.create_dossier()
        LoaiVanBan.objects.create(
            ho_so=dossier,
            ten_loai="Quyết định",
        )

        response = self.client.delete(
            reverse(
                "records:dossier-detail",
                args=[dossier.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    @patch(
        "records.views.HoSoDetailAPIView.perform_destroy",
        side_effect=IntegrityError("foreign key violation"),
    )
    def test_dossier_referenced_by_group2_returns_conflict(self, _perform_destroy):
        dossier = self.create_dossier()

        response = self.client.delete(
            reverse("records:dossier-detail", args=[dossier.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(HoSo.objects.filter(pk=dossier.pk).exists())

    def test_document_type_crud_and_duplicate_validation(self):
        dossier = self.create_dossier()

        list_url = reverse(
            "records:document-type-list-create",
            args=[dossier.pk],
        )

        create_response = self.client.post(
            list_url,
            {
                "ten_loai": " Quyết định ",
                "ngay_lap": "2026-09-30",
                "ghi_chu": "",
            },
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            create_response.data["ten_loai"],
            "Quyết định",
        )
        self.assertEqual(
            create_response.data["ho_so"],
            dossier.pk,
        )

        duplicate_response = self.client.post(
            list_url,
            {
                "ten_loai": " quyết ĐỊNH ",
                "ngay_lap": None,
                "ghi_chu": "",
            },
            format="json",
        )
        self.assertEqual(
            duplicate_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        document_type_id = create_response.data["id"]
        detail_url = reverse(
            "records:document-type-detail",
            args=[document_type_id],
        )

        update_response = self.client.patch(
            detail_url,
            {"ten_loai": "Thông báo"},
            format="json",
        )
        self.assertEqual(
            update_response.status_code,
            status.HTTP_200_OK,
        )

        delete_response = self.client.delete(detail_url)
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_document_type_rejects_blank_name(self):
        dossier = self.create_dossier()
        response = self.client.post(
            reverse(
                "records:document-type-list-create",
                args=[dossier.pk],
            ),
            {"ten_loai": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ten_loai", response.data)

    @patch(
        "records.views.LoaiVanBanDetailAPIView.perform_destroy",
        side_effect=IntegrityError("foreign key violation"),
    )
    def test_document_type_referenced_by_group2_returns_conflict(
        self,
        _perform_destroy,
    ):
        dossier = self.create_dossier()
        document_type = LoaiVanBan.objects.create(
            ho_so=dossier,
            ten_loai="Quyết định",
        )

        response = self.client.delete(
            reverse("records:document-type-detail", args=[document_type.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(LoaiVanBan.objects.filter(pk=document_type.pk).exists())
