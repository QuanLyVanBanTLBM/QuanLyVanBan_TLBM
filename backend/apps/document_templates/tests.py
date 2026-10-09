import io
import openpyxl
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

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
        self.admin = User.objects.create_superuser(
            username='admin',
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
        doc = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.cat1,
            ky_hieu='05/HD-2026',
            tieu_de='Hướng dẫn nghiệp vụ một phần',
            ngay_dang=date(2026, 3, 1),
            hieu_luc='CON_HIEU_LUC_1_PHAN',
            don_vi_id=10,
            hien_thi='NOI_BO_PHONG_BAN',
            nguoi_tao=self.user,
        )
        self.assertEqual(doc.hieu_luc, 'CON_HIEU_LUC_1_PHAN')
        self.assertEqual(doc.don_vi_id, 10)

        # Kiểm tra qua API detail
        res = self.client.get(f'/api/resources/documents/{doc.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['hieu_luc'], 'CON_HIEU_LUC_1_PHAN')
        self.assertEqual(res.data['don_vi_id'], 10)

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


