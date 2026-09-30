from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.records.models import Dossier, DocumentType

User = get_user_model()

class NhiTasksTestCase(TestCase):
    def setUp(self):
        # Tạo test data không dùng dữ liệu người thật
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Giả lập gán quyền view_hoso cho user (tùy theo logic phân quyền dự án)
        
        self.dossier_1 = Dossier.objects.create(
            code='HS01', name='Hồ sơ 1', created_by=self.user, is_system=False, sort_order=1
        )
        self.dossier_2 = Dossier.objects.create(
            code='HS02', name='Hồ sơ 2', created_by=self.user, is_system=False, sort_order=2
        )
        
        self.doc_type_1 = DocumentType.objects.create(
            dossier=self.dossier_1, name='Loại VB A', sort_order=1
        )
        self.doc_type_2 = DocumentType.objects.create(
            dossier=self.dossier_1, name='Loại VB B', sort_order=2
        )
        self.doc_type_3 = DocumentType.objects.create(
            dossier=self.dossier_2, name='Loại VB C', sort_order=1
        )

    def test_admin_model_creation(self):
        """Test việc khởi tạo Model hoạt động và lưu đúng các trường"""
        self.assertEqual(Dossier.objects.count(), 2)
        self.assertEqual(DocumentType.objects.count(), 3)
        self.assertEqual(self.doc_type_1.dossier, self.dossier_1)

    def test_api_get_document_types_scope_by_dossier(self):
        """Test GET Cấp 2 chỉ trả về đúng loại văn bản của hồ sơ được chọn (không N+1)"""
        # Giả định URL name cấu hình là 'document-type-list'
        url = reverse('document-type-list', kwargs={'dossier_id': self.dossier_1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Chỉ có 2 loại VB thuộc Hồ sơ 1
        self.assertEqual(len(response.data['results']), 2) 

    def test_api_get_document_types_search_case_insensitive(self):
        """Test search không phân biệt hoa thường"""
        url = reverse('document-type-list', kwargs={'dossier_id': self.dossier_1.id})
        response = self.client.get(url, {'search': 'loại vb a'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Loại VB A')

    def test_api_get_document_types_filter_year(self):
        """Test lọc năm theo ngày lập"""
        url = reverse('document-type-list', kwargs={'dossier_id': self.dossier_1.id})
        current_year = self.doc_type_1.created_at.year
        response = self.client.get(url, {'year': current_year})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        response_invalid_year = self.client.get(url, {'year': 1999})
        self.assertEqual(len(response_invalid_year.data['results']), 0)