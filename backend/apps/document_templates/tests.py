import atexit
import io
import re
import shutil
import tempfile
import openpyxl
from pathlib import Path
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from organizations.models import DonVi

User = get_user_model()

TEMP_STORAGE_ROOT = tempfile.mkdtemp(prefix="templates-tests-")
atexit.register(shutil.rmtree, TEMP_STORAGE_ROOT, ignore_errors=True)

from document_templates.models import (
    DanhMucTaiLieu,
    LoaiTaiLieu,
    TaiLieuChiTiet,
    ChiTietTaiLieuAttachment,
    validate_document_file,
)


class DocumentTemplatesValidationTests(TestCase):
    """Kiểm tra logic validator file đính kèm (<20MB, định dạng cho phép)"""

    def test_valid_file_passes(self):
        file = SimpleUploadedFile("quy_che_2026.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        # Không bắn ValidationError
        validate_document_file(file)

        docx_file = SimpleUploadedFile("bieu_mau.docx", b"docx sample content")
        validate_document_file(docx_file)

    def test_invalid_extension_raises_error(self):
        file = SimpleUploadedFile("malware.exe", b"binary content")
        with self.assertRaises(ValidationError) as ctx:
            validate_document_file(file)
        self.assertIn("không được hỗ trợ", str(ctx.exception))

        mp4_file = SimpleUploadedFile("video.mp4", b"video stream")
        with self.assertRaises(ValidationError) as ctx2:
            validate_document_file(mp4_file)
        self.assertIn("không được hỗ trợ", str(ctx2.exception))

    def test_oversized_file_raises_error(self):
        # Giả lập file lớn hơn 20MB
        class MockOversizedFile:
            name = "heavy_scan.pdf"
            size = 21 * 1024 * 1024  # 21MB

        with self.assertRaises(ValidationError) as ctx:
            validate_document_file(MockOversizedFile())
        self.assertIn("không được vượt quá 20MB", str(ctx.exception))


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
class DocumentTemplatesModelAndAPITests(TestCase):
    """Kiểm thử Model và API ViewSets cho Phân hệ Tài liệu & Biểu mẫu"""

    def setUp(self):
        self.client = APIClient()

        extra_user = {}
        if hasattr(User, 'ho_ten'):
            extra_user['ho_ten'] = 'Nguyen Chi Tin'
        else:
            extra_user['first_name'] = 'Chi Tin'
            extra_user['last_name'] = 'Nguyen'

        self.user = User.objects.create_user(
            username='chitin',
            password='password123',
            **extra_user
        )
        from django.contrib.auth.models import Permission
        for codename in [
            'view_loaitailieubieumau', 'add_loaitailieubieumau', 'change_loaitailieubieumau', 'delete_loaitailieubieumau',
            'view_tailieu', 'add_tailieu', 'change_tailieu', 'delete_tailieu',
        ]:
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename}
            )
            self.user.user_permissions.add(perm)

        self.admin = User.objects.create_superuser(
            username='templates_admin_test',
            email='admin@example.com',
            password='adminpassword'
        )

        # Tạo Danh mục Cấp 1
        self.cat1 = DanhMucTaiLieu.objects.create(
            stt_uu_tien=1,
            ky_hieu='TLBM-CHUNG',
            ten_tai_lieu='Tài liệu, Biểu mẫu chung',
            nguoi_lap=self.admin
        )
        self.cat2 = DanhMucTaiLieu.objects.create(
            stt_uu_tien=2,
            ky_hieu='HS-BNS',
            ten_tai_lieu='Hồ sơ Ban Nhân sự',
            nguoi_lap=self.admin
        )

        # Tạo Loại Cấp 2
        self.type1 = LoaiTaiLieu.objects.create(
            dm_tai_lieu=self.cat1,
            ten_loai='Tài liệu bảo hiểm',
            is_public=True
        )
        self.type2 = LoaiTaiLieu.objects.create(
            dm_tai_lieu=self.cat1,
            ten_loai='Biểu mẫu bảo hiểm',
            is_public=True
        )
        self.type3 = LoaiTaiLieu.objects.create(
            dm_tai_lieu=self.cat2,
            ten_loai='Hồ sơ tuyển dụng',
            is_public=True
        )

        # Tạo file đính kèm mẫu
        self.sample_file = SimpleUploadedFile(
            "quy_dinh_2026.pdf",
            b"%PDF-1.4 test document content",
            content_type="application/pdf"
        )

        # Tạo Chi tiết tài liệu
        self.doc1 = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            ky_hieu='01/QĐ-BL-2026',
            tieu_de='Quy định bảo hiểm xe cơ giới 2026',
            ngay_dang=date(2026, 1, 15),
            noi_ban_hanh='Ban Giám Đốc',
            hieu_luc='CON_HIEU_LUC',
            file_dinh_kem=self.sample_file,
            hien_thi='TAT_CA',
            nguoi_tao=self.user
        )
        self.doc1.loai_tai_lieu.add(self.type1, self.type2)

        self.doc2 = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat2,
            ky_hieu='02/BM-NS-2025',
            tieu_de='Biểu mẫu ứng viên thử việc',
            ngay_dang=date(2025, 6, 20),
            noi_ban_hanh='Phòng Nhân sự',
            hieu_luc='HET_HIEU_LUC',
            file_dinh_kem=SimpleUploadedFile("bieu_mau_cu.docx", b"docx content"),
            hien_thi='NOI_BO_PHONG_BAN',
            nguoi_tao=self.user
        )
        self.doc2.loai_tai_lieu.add(self.type3)

    def test_model_tailieuchitiet_clean_validation(self):
        """Khi hieu_luc là HET_VA_THAY_THE thì bắt buộc có link_thay_the"""
        doc = TaiLieuChiTiet(
            dm_tai_lieu=self.cat1,
            tieu_de='Văn bản bị thay thế',
            ngay_dang=date(2026, 2, 1),
            hieu_luc='HET_VA_THAY_THE',
            link_thay_the='',  # Rỗng -> phải báo lỗi
            file_dinh_kem=SimpleUploadedFile("test.pdf", b"test")
        )
        with self.assertRaises(ValidationError):
            doc.clean()

        # Thêm link thay thế hợp lệ -> thành công
        doc.link_thay_the = 'https://example.com/vb-thay-the.pdf'
        doc.clean()

    def test_api_list_documents(self):
        """Khách vãng lai xem được tài liệu TAT_CA, ẩn tài liệu NOI_BO_PHONG_BAN"""
        response = self.client.get('/api/resources/documents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Khách vãng lai chỉ thấy doc1 (TAT_CA)
        ids = [item['id'] for item in response.data] if isinstance(response.data, list) else [item['id'] for item in response.data.get('results', [])]
        self.assertIn(self.doc1.id, ids)
        self.assertNotIn(self.doc2.id, ids)

    def test_api_authenticated_user_sees_department_doc(self):
        """Người tạo xem được tài liệu nội bộ do mình tạo"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/resources/documents/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data] if isinstance(response.data, list) else [item['id'] for item in response.data.get('results', [])]
        self.assertIn(self.doc1.id, ids)
        self.assertIn(self.doc2.id, ids)

    def test_api_filtering(self):
        """Kiểm tra các bộ lọc: Cấp 1, Cấp 2, Hiệu lực, Năm, Search"""
        self.client.force_authenticate(user=self.admin)

        # Lọc theo Cấp 1: dm_tai_lieu=cat1.id
        res = self.client.get(f'/api/resources/documents/?dm_tai_lieu={self.cat1.id}')
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.doc1.id)

        # Lọc theo Cấp 2: loai_tai_lieu=type3.id
        res = self.client.get(f'/api/resources/documents/?loai_tai_lieu={self.type3.id}')
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.doc2.id)

        # Lọc theo năm: nam=2025
        res = self.client.get('/api/resources/documents/?nam=2025')
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.doc2.id)

        # Lọc theo hiệu lực: hieu_luc=CON_HIEU_LUC
        res = self.client.get('/api/resources/documents/?hieu_luc=CON_HIEU_LUC')
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.doc1.id)

        # Tìm kiếm theo từ khóa
        res = self.client.get('/api/resources/documents/?search=cơ giới')
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.doc1.id)

    def test_api_create_document(self):
        """Tạo mới tài liệu kèm upload file hợp lệ"""
        self.client.force_authenticate(user=self.user)
        new_file = SimpleUploadedFile("thong_bao_moi.pdf", b"%PDF-1.4 valid pdf", content_type="application/pdf")
        payload = {
            'dm_tai_lieu': self.cat1.id,
            'loai_tai_lieu': [self.type1.id, self.type2.id],
            'ky_hieu': '03/TB-2026',
            'tieu_de': 'Thông báo triển khai chữ ký số',
            'ngay_dang': '2026-03-01',
            'noi_ban_hanh': 'Ban Giám Đốc',
            'hieu_luc': 'CON_HIEU_LUC',
            'hien_thi': 'TAT_CA',
            'file_dinh_kem': new_file,
        }
        res = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['tieu_de'], 'Thông báo triển khai chữ ký số')
        self.assertEqual(len(res.data['loai_tai_lieu']), 2)
        self.assertEqual(len(res.data['loai_tai_lieu_names']), 2)

    def test_api_create_document_invalid_extension_rejected(self):
        """Upload file đuôi không hợp lệ bị từ chối 400 Bad Request"""
        self.client.force_authenticate(user=self.user)
        bad_file = SimpleUploadedFile("danger.exe", b"binary content")
        payload = {
            'dm_tai_lieu': self.cat1.id,
            'tieu_de': 'Tài liệu độc hại',
            'ngay_dang': '2026-03-01',
            'file_dinh_kem': bad_file,
        }
        res = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file_dinh_kem', res.data)

    def test_api_toggle_validity(self):
        """API toggle trạng thái hiệu lực"""
        self.client.force_authenticate(user=self.user)
        url = f'/api/resources/documents/{self.doc1.id}/toggle-validity/'
        res = self.client.post(url, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['hieu_luc'], 'HET_HIEU_LUC')

        # Đổi sang HET_VA_THAY_THE với link
        res2 = self.client.post(url, {
            'hieu_luc': 'HET_VA_THAY_THE',
            'link_thay_the': 'https://example.com/replacement.pdf'
        })
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['hieu_luc'], 'HET_VA_THAY_THE')

    def test_api_export_excel(self):
        """Xuất danh sách tài liệu ra file Excel (.xlsx) chuẩn và đọc được bằng openpyxl"""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/resources/documents/export-excel/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('Danh_sach_tai_lieu_', res['Content-Disposition'])

        # Mở và đọc nội dung file Excel
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertIn("DanhSachTaiLieu", wb.sheetnames)
        ws = wb["DanhSachTaiLieu"]
        # Tiêu đề tại A1
        self.assertEqual(ws["A1"].value, "DANH SÁCH TÀI LIỆU VÀ BIỂU MẪU CHUNG")
        # Header tại row 4
        self.assertEqual(ws.cell(row=4, column=1).value, "STT")
        self.assertEqual(ws.cell(row=4, column=3).value, "Tiêu đề tài liệu")
        # Ít nhất có 2 dòng dữ liệu
        self.assertGreaterEqual(ws.max_row, 5)

    def test_api_export_excel_english(self):
        """Xuất danh sách tài liệu ra file Excel (.xlsx) với ngôn ngữ tiếng Anh (?lang=en)"""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/resources/documents/export-excel/?lang=en')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('Document_List_', res['Content-Disposition'])

        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertIn("DocumentList", wb.sheetnames)
        ws = wb["DocumentList"]
        self.assertEqual(ws["A1"].value, "COMMON DOCUMENTS AND TEMPLATES DIRECTORY")
        self.assertEqual(ws.cell(row=4, column=1).value, "No.")
        self.assertEqual(ws.cell(row=4, column=3).value, "Document Title")
        self.assertGreaterEqual(ws.max_row, 5)

    def test_anonymous_user_cannot_create_or_modify_or_delete_document(self):
        """Khắc phục Lỗi 1 (P0): Người dùng ẩn danh không được phép POST, PATCH, DELETE"""
        self.client.force_authenticate(user=None)
        # Thử POST ẩn danh
        res_post = self.client.post('/api/resources/documents/', {'tieu_de': 'Tài liệu lậu'})
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)

        # Thử PATCH ẩn danh
        res_patch = self.client.patch(f'/api/resources/documents/{self.doc1.id}/', {'tieu_de': 'Sửa lậu'})
        self.assertEqual(res_patch.status_code, status.HTTP_401_UNAUTHORIZED)

        # Thử DELETE ẩn danh
        res_del = self.client.delete(f'/api/resources/documents/{self.doc1.id}/')
        self.assertEqual(res_del.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_cannot_overwrite_nguoi_tao(self):
        """Khắc phục Lỗi 2 (P1): PATCH không được phép ghi đè trường nguoi_tao"""
        self.client.force_authenticate(user=self.admin)
        other_user = User.objects.create_user(username='other_user', password='password123')
        original_creator_id = self.doc1.nguoi_tao_id

        res = self.client.patch(f'/api/resources/documents/{self.doc1.id}/', {
            'nguoi_tao': other_user.id
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.doc1.refresh_from_db()
        # nguoi_tao phải giữ nguyên là người tạo ban đầu
        self.assertEqual(self.doc1.nguoi_tao_id, original_creator_id)

    def test_toggle_validity_missing_replacement_link_returns_400(self):
        """Khắc phục Lỗi 3 (P2): Đổi sang HET_VA_THAY_THE mà thiếu link thay thế phải trả về 400 Bad Request, không được bung lỗi 500"""
        self.client.force_authenticate(user=self.user)
        url = f'/api/resources/documents/{self.doc1.id}/toggle-validity/'
        res = self.client.post(url, {
            'hieu_luc': 'HET_VA_THAY_THE',
            'link_thay_the': ''  # Rỗng -> phải trả 400
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('link_thay_the', res.data)

    def test_don_vi_id_and_con_hieu_luc_1_phan(self):
        """Kiểm tra trường don_vi_id và giá trị hiệu lực CON_HIEU_LUC_1_PHAN chuẩn DDL Base v1"""
        self.client.force_authenticate(user=self.user)
        don_vi_id = DonVi.objects.order_by("id").values_list("id", flat=True).first()
        doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            ky_hieu='05/HD-2026',
            tieu_de='Hướng dẫn nghiệp vụ một phần',
            ngay_dang=date(2026, 3, 1),
            hieu_luc='CON_HIEU_LUC_1_PHAN',
            don_vi_id=don_vi_id,
            hien_thi='NOI_BO_PHONG_BAN',
            nguoi_tao=self.user,
        )
        self.assertEqual(doc.hieu_luc, 'CON_HIEU_LUC_1_PHAN')
        self.assertEqual(doc.don_vi_id, don_vi_id)

        # Kiểm tra qua API detail
        res = self.client.get(f'/api/resources/documents/{doc.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['hieu_luc'], 'CON_HIEU_LUC_1_PHAN')
        self.assertEqual(res.data['don_vi_id'], don_vi_id)

    def test_attachment_model_and_api(self):
        """Kiểm tra bảng records_chitiettailieu_attachment và API quản lý tệp đính kèm chuẩn DDL Base v1"""
        self.client.force_authenticate(user=self.user)
        # Tạo tệp đính kèm trực tiếp
        att = ChiTietTaiLieuAttachment.objects.create(
            document=self.doc1,
            name='phu_luc_01.pdf',
            path='/media/documents/templates/phu_luc_01.pdf',
            file_size=102400,
            mime_type='application/pdf',
            nguoi_tao=self.user,
        )
        self.assertEqual(att.document_id, self.doc1.id)
        self.assertFalse(att.is_deleted)
        self.assertEqual(att.nguoi_tao, self.user)
        self.assertIsNotNone(att.created_at)

        # Truy vấn danh sách attachment qua API
        res = self.client.get(f'/api/resources/attachments/?document={self.doc1.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.data if isinstance(res.data, list) else res.data.get('results', [])
        self.assertTrue(any(item['name'] == 'phu_luc_01.pdf' for item in items))

        # Kiểm tra xóa mềm (soft delete)
        del_res = self.client.delete(f'/api/resources/attachments/{att.id}/')
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        att.refresh_from_db()
        self.assertTrue(att.is_deleted)

    def test_create_document_with_multiple_files(self):
        """Kiểm tra lưu tài liệu đính kèm nhiều file cùng lúc qua form-data"""
        self.client.force_authenticate(user=self.user)
        file1 = SimpleUploadedFile("bang_ke_01.xlsx", b"excel content", content_type="application/vnd.ms-excel")
        file2 = SimpleUploadedFile("huong_dan_01.pdf", b"%PDF-1.4 pdf content", content_type="application/pdf")
        payload = {
            'dm_tai_lieu': self.cat1.id,
            'loai_tai_lieu': [self.type1.id],
            'ky_hieu': '10/TB-MULTI-2026',
            'tieu_de': 'Thông báo kèm nhiều biểu mẫu',
            'ngay_dang': '2026-03-10',
            'noi_ban_hanh': 'Phòng Tổng Hợp',
            'hieu_luc': 'CON_HIEU_LUC',
            'hien_thi': 'TAT_CA',
            'files': [file1, file2],
        }
        res = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res.data['attachments']), 2)
        names = [a['name'] for a in res.data['attachments']]
        self.assertIn('bang_ke_01.xlsx', names)
        self.assertIn('huong_dan_01.pdf', names)

    def test_uploaded_files_stored_in_shared_tree_and_viewable(self):
        """Tệp lưu ở mau-van-ban/YYYY/MM/DD/<uuid>.<ext>, giữ đuôi riêng của biểu mẫu; xem tệp đọc từ kho dùng chung"""
        self.client.force_authenticate(user=self.user)
        payload = {
            'dm_tai_lieu': self.cat1.id,
            'loai_tai_lieu': [self.type1.id],
            'ky_hieu': '11/TB-KHO-2026',
            'tieu_de': 'Biểu mẫu lưu kho dùng chung',
            'ngay_dang': '2026-03-10',
            'noi_ban_hanh': 'Phòng Tổng Hợp',
            'hieu_luc': 'CON_HIEU_LUC',
            'hien_thi': 'TAT_CA',
            'files': [
                SimpleUploadedFile("Bảng kê.XLSX", b"excel content"),
                SimpleUploadedFile("hướng dẫn.pdf", b"%PDF-1.4 pdf content", content_type="application/pdf"),
            ],
        }
        res = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        atts = {a['name']: a for a in res.data['attachments']}
        xlsx_path = atts['Bảng kê.XLSX']['path']
        self.assertTrue(re.fullmatch(r'/media/mau-van-ban/\d{4}/\d{2}/\d{2}/[0-9a-f]{32}\.xlsx', xlsx_path), xlsx_path)
        self.assertEqual((Path(TEMP_STORAGE_ROOT) / xlsx_path.removeprefix('/media/')).read_bytes(), b"excel content")

        view = self.client.get(f"/api/resources/attachments/{atts['hướng dẫn.pdf']['id']}/view/")
        self.assertEqual(view.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(view.streaming_content), b"%PDF-1.4 pdf content")

    def test_view_attachment_outside_storage_or_missing_returns_404(self):
        self.client.force_authenticate(user=self.user)
        for stored in ('/media/../../etc/passwd', '/media/mau-van-ban/2026/01/01/khong-con.pdf', '/media/documents/templates/cu.pdf'):
            att = ChiTietTaiLieuAttachment.objects.create(document=self.doc1, name='x.pdf', path=stored, nguoi_tao=self.user)
            res = self.client.get(f'/api/resources/attachments/{att.id}/view/')
            self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND, stored)

    def test_update_document_add_and_delete_attachments(self):
        """Kiểm tra cập nhật tài liệu: xóa file cũ và tải lên file mới, lọc bỏ soft-deleted"""
        self.client.force_authenticate(user=self.user)
        # Tạo trước 2 attachment cho doc1
        att1 = ChiTietTaiLieuAttachment.objects.create(
            document=self.doc1,
            name='file_cu_1.pdf',
            path='/media/documents/templates/file_cu_1.pdf',
            file_size=5000,
            mime_type='application/pdf',
            nguoi_tao=self.user,
        )
        att2 = ChiTietTaiLieuAttachment.objects.create(
            document=self.doc1,
            name='file_cu_2.pdf',
            path='/media/documents/templates/file_cu_2.pdf',
            file_size=6000,
            mime_type='application/pdf',
            nguoi_tao=self.user,
        )

        new_file = SimpleUploadedFile("file_moi.docx", b"docx content")
        # Gửi PATCH xóa att1 và thêm new_file
        payload = {
            'tieu_de': 'Quy định bảo hiểm xe cơ giới 2026 (Đã cập nhật)',
            'files': [new_file],
            'deleted_attachment_ids': [att1.id],
        }
        res = self.client.patch(f'/api/resources/documents/{self.doc1.id}/', payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Kiểm tra trong DB: att1 đã bị xóa mềm, att2 còn nguyên
        att1.refresh_from_db()
        self.assertTrue(att1.is_deleted)
        att2.refresh_from_db()
        self.assertFalse(att2.is_deleted)

        # Danh sách trả về không chứa att1, nhưng có att2 và file_moi.docx
        active_names = [a['name'] for a in res.data['attachments']]
        self.assertNotIn('file_cu_1.pdf', active_names)
        self.assertIn('file_cu_2.pdf', active_names)
        self.assertIn('file_moi.docx', active_names)

    def test_patch_document_json_dict_does_not_crash(self):
        """Kiểm tra gọi PATCH với JSON payload (request.data là dict thông thường) không bị AttributeError"""
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(
            f'/api/resources/documents/{self.doc1.id}/',
            {'tieu_de': 'Tiêu đề cập nhật qua JSON'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['tieu_de'], 'Tiêu đề cập nhật qua JSON')

    def test_dynamic_validity_and_filtering(self):
        """Kiểm tra tính toán hiệu lực động theo thời gian thực và lọc theo hiệu lực"""
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()

        # Tạo văn bản có ngày hết hạn trong tương lai (+10 ngày)
        future_doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            tieu_de='Văn bản hết hạn tương lai',
            ngay_dang=today,
            hieu_luc='HET_HIEU_LUC',
            ngay_het_hieu_luc=today + timedelta(days=10),
            hien_thi='TAT_CA',
            nguoi_tao=self.user
        )
        self.assertFalse(future_doc.is_expired)
        self.assertEqual(future_doc.effective_hieu_luc, 'CON_HIEU_LUC')

        # Tạo văn bản có ngày hết hạn trong quá khứ (-5 ngày)
        past_doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            tieu_de='Văn bản hết hạn quá khứ',
            ngay_dang=today - timedelta(days=30),
            hieu_luc='CON_HIEU_LUC',
            ngay_het_hieu_luc=today - timedelta(days=5),
            hien_thi='TAT_CA',
            nguoi_tao=self.user
        )
        self.assertTrue(past_doc.is_expired)
        self.assertEqual(past_doc.effective_hieu_luc, 'HET_HIEU_LUC')

        self.client.force_authenticate(user=self.user)

        # Lọc theo hieu_luc=CON_HIEU_LUC phải chứa future_doc và không chứa past_doc
        res_active = self.client.get('/api/resources/documents/?hieu_luc=CON_HIEU_LUC')
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        active_items = res_active.data['results'] if isinstance(res_active.data, dict) else res_active.data
        active_ids = [d['id'] for d in active_items]
        self.assertIn(future_doc.id, active_ids)
        self.assertNotIn(past_doc.id, active_ids)

        # Lọc theo hieu_luc=HET_HIEU_LUC phải chứa past_doc và không chứa future_doc
        res_expired = self.client.get('/api/resources/documents/?hieu_luc=HET_HIEU_LUC')
        self.assertEqual(res_expired.status_code, status.HTTP_200_OK)
        expired_items = res_expired.data['results'] if isinstance(res_expired.data, dict) else res_expired.data
        expired_ids = [d['id'] for d in expired_items]
        self.assertIn(past_doc.id, expired_ids)
        self.assertNotIn(future_doc.id, expired_ids)

    def test_expiration_date_cannot_be_before_posted_date(self):
        self.client.force_authenticate(user=self.admin)
        from django.utils import timezone
        import datetime
        today = timezone.localdate()
        yesterday = today - datetime.timedelta(days=1)
        response = self.client.post('/api/resources/documents/', {
            'dm_tai_lieu': self.cat1.id,
            'loai_tai_lieu': [self.type1.id],
            'tieu_de': 'Tài liệu test ngày hết hạn không hợp lệ',
            'ngay_dang': today.strftime('%Y-%m-%d'),
            'ngay_het_hieu_luc': yesterday.strftime('%Y-%m-%d'),
            'hieu_luc': 'HET_HIEU_LUC',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ngay_het_hieu_luc', response.data)

    def test_search_by_specific_field(self):
        self.client.force_authenticate(user=self.admin)
        doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            tieu_de='Văn bản đặc biệt ABC',
            ky_hieu='99/QD-SPECIAL',
            noi_ban_hanh='Sở Kế hoạch Đầu tư',
            ngay_dang='2026-05-01',
            hieu_luc='CON_HIEU_LUC',
            nguoi_tao=self.admin
        )
        # Tìm theo search_field=code
        res = self.client.get('/api/resources/documents/?search=99/QD&search_field=code')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.data['results'] if isinstance(res.data, dict) else res.data
        ids = [d['id'] for d in items]
        self.assertIn(doc.id, ids)

        # Tìm theo search_field=title với từ khóa của code thì không thấy
        res_fail = self.client.get('/api/resources/documents/?search=99/QD&search_field=title')
        self.assertEqual(res_fail.status_code, status.HTTP_200_OK)
        items_fail = res_fail.data['results'] if isinstance(res_fail.data, dict) else res_fail.data
        ids_fail = [d['id'] for d in items_fail]
        self.assertNotIn(doc.id, ids_fail)

    def test_api_pagination_structure(self):
        """Kiểm tra cả 3 ViewSet và AttachmentViewSet đều trả về cấu trúc phân trang chuẩn (count, next, previous, results)"""
        self.client.force_authenticate(user=self.admin)

        # 1. Documents endpoint
        res_docs = self.client.get('/api/resources/documents/')
        self.assertEqual(res_docs.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res_docs.data, dict)
        self.assertIn('count', res_docs.data)
        self.assertIn('next', res_docs.data)
        self.assertIn('previous', res_docs.data)
        self.assertIn('results', res_docs.data)
        self.assertIsInstance(res_docs.data['results'], list)

        # 2. Categories endpoint
        res_cats = self.client.get('/api/resources/categories/')
        self.assertEqual(res_cats.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res_cats.data, dict)
        self.assertIn('count', res_cats.data)
        self.assertIn('next', res_cats.data)
        self.assertIn('previous', res_cats.data)
        self.assertIn('results', res_cats.data)
        self.assertIsInstance(res_cats.data['results'], list)

        # 3. Types endpoint
        res_types = self.client.get('/api/resources/types/')
        self.assertEqual(res_types.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res_types.data, dict)
        self.assertIn('count', res_types.data)
        self.assertIn('next', res_types.data)
        self.assertIn('previous', res_types.data)
        self.assertIn('results', res_types.data)
        self.assertIsInstance(res_types.data['results'], list)

    def test_attachment_idor_protection(self):
        """Khách vãng lai và user khác không thể xem metadata, preview, view hoặc xóa tệp của tài liệu NOI_BO_PHONG_BAN (chống IDOR)"""
        extra_other = {'ho_ten': 'Other User'} if hasattr(User, 'ho_ten') else {'first_name': 'Other', 'last_name': 'User'}
        other_user = User.objects.create_user(
            username='stranger_dept',
            password='password123',
            **extra_other
        )

        # Tạo file đính kèm trên tài liệu nội bộ self.doc2
        secret_att = ChiTietTaiLieuAttachment.objects.create(
            document=self.doc2,
            name="bang_luong_mat.xlsx",
            path="templates/bang_luong_mat.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            nguoi_tao=self.user,
        )

        # 1. Khách vãng lai (ẩn danh)
        self.client.logout()
        res_list = self.client.get('/api/resources/attachments/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        list_ids = [a['id'] for a in (res_list.data['results'] if isinstance(res_list.data, dict) else res_list.data)]
        self.assertNotIn(secret_att.id, list_ids)

        res_detail = self.client.get(f'/api/resources/attachments/{secret_att.id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

        res_view = self.client.get(f'/api/resources/attachments/{secret_att.id}/view/')
        self.assertEqual(res_view.status_code, status.HTTP_404_NOT_FOUND)

        res_preview = self.client.get(f'/api/resources/attachments/{secret_att.id}/preview/')
        self.assertEqual(res_preview.status_code, status.HTTP_404_NOT_FOUND)

        res_delete = self.client.delete(f'/api/resources/attachments/{secret_att.id}/')
        self.assertIn(res_delete.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND])

        # 2. Người dùng thuộc phòng ban/đơn vị khác
        self.client.force_authenticate(user=other_user)
        res_other_detail = self.client.get(f'/api/resources/attachments/{secret_att.id}/')
        self.assertEqual(res_other_detail.status_code, status.HTTP_404_NOT_FOUND)

        res_other_view = self.client.get(f'/api/resources/attachments/{secret_att.id}/view/')
        self.assertEqual(res_other_view.status_code, status.HTTP_404_NOT_FOUND)

        res_other_preview = self.client.get(f'/api/resources/attachments/{secret_att.id}/preview/')
        self.assertEqual(res_other_preview.status_code, status.HTTP_404_NOT_FOUND)

        res_other_del = self.client.delete(f'/api/resources/attachments/{secret_att.id}/')
        self.assertEqual(res_other_del.status_code, status.HTTP_404_NOT_FOUND)

        # 3. Người tạo hợp pháp (self.user) có quyền truy cập và xóa
        self.client.force_authenticate(user=self.user)
        res_owner_detail = self.client.get(f'/api/resources/attachments/{secret_att.id}/')
        self.assertEqual(res_owner_detail.status_code, status.HTTP_200_OK)

        res_owner_del = self.client.delete(f'/api/resources/attachments/{secret_att.id}/')
        self.assertEqual(res_owner_del.status_code, status.HTTP_204_NO_CONTENT)
        secret_att.refresh_from_db()
        self.assertTrue(secret_att.is_deleted)

    def test_upload_zip_and_rar_with_temporary_file(self):
        """Kiểm tra đính kèm tệp zip/rar dạng TemporaryUploadedFile (BufferedRandom) không bị lỗi deepcopy/pickle."""
        from django.core.files.uploadedfile import TemporaryUploadedFile
        from django.http import QueryDict
        from document_templates.serializers import TaiLieuChiTietSerializer

        self.client.force_authenticate(user=self.user)
        # 1. Test qua APIClient với SimpleUploadedFile .zip và .rar
        zip_file = SimpleUploadedFile("archive.zip", b"PK\x03\x04test_content", content_type="application/zip")
        rar_file = SimpleUploadedFile("archive.rar", b"Rar!test_content", content_type="application/x-rar-compressed")
        res = self.client.patch(
            f'/api/resources/documents/{self.doc1.id}/',
            {'files': [zip_file, rar_file]},
            format='multipart'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        active_names = [a['name'] for a in res.data['attachments']]
        self.assertIn('archive.zip', active_names)
        self.assertIn('archive.rar', active_names)

        # 2. Test trực tiếp serializer với QueryDict immutable chứa TemporaryUploadedFile (tránh TypeError BufferedRandom)
        qd = QueryDict('tieu_de=TaiLieuTest&dm_tai_lieu=' + str(self.cat1.id) + '&ngay_dang=2026-10-30&ngay_het_hieu_luc=', mutable=True)
        tf = TemporaryUploadedFile('big_archive.zip', 'application/zip', 100, 'utf-8')
        tf.write(b'PK\x03\x04test')
        tf.seek(0)
        qd.setlist('files', [tf])
        qd._mutable = False  # Giả lập immutable QueryDict như trong production Django request

        serializer = TaiLieuChiTietSerializer(data=qd)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('ngay_het_hieu_luc'))


@override_settings(DOCUMENT_STORAGE_ROOT=TEMP_STORAGE_ROOT)
class DocumentTemplatesRBACPermissionsTests(TestCase):
    """Kiểm thử ma trận phân quyền RBAC (contract Issue #21) cho Tài liệu & Biểu mẫu"""

    def setUp(self):
        from django.contrib.auth.models import Permission
        self.client = APIClient()

        # 1. Plain user: không có bất kỳ quyền nào
        self.plain_user = User.objects.create_user(username="plain_user", password="password123")

        # 2. Creator user: có quyền add_tailieu
        self.creator_user = User.objects.create_user(username="creator_user", password="password123")
        perm_add, _ = Permission.objects.get_or_create(codename="add_tailieu", defaults={"name": "add_tailieu"})
        self.creator_user.user_permissions.add(perm_add)

        # 3. Editor user: có quyền change_tailieu
        self.editor_user = User.objects.create_user(username="editor_user", password="password123")
        perm_change, _ = Permission.objects.get_or_create(codename="change_tailieu", defaults={"name": "change_tailieu"})
        self.editor_user.user_permissions.add(perm_change)

        # 4. Deleter user: có quyền delete_tailieu
        self.deleter_user = User.objects.create_user(username="deleter_user", password="password123")
        perm_del, _ = Permission.objects.get_or_create(codename="delete_tailieu", defaults={"name": "delete_tailieu"})
        self.deleter_user.user_permissions.add(perm_del)

        # 5. Category manager: có quyền add_loaitailieubieumau, change_loaitailieubieumau, delete_loaitailieubieumau
        self.cat_user = User.objects.create_user(username="cat_user", password="password123")
        for c in ["add_loaitailieubieumau", "change_loaitailieubieumau", "delete_loaitailieubieumau"]:
            p, _ = Permission.objects.get_or_create(codename=c, defaults={"name": c})
            self.cat_user.user_permissions.add(p)

        # 6. Superuser
        self.superuser = User.objects.create_superuser(username="rbac_root", password="password123", email="root@example.com")

        # Dữ liệu ban đầu
        self.cat = DanhMucTaiLieu.objects.create(
            stt_uu_tien=1, ky_hieu="CAT-RBAC", ten_tai_lieu="Danh mục RBAC", nguoi_lap=self.superuser
        )
        self.type_item = LoaiTaiLieu.objects.create(
            dm_tai_lieu=self.cat, ten_loai="Loại RBAC", is_public=True
        )
        self.doc_by_creator = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat,
            ky_hieu="01/CREATOR",
            tieu_de="Tài liệu do creator tạo",
            ngay_dang=date(2026, 1, 1),
            hieu_luc="CON_HIEU_LUC",
            hien_thi="TAT_CA",
            file_dinh_kem=SimpleUploadedFile("doc1.pdf", b"%PDF content"),
            nguoi_tao=self.creator_user,
        )
        self.doc_by_admin = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat,
            ky_hieu="02/ADMIN",
            tieu_de="Tài liệu do admin tạo",
            ngay_dang=date(2026, 1, 2),
            hieu_luc="CON_HIEU_LUC",
            hien_thi="TAT_CA",
            file_dinh_kem=SimpleUploadedFile("doc2.pdf", b"%PDF content"),
            nguoi_tao=self.superuser,
        )

    def test_create_document_permission(self):
        """User thiếu add_tailieu nhận 403, có add_tailieu nhận 201"""
        payload = {
            'dm_tai_lieu': self.cat.id,
            'tieu_de': 'Tài liệu test quyền',
            'ngay_dang': '2026-03-01',
            'file_dinh_kem': SimpleUploadedFile("test.pdf", b"%PDF content", content_type="application/pdf"),
        }
        # 1. Plain user không có add_tailieu -> 403
        self.client.force_authenticate(user=self.plain_user)
        res_denied = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res_denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_denied.data.get('detail'), "roles.messages.permissionDenied")

        # 2. Creator user có add_tailieu -> 201
        self.client.force_authenticate(user=self.creator_user)
        payload['file_dinh_kem'] = SimpleUploadedFile("test2.pdf", b"%PDF content", content_type="application/pdf")
        res_ok = self.client.post('/api/resources/documents/', payload, format='multipart')
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_update_document_permission(self):
        """Creator sửa được tài liệu của mình; người khác phải có change_tailieu mới sửa được"""
        # 1. Plain user sửa doc của creator -> 403
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.patch(f'/api/resources/documents/{self.doc_by_creator.id}/', {'tieu_de': 'Sửa trái phép'})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Creator user sửa doc của chính mình -> 200
        self.client.force_authenticate(user=self.creator_user)
        res_self = self.client.patch(f'/api/resources/documents/{self.doc_by_creator.id}/', {'tieu_de': 'Creator tự sửa'})
        self.assertEqual(res_self.status_code, status.HTTP_200_OK)

        # 3. Creator user sửa doc của admin -> 403 (vì creator không có change_tailieu)
        res_other = self.client.patch(f'/api/resources/documents/{self.doc_by_admin.id}/', {'tieu_de': 'Sửa doc admin'})
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Editor user có change_tailieu sửa doc của người khác -> 200
        self.client.force_authenticate(user=self.editor_user)
        res_editor = self.client.patch(f'/api/resources/documents/{self.doc_by_creator.id}/', {'tieu_de': 'Editor sửa'})
        self.assertEqual(res_editor.status_code, status.HTTP_200_OK)

    def test_toggle_validity_permission(self):
        """Toggle validity yêu cầu change_tailieu hoặc chính là người tạo"""
        url_creator_doc = f'/api/resources/documents/{self.doc_by_creator.id}/toggle-validity/'
        url_admin_doc = f'/api/resources/documents/{self.doc_by_admin.id}/toggle-validity/'

        # Plain user -> 403
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.post(url_creator_doc, {})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Creator user toggle doc của mình -> 200
        self.client.force_authenticate(user=self.creator_user)
        res = self.client.post(url_creator_doc, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Creator user toggle doc của admin -> 403
        res = self.client.post(url_admin_doc, {})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_document_permission(self):
        """Creator xóa được doc của mình; xóa doc người khác cần delete_tailieu hoặc superuser"""
        # 1. Plain user xóa doc creator -> 403
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.delete(f'/api/resources/documents/{self.doc_by_creator.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Deleter user có delete_tailieu xóa doc admin -> 204
        self.client.force_authenticate(user=self.deleter_user)
        res = self.client.delete(f'/api/resources/documents/{self.doc_by_admin.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        # 3. Creator user xóa doc của chính mình -> 204
        self.client.force_authenticate(user=self.creator_user)
        res = self.client.delete(f'/api/resources/documents/{self.doc_by_creator.id}/')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_category_and_type_rbac_permissions(self):
        """Danh mục và Loại tài liệu: thêm, sửa, xóa yêu cầu quyền tương ứng"""
        # 1. Plain user thêm danh mục -> 403
        self.client.force_authenticate(user=self.plain_user)
        res_cat = self.client.post('/api/resources/categories/', {'ten_tai_lieu': 'DM Mới'})
        self.assertEqual(res_cat.status_code, status.HTTP_403_FORBIDDEN)

        res_type = self.client.post('/api/resources/types/', {'dm_tai_lieu': self.cat.id, 'ten_loai': 'Loại Mới'})
        self.assertEqual(res_type.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Cat user có quyền -> 201
        self.client.force_authenticate(user=self.cat_user)
        res_cat_ok = self.client.post('/api/resources/categories/', {'stt_uu_tien': 99, 'ten_tai_lieu': 'DM Mới Đạt'})
        self.assertEqual(res_cat_ok.status_code, status.HTTP_201_CREATED)
        new_cat_id = res_cat_ok.data['id']

        # Cat user sửa danh mục -> 200
        res_edit = self.client.patch(f'/api/resources/categories/{new_cat_id}/', {'ten_tai_lieu': 'DM Sửa'})
        self.assertEqual(res_edit.status_code, status.HTTP_200_OK)

        # Cat user xóa danh mục -> 204
        res_del = self.client.delete(f'/api/resources/categories/{new_cat_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

