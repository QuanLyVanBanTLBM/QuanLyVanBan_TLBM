"""
Kiểm thử tính cô lập nghiêm ngặt của tệp đính kèm giữa các phân hệ:
Văn bản Đến vs Văn bản Đi, và Thường vs Hạn chế (Confidential).
Đảm bảo ngăn ngừa tuyệt đối lỗi hiển thị chéo tệp (ID collision & cross-model fallback).
"""
import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import (
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    DocumentAccessLog,
)
from documents.serializers import (
    DocumentAttachmentSerializer,
    VanBanDenAttachmentSerializer,
    VanBanDiAttachmentSerializer,
    DocumentListSerializer,
)

User = get_user_model()
TEMP_STORAGE = tempfile.mkdtemp()


def make_user(username, is_staff=False, perms=()):
    user = User.objects.create_user(username=username, password="TestPassword123", is_staff=is_staff)
    for codename in perms:
        try:
            perm = Permission.objects.get(codename=codename)
            user.user_permissions.add(perm)
        except Permission.DoesNotExist:
            pass
    return user


def api_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE, MEDIA_ROOT=TEMP_STORAGE)
class AttachmentCrossModuleIsolationTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_STORAGE, ignore_errors=True)

    def setUp(self):
        self.admin_user = make_user("admin_test", is_staff=True, perms=(
            "view_vanbanden", "view_vanbandi", "view_han_che_vanbanden", "view_han_che_vanbandi"
        ))
        self.normal_user = make_user("normal_user", perms=("view_vanbanden", "view_vanbandi"))
        self.unauthorized_user = make_user("unauthorized_user")

        # Tạo văn bản Đến
        self.vb_den = VanBanDen.objects.create(
            nam=2026,
            so_hieu="100/DEN",
            so_thu_tu=100,
            trich_yeu="Văn bản đến số 100",
            nguoi_tao=self.admin_user,
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
        )
        self.att_den = VanBanDenAttachment.objects.create(
            document=self.vb_den,
            name="HoaDon_Test_Den.pdf",
            file=SimpleUploadedFile("HoaDon_Test_Den.pdf", b"%PDF-1.4 mock den content", content_type="application/pdf"),
            nguoi_tao=self.admin_user,
        )

        # Tạo văn bản Đi
        self.vb_di = VanBanDi.objects.create(
            nam=2026,
            so_hieu="200/DI",
            so_thu_tu=200,
            trich_yeu="Văn bản đi số 200",
            nguoi_tao=self.admin_user,
            pham_vi=PhamVi.NOI_BO,
            hien_thi=True,
        )
        self.att_di = VanBanDiAttachment.objects.create(
            document=self.vb_di,
            name="QuyetDinh_Test_Di.pdf",
            file=SimpleUploadedFile("QuyetDinh_Test_Di.pdf", b"%PDF-1.4 mock di content", content_type="application/pdf"),
            nguoi_tao=self.admin_user,
        )

        # Tạo văn bản Mật / Hạn chế
        self.vb_mat = VanBanDen.objects.create(
            nam=2026,
            so_hieu="300/MAT",
            so_thu_tu=300,
            trich_yeu="Văn bản mật số 300",
            nguoi_tao=self.admin_user,
            pham_vi=PhamVi.HAN_CHE,
            hien_thi=True,
        )
        self.att_mat = VanBanDenAttachment.objects.create(
            document=self.vb_mat,
            name="TaiLieuMat.pdf",
            file=SimpleUploadedFile("TaiLieuMat.pdf", b"%PDF-1.4 mock confidential", content_type="application/pdf"),
            nguoi_tao=self.admin_user,
        )

    def test_serializers_generate_strict_loai_and_pham_vi_query_params(self):
        """Serializer phải sinh ra URL download có chứa đúng tham số ?loai= và &pham_vi=."""
        url_den = VanBanDenAttachmentSerializer(self.att_den).data["file"]
        self.assertIn("loai=DEN", url_den)
        self.assertNotIn("pham_vi=HAN_CHE", url_den)

        url_di = VanBanDiAttachmentSerializer(self.att_di).data["file"]
        self.assertIn("loai=DI", url_di)
        self.assertNotIn("pham_vi=HAN_CHE", url_di)

        url_mat = VanBanDenAttachmentSerializer(self.att_mat).data["file"]
        self.assertIn("loai=DEN", url_mat)
        self.assertIn("pham_vi=HAN_CHE", url_mat)

        # DocumentAttachmentSerializer (Serializer chung)
        gen_url_den = DocumentAttachmentSerializer(self.att_den).data["file"]
        self.assertIn("loai=DEN", gen_url_den)

        gen_url_di = DocumentAttachmentSerializer(self.att_di).data["file"]
        self.assertIn("loai=DI", gen_url_di)

        # DocumentListSerializer
        list_url_di = DocumentListSerializer(self.vb_di).data["first_attachment_url"]
        self.assertIn("loai=DI", list_url_di)

        list_url_den = DocumentListSerializer(self.vb_den).data["first_attachment_url"]
        self.assertIn("loai=DEN", list_url_den)

    def test_download_outbound_attachment_with_loai_param_returns_outbound_file(self):
        """Tải tệp văn bản đi với ?loai=DI trả về đúng tệp của văn bản đi."""
        client = api_for(self.admin_user)
        url = f"/api/documents/{self.vb_di.pk}/attachments/{self.att_di.pk}/download/?loai=DI"
        resp = client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"%PDF-1.4 mock di content", resp.content)
        self.assertIn("QuyetDinh_Test_Di.pdf", resp.headers.get("Content-Disposition", ""))

    def test_download_cross_module_tampering_is_rejected(self):
        """Yêu cầu tệp của VB Đến nhưng cố ý truyền loai=DI hoặc document_id của VB Đi phải bị từ chối 404."""
        client = api_for(self.admin_user)
        # Giả lập truy vấn chéo: dùng doc_id của VB Đi nhưng yêu cầu tệp đính kèm của VB Đến
        url = f"/api/documents/{self.vb_di.pk}/attachments/{self.att_den.pk}/download/?loai=DI"
        resp = client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Giả lập truy vấn chéo: dùng doc_id của VB Đến nhưng yêu cầu tệp đính kèm của VB Đi
        url_cross = f"/api/documents/{self.vb_den.pk}/attachments/{self.att_di.pk}/download/?loai=DEN"
        resp_cross = client.get(url_cross)
        self.assertEqual(resp_cross.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_fallback_referer_outgoing_routes_to_vanbandi(self):
        """Nếu thiếu query param ?loai=, Referer /documents/outgoing định tuyến chính xác sang VB Đi."""
        client = api_for(self.admin_user)
        url = f"/api/documents/{self.vb_di.pk}/attachments/{self.att_di.pk}/download/"
        resp = client.get(url, HTTP_REFERER="http://localhost:5173/documents/outgoing/200")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"%PDF-1.4 mock di content", resp.content)

    def test_confidential_document_unauthorized_download_returns_404_masking(self):
        """Người dùng không có quyền truy cập VB Hạn chế khi tải tệp sẽ nhận 404 Masking và ghi log BI_TU_CHOI."""
        client = api_for(self.normal_user)
        url = f"/api/documents/{self.vb_mat.pk}/attachments/{self.att_mat.pk}/download/?loai=DEN&pham_vi=HAN_CHE"
        resp = client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Kiểm tra nhật ký truy cập không thể chối bỏ (WORM log)
        denied_log = DocumentAccessLog.objects.filter(
            document_id=self.vb_mat.pk,
            user=self.normal_user,
            hanh_dong=DocumentAccessLog.HanhDong.BI_TU_CHOI,
        ).exists()
        self.assertTrue(denied_log)
