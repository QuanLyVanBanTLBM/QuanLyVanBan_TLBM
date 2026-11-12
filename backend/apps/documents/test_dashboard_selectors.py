from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Position
from documents.models import PhamVi, VanBanDen, VanBanDenAttachment, VanBanDi, VanBanDiAttachment
from documents.selectors import tep_dinh_kem_hien_hanh
from organizations.models import DonVi, KhoiKhuVuc


class TepDinhKemHienHanhTests(TestCase):
    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối Hỗ trợ")
        latest = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest + 1, ten="Phòng Hành chính")
        chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Chuyên viên")
        self.user = get_user_model().objects.create_user(
            username="selector_user", password="password123", don_vi=don_vi, chuc_vu=chuc_vu
        )
        year = timezone.localdate().year
        self.incoming = [
            VanBanDen.objects.create(
                nam=year, so_thu_tu=i, so_hieu=f"DEN-{i}", trich_yeu="Đến", nguoi_tao=self.user,
                pham_vi=PhamVi.NOI_BO,
            )
            for i in (1, 2)
        ]
        self.outgoing = VanBanDi.objects.create(
            nam=year, so_thu_tu=1, so_hieu="DI-1", trich_yeu="Đi", nguoi_tao=self.user, pham_vi=PhamVi.NOI_BO,
        )

    def _at(self, day):
        return timezone.make_aware(datetime(2026, 1, day, 9))

    def test_orders_by_upload_time_then_id_and_skips_soft_deleted(self):
        doc = self.incoming[0]
        second = VanBanDenAttachment.objects.create(document=doc, name="b", path="b", created_at=self._at(2))
        first = VanBanDenAttachment.objects.create(document=doc, name="a", path="a", created_at=self._at(1))
        VanBanDenAttachment.objects.create(document=doc, name="c", path="c", created_at=self._at(3), is_deleted=True)
        tie = VanBanDenAttachment.objects.create(document=doc, name="d", path="d", created_at=self._at(2))

        rows = list(tep_dinh_kem_hien_hanh("DEN", [doc.pk]))
        self.assertEqual([row.pk for row in rows], [first.pk, second.pk, tie.pk])

    def test_limits_to_given_documents(self):
        wanted = VanBanDenAttachment.objects.create(document=self.incoming[0], name="x", path="x")
        VanBanDenAttachment.objects.create(document=self.incoming[1], name="y", path="y")

        self.assertEqual([row.pk for row in tep_dinh_kem_hien_hanh("DEN", [self.incoming[0].pk])], [wanted.pk])
        self.assertEqual(list(tep_dinh_kem_hien_hanh("DEN", [])), [])

    def test_selects_attachment_model_by_document_kind(self):
        VanBanDenAttachment.objects.create(document=self.incoming[0], name="den", path="den")
        outgoing_att = VanBanDiAttachment.objects.create(document=self.outgoing, name="di", path="di")

        self.assertEqual(
            [row.pk for row in tep_dinh_kem_hien_hanh("DI", [self.outgoing.pk])], [outgoing_att.pk]
        )
        self.assertEqual(list(tep_dinh_kem_hien_hanh("DEN", [self.outgoing.pk])), [])
