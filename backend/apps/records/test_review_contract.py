from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import Resolver404, resolve, reverse
from rest_framework.test import APITestCase
from records.models import HoSo, LoaiVanBan


class ReviewContractTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='review-reader', password='test-only')
        self.client.force_authenticate(self.user)
        self.dossier = HoSo.objects.create(so_ky_hieu='REVIEW', ten_ho_so='Review dossier', nguoi_lap=self.user)
        self.category = LoaiVanBan.objects.create(ho_so=self.dossier, ten_loai='Category A')
        self.url = reverse('records:document-type-catalog')

    def test_retired_metadata_route_has_no_resolver_even_for_catalog_reader(self):
        with self.assertRaises(Resolver404):
            resolve(f'/api/records/dossiers/{self.dossier.pk}/documents/')
        self.assertEqual(self.client.get(f'/api/records/dossiers/{self.dossier.pk}/documents/').status_code, 404)

    def test_catalog_without_permission_is_forbidden(self):
        with patch.object(type(self.user), 'has_perm', return_value=False):
            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_catalog_reader_receives_category_id_and_parent_without_document_metadata(self):
        with patch.object(type(self.user), 'has_perm', side_effect=lambda perm: perm == 'records.view_hoso'):
            response = self.client.get(self.url, {'ho_so': self.dossier.pk, 'search': 'Category'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        row = response.data['results'][0]
        self.assertEqual((row['id'], row['ho_so'], row['ten_ho_so']), (self.category.pk, self.dossier.pk, 'Review dossier'))
        self.assertNotIn('trich_yeu', row)
        self.assertNotIn('documents', row)

    def test_catalog_requires_authentication_and_valid_filter(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.client.force_authenticate(self.user)
        with patch.object(type(self.user), 'has_perm', return_value=True):
            for value in ('-1', '0', 'abc', '1 OR 1=1'):
                self.assertEqual(self.client.get(self.url, {'ho_so': value}).status_code, 400)
            self.assertEqual(self.client.get(self.url, {'year': 'not-a-year'}).status_code, 400)
            self.assertEqual(self.client.post(self.url, {}).status_code, 405)

    def test_fresh_migrations_have_exact_canonical_fk_indexes(self):
        for table, column, name in (('records_hoso', 'nguoi_lap_id', 'idx_hoso_nguoi_lap'), ('records_loaivanban', 'ho_so_id', 'idx_loaivanban_hoso')):
            with connection.cursor() as cursor:
                indexes = connection.introspection.get_constraints(cursor, table)
            matches = {key for key, info in indexes.items() if info.get('index') and not info.get('unique') and info.get('columns') == [column]}
            self.assertEqual(matches, {name})
