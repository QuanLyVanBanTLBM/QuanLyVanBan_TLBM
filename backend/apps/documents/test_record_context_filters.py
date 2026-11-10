"""Document-list handoff keeps exact category/dossier IDs and existing visibility rules."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from records.models import HoSo, LoaiVanBan
from documents.filters import VanBanDenFilter, VanBanDiFilter
from documents.models import (
    PhamVi, VanBanDen, VanBanDi,
    VanBanDenDanhmuc, VanBanDiDanhmuc, VanBanDenHoSo, VanBanDiHoSo,
)
from documents.selectors import van_ban_xem_duoc


class RecordContextFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="record_context_owner")
        cls.outsider = get_user_model().objects.create_user(username="record_context_outsider")
        cls.parent = HoSo.objects.create(so_ky_hieu="CONTEXT-A", ten_ho_so="Context parent", nguoi_lap=cls.owner)
        cls.other_parent = HoSo.objects.create(so_ky_hieu="CONTEXT-B", ten_ho_so="Other parent", nguoi_lap=cls.owner)
        cls.category = LoaiVanBan.objects.create(ho_so=cls.parent, ten_loai="Selected category")
        cls.other_category = LoaiVanBan.objects.create(ho_so=cls.parent, ten_loai="Other category")
        cls.outside_category = LoaiVanBan.objects.create(ho_so=cls.other_parent, ten_loai="Selected category")
        cls.models = [("DEN", VanBanDen, VanBanDenFilter, VanBanDenDanhmuc, VanBanDenHoSo, "vanbanden"),
                      ("DI", VanBanDi, VanBanDiFilter, VanBanDiDanhmuc, VanBanDiHoSo, "vanbandi")]
        cls.rows = {}
        for direction, model, _, category_link, dossier_link, relation in cls.models:
            rows = {}
            definitions = [
                ("selected", cls.category, cls.parent, PhamVi.NOI_BO, "Selected document", "DOC/SEL"),
                ("wrong_type", cls.other_category, cls.parent, PhamVi.NOI_BO, f"Content {cls.category.pk}", f"DOC/{cls.category.pk}/OTHER"),
                ("unlinked", None, cls.parent, PhamVi.NOI_BO, f"Content {cls.category.pk}", f"DOC/{cls.category.pk}/NONE"),
                ("other_parent", cls.outside_category, cls.other_parent, PhamVi.NOI_BO, "Outside dossier", "DOC/OTHER"),
                ("restricted", cls.category, cls.parent, PhamVi.HAN_CHE, "Restricted document", "DOC/RESTRICTED"),
                ("text_type", None, cls.parent, PhamVi.NOI_BO, "Thông báo nghiệp vụ", "DOC/TB"),
            ]
            for index, (key, category, parent, scope, summary, reference) in enumerate(definitions, 1):
                doc = model.objects.create(so_hieu=reference, so_thu_tu=index, nam=2026,
                    trich_yeu=summary, nguoi_tao=cls.owner, pham_vi=scope, hien_thi=True)
                dossier_link.objects.create(**{relation: doc, "hoso_id": parent.pk})
                if category:
                    category_link.objects.create(**{relation: doc, "loaivanban_id": category.pk})
                rows[key] = doc
            cls.rows[direction] = rows

    def test_numeric_category_does_not_match_summary_or_reference(self):
        for direction, model, filter_class, *_ in self.models:
            with self.subTest(direction=direction):
                filtered = filter_class({"loai_van_ban": str(self.category.pk)}, queryset=model.objects.all())
                self.assertTrue(filtered.is_valid(), filtered.errors)
                self.assertSetEqual(set(filtered.qs.values_list("pk", flat=True)), {
                    self.rows[direction][key].pk for key in ("selected", "restricted")
                })

    def test_numeric_dossier_does_not_match_summary_or_reference(self):
        for direction, model, filter_class, _, dossier_link, relation in self.models:
            with self.subTest(direction=direction):
                doc_with_other_pk_in_summary = model.objects.create(
                    so_hieu=f"DOC/TRICHYEU/{self.other_parent.pk}",
                    so_thu_tu=99,
                    nam=2026,
                    trich_yeu=f"Báo cáo tiến độ ngày {self.other_parent.pk}",
                    nguoi_tao=self.owner,
                    pham_vi=PhamVi.NOI_BO,
                    hien_thi=True,
                )
                dossier_link.objects.create(**{relation: doc_with_other_pk_in_summary, "hoso_id": self.parent.pk})

                filtered = filter_class({"ho_so": str(self.other_parent.pk)}, queryset=model.objects.all())
                self.assertTrue(filtered.is_valid(), filtered.errors)
                result_pks = set(filtered.qs.values_list("pk", flat=True))
                self.assertIn(self.rows[direction]["other_parent"].pk, result_pks)
                self.assertNotIn(doc_with_other_pk_in_summary.pk, result_pks)

    def test_mismatched_dossier_and_category_produce_no_results(self):
        for direction, model, filter_class, *_ in self.models:
            with self.subTest(direction=direction):
                query = {"ho_so": str(self.other_parent.pk), "loai_van_ban": str(self.category.pk)}
                self.assertFalse(filter_class(query, queryset=model.objects.all()).qs.exists())

    def test_unknown_category_does_not_fall_back_to_text(self):
        missing_id = LoaiVanBan.objects.order_by("-pk").first().pk + 1
        for direction, model, filter_class, *_ in self.models:
            with self.subTest(direction=direction):
                model.objects.filter(pk=self.rows[direction]["unlinked"].pk).update(trich_yeu=str(missing_id))
                self.assertFalse(filter_class({"loai_van_ban": str(missing_id)}, queryset=model.objects.all()).qs.exists())

    def test_text_search_still_supports_document_type_labels(self):
        for direction, model, filter_class, *_ in self.models:
            with self.subTest(direction=direction):
                result = filter_class({"loai_van_ban": "Thông báo"}, queryset=model.objects.all()).qs
                self.assertQuerySetEqual(result, [self.rows[direction]["text_type"]])

    def test_context_filters_intersect_with_existing_visibility(self):
        for direction, _, filter_class, *_ in self.models:
            for scope, expected in [(PhamVi.NOI_BO, "selected"), (PhamVi.HAN_CHE, "restricted")]:
                with self.subTest(direction=direction, scope=scope):
                    query = {"ho_so": str(self.parent.pk), "loai_van_ban": str(self.category.pk), "pham_vi": scope}
                    visible = van_ban_xem_duoc(self.owner, direction)
                    self.assertQuerySetEqual(filter_class(query, queryset=visible).qs, [self.rows[direction][expected]])
                    if scope == PhamVi.HAN_CHE:
                        stranger_visible = van_ban_xem_duoc(self.outsider, direction)
                        self.assertFalse(filter_class(query, queryset=stranger_visible).qs.exists())

    def test_api_count_and_pagination_match_selected_context(self):
        client = APIClient()
        client.force_authenticate(self.owner)
        for direction, *_ in self.models:
            for scope, expected in [(PhamVi.NOI_BO, "selected"), (PhamVi.HAN_CHE, "restricted")]:
                with self.subTest(direction=direction, scope=scope):
                    response = client.get("/api/documents/", {"loai": direction, "ho_so": self.parent.pk,
                        "loai_van_ban": self.category.pk, "pham_vi": scope, "page_size": 1})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data["count"], 1)
                    self.assertIsNone(response.data["next"])
                    self.assertEqual([item["id"] for item in response.data["results"]], [self.rows[direction][expected].pk])

    def test_api_filters_do_not_reveal_restricted_documents_to_other_users(self):
        client = APIClient()
        client.force_authenticate(self.outsider)
        for direction, *_ in self.models:
            with self.subTest(direction=direction):
                response = client.get("/api/documents/", {"loai": direction, "ho_so": self.parent.pk,
                    "loai_van_ban": self.category.pk, "pham_vi": PhamVi.HAN_CHE})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 0)
                self.assertEqual(response.data["results"], [])
