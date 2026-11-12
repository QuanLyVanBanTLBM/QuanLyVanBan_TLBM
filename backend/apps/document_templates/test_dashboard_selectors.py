from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Position
from document_templates.models import ChiTietTaiLieuAttachment, DanhMucTaiLieu, TaiLieuChiTiet
from document_templates.selectors import tai_lieu_hieu_luc_xem_duoc, visible_resources
from organizations.models import DonVi, KhoiKhuVuc


class TaiLieuHieuLucXemDuocTests(TestCase):
    def setUp(self):
        khoi = KhoiKhuVuc.objects.create(ten="Khối Hỗ trợ")
        latest = DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0
        don_vi = DonVi.objects.create(khoi=khoi, stt_uu_tien=latest + 1, ten="Phòng Hành chính")
        chuc_vu = Position.objects.create(display_order=Position.get_next_display_order(), name="Chuyên viên")
        users = get_user_model().objects
        self.user = users.create_user(username="selector_user", password="password123", don_vi=don_vi, chuc_vu=chuc_vu)
        self.other = users.create_user(username="selector_other", password="password123", don_vi=don_vi, chuc_vu=chuc_vu)
        self.category = DanhMucTaiLieu.objects.create(ten_tai_lieu="Mẫu", nguoi_lap=self.other)
        self.today = timezone.localdate()

    def _resource(self, code, creator, visibility="TAT_CA", validity="CON_HIEU_LUC"):
        return TaiLieuChiTiet.objects.create(
            dm_tai_lieu=self.category, ky_hieu=code, tieu_de=code, ngay_dang=self.today,
            hien_thi=visibility, nguoi_tao=creator, hieu_luc=validity,
        )

    def test_returns_valid_resources_within_visible_scope(self):
        public = self._resource("PUBLIC", self.other)
        own = self._resource("OWN", self.user, visibility="NOI_BO_PHONG_BAN")
        self._resource("PRIVATE", self.other, visibility="NOI_BO_PHONG_BAN")
        self._resource("EXPIRED", self.other, validity="HET_HIEU_LUC")

        codes = set(tai_lieu_hieu_luc_xem_duoc(self.user).values_list("ky_hieu", flat=True))
        self.assertEqual(codes, {public.ky_hieu, own.ky_hieu})
        visible = visible_resources(TaiLieuChiTiet.objects.all(), self.user).filter(hieu_luc="CON_HIEU_LUC")
        self.assertEqual(codes, set(visible.values_list("ky_hieu", flat=True)))

    def test_prefetches_active_attachments_in_id_order(self):
        resource = self._resource("DOC", self.other)
        first = ChiTietTaiLieuAttachment.objects.create(document=resource, name="a.xlsx", path="r/a.xlsx")
        ChiTietTaiLieuAttachment.objects.create(document=resource, name="deleted.pdf", path="r/d.pdf", is_deleted=True)
        second = ChiTietTaiLieuAttachment.objects.create(document=resource, name="b.pdf", path="r/b.pdf")

        row = tai_lieu_hieu_luc_xem_duoc(self.user).get(pk=resource.pk)
        self.assertEqual([att.pk for att in row.active_attachments], [first.pk, second.pk])

    def test_resource_without_attachments_has_empty_list(self):
        resource = self._resource("EMPTY", self.other)

        row = tai_lieu_hieu_luc_xem_duoc(self.user).get(pk=resource.pk)
        self.assertEqual(row.active_attachments, [])
