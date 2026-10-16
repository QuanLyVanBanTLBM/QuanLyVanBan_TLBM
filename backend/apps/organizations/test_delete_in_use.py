"""
B8 (QA 14/10): không xóa Đơn vị / Chức vụ khi module khác còn dùng id của nó (DDL: ON DELETE RESTRICT).
"""
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Position
from organizations.models import DonVi, KhoiKhuVuc
from organizations.references import POSITION_REFERENCES, UNIT_REFERENCES
from signing.models import SigningProcess, SigningProcessStep, SigningProcessStepSigner


class ReferenceListTest(TestCase):
    def test_every_reference_points_to_an_existing_model_field(self):
        # Gõ sai tên model/cột thì kiểm tra sẽ âm thầm bỏ qua, nên khóa lại bằng test.
        for app_label, model_name, field in UNIT_REFERENCES + POSITION_REFERENCES:
            model = apps.get_model(app_label, model_name)
            self.assertIn(field, {f.attname for f in model._meta.concrete_fields}, f"{model_name}.{field}")


class DeleteInUseTest(TestCase):
    def setUp(self):
        self.region = KhoiKhuVuc.objects.create(ten="Khối QA")
        self.unit = DonVi.objects.create(khoi=self.region, stt_uu_tien=1, ten="Phòng đang dùng")
        self.free_unit = DonVi.objects.create(khoi=self.region, stt_uu_tien=2, ten="Phòng trống")
        self.position = Position.objects.create(display_order=900, name="Chức vụ đang dùng")
        self.free_position = Position.objects.create(display_order=901, name="Chức vụ trống")
        user = get_user_model().objects.create_user(
            username="qa_delete", password="x", email="qa_delete@example.com", don_vi=self.free_unit
        )
        user.user_permissions.add(*Permission.objects.filter(codename__in=["delete_donvi", "delete_chucvu"]))
        self.client = APIClient()
        self.client.force_authenticate(user=user)

        process = SigningProcess.objects.create(
            ma_quy_trinh="QA-B8", ten_quy_trinh="QA", pham_vi="PHONG_BAN", don_vi_ap_dung_id=self.unit.pk, create_by=user
        )
        step = SigningProcessStep.objects.create(quy_trinh=process, cap_ky=1, ten_cap_ky="Cấp 1", thu_tu=1)
        SigningProcessStepSigner.objects.create(
            buoc_quy_trinh=step, chuc_vu_id=self.position.pk, pham_vi_chuc_vu="DON_VI_NGUOI_TAO", thu_tu=1
        )

    def test_unit_used_by_signing_process_is_not_deleted(self):
        res = self.client.delete(f"/api/organizations/units/{self.unit.pk}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["key"], "organizations.messages.unitInUse")
        self.assertTrue(DonVi.objects.filter(pk=self.unit.pk).exists())

    def test_position_used_by_signing_step_is_not_deleted(self):
        res = self.client.delete(f"/api/positions/{self.position.pk}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "positions.messages.inUseByModule")
        self.assertTrue(Position.objects.filter(pk=self.position.pk).exists())

    def test_unit_with_employees_keeps_its_own_message(self):
        res = self.client.delete(f"/api/organizations/units/{self.free_unit.pk}/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["key"], "organizations.messages.unitHasEmployees")

    def test_unused_unit_and_position_are_still_deleted(self):
        spare = DonVi.objects.create(khoi=self.region, stt_uu_tien=3, ten="Phòng xóa được")
        self.assertEqual(self.client.delete(f"/api/organizations/units/{spare.pk}/").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/positions/{self.free_position.pk}/").status_code, 204)
        self.assertFalse(DonVi.objects.filter(pk=spare.pk).exists())
        self.assertFalse(Position.objects.filter(pk=self.free_position.pk).exists())
