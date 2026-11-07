"""
Quản trị viên (nhóm ADMIN, superuser) xóa được văn bản hạn chế hết hiệu lực (issue #610):
- API: DELETE trả 204, cờ can_delete khớp với kết quả; người tạo, người nhận, Chuyên viên không xóa được.
- CSDL: trigger prevent_delete_van_ban_han_che chỉ mở trong giao dịch của lệnh xóa đó; DELETE trực tiếp vẫn bị chặn.
- Nhật ký truy cập documents_access_log giữ nguyên sau khi xóa.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authorization.models import GroupInfo
from documents.models import DocumentAccessLog, HieuLuc, PhamVi, VanBanDen, VanBanDi

MODELS = {"DEN": VanBanDen, "DI": VanBanDi}


def group_of(code):
    return Group.objects.get(pk=GroupInfo.objects.get(ma_nhom_quyen=code).pk)


class AdminXoaVanBanHanCheTest(TestCase):
    def setUp(self):
        User = get_user_model()

        def user_in(username, code=None):
            user = User.objects.create_user(username=username, password="TestOnly12345")
            if code:
                user.groups.add(group_of(code))
            return user

        self.admin_group_user = user_in("xhc_admin", "ADMIN")
        self.superuser = User.objects.create_superuser(username="xhc_su", password="TestOnly12345")
        self.creator = user_in("xhc_tao", "CV")
        self.recipient = user_in("xhc_nhan", "CV")
        self.clerk = user_in("xhc_vt", "VT")

    def make_doc(self, loai, hieu_luc=HieuLuc.HET_HIEU_LUC, so_hieu=None):
        doc = MODELS[loai].objects.create(
            so_thu_tu=1,
            so_hieu=so_hieu or f"1/{loai}-XHC",
            nam=2026,
            trich_yeu=f"Văn bản hạn chế {loai}",
            nguoi_tao=self.creator,
            pham_vi=PhamVi.HAN_CHE,
            hieu_luc=hieu_luc,
        )
        doc.nguoi_nhan.add(self.recipient)
        return doc

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def delete(self, user, loai, doc):
        return self.client_for(user).delete(f"/api/documents/{doc.pk}/?loai={loai}")

    def test_admin_deletes_expired_restricted_document(self):
        for loai in ("DEN", "DI"):
            for user in (self.admin_group_user, self.superuser):
                doc = self.make_doc(loai, so_hieu=f"2/{loai}-{user.username}")
                detail = self.client_for(user).get(f"/api/documents/{doc.pk}/?loai={loai}")
                self.assertEqual(detail.status_code, status.HTTP_200_OK, (loai, user.username))
                self.assertTrue(detail.data["can_delete"], (loai, user.username))
                logs_before = DocumentAccessLog.objects.filter(document_id=doc.pk).count()
                self.assertGreater(logs_before, 0)

                response = self.delete(user, loai, doc)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, (loai, user.username))
                self.assertFalse(MODELS[loai].objects.filter(pk=doc.pk).exists())
                # Nhật ký truy cập không có khóa ngoại tới văn bản nên còn nguyên.
                self.assertEqual(DocumentAccessLog.objects.filter(document_id=doc.pk).count(), logs_before)

    def test_others_cannot_delete_restricted_document(self):
        for loai in ("DEN", "DI"):
            doc = self.make_doc(loai, so_hieu=f"3/{loai}-KHONG-XOA")
            for user in (self.creator, self.recipient, self.clerk):
                response = self.delete(user, loai, doc)
                self.assertIn(
                    response.status_code,
                    (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
                    (loai, user.username),
                )
                self.assertTrue(MODELS[loai].objects.filter(pk=doc.pk).exists(), (loai, user.username))

    def test_creator_gets_forbidden_message_on_active_restricted_document(self):
        doc = self.make_doc("DEN", hieu_luc=HieuLuc.CON_HIEU_LUC, so_hieu="4/DEN-CON-HL")
        response = self.delete(self.creator, "DEN", doc)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("không được phép xóa", str(response.data))
        self.assertTrue(VanBanDen.objects.filter(pk=doc.pk).exists())

    def test_model_delete_still_refuses_without_permission_flag(self):
        doc = self.make_doc("DEN", so_hieu="5/DEN-MODEL")
        with self.assertRaises(ValidationError):
            doc.delete()
        self.assertTrue(VanBanDen.objects.filter(pk=doc.pk).exists())

    def test_database_trigger_blocks_direct_delete_and_view_closes_it_afterwards(self):
        for loai, table in (("DEN", "documents_vanbanden"), ("DI", "documents_vanbandi")):
            doc = self.make_doc(loai, so_hieu=f"6/{loai}-TRIGGER")
            with self.assertRaises(DatabaseError):
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", [doc.pk])
            self.assertTrue(MODELS[loai].objects.filter(pk=doc.pk).exists())

            # Quản trị viên xóa qua API xong thì biến phiên được đóng: lệnh DELETE trực tiếp kế tiếp vẫn bị chặn.
            admin_doc = self.make_doc(loai, so_hieu=f"7/{loai}-QUAN-TRI")
            self.assertEqual(
                self.delete(self.admin_group_user, loai, admin_doc).status_code, status.HTTP_204_NO_CONTENT
            )
            with self.assertRaises(DatabaseError):
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", [doc.pk])
            self.assertTrue(MODELS[loai].objects.filter(pk=doc.pk).exists())
