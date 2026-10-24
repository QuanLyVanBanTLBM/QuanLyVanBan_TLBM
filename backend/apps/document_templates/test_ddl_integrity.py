"""Database contract tests for the document-template DDL references."""

from datetime import date

from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from accounts.models import Employee
from document_templates.models import (
    ChiTietTaiLieuAttachment,
    ChiTietTaiLieuLoaiTaiLieu,
    DanhMucTaiLieu,
    LoaiTaiLieu,
    TaiLieuChiTiet,
)
from organizations.models import DonVi


class DocumentTemplateDdlIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Employee.objects.create_user(username="template_ddl_integrity_user", password="pw")
        cls.unit = DonVi.objects.exclude(pk=cls.user.don_vi_id).order_by("id").first()
        if cls.unit is None:
            from organizations.models import KhoiKhuVuc
            khoi = KhoiKhuVuc.objects.first() or KhoiKhuVuc.objects.create(ten="Khối Mẫu")
            next_stt = (DonVi.objects.order_by("-stt_uu_tien").values_list("stt_uu_tien", flat=True).first() or 0) + 1
            cls.unit = DonVi.objects.create(khoi=khoi, stt_uu_tien=next_stt, ten="Đơn vị kiểm tra toàn vẹn")
        cls.category = DanhMucTaiLieu.objects.create(
            stt_uu_tien=0,
            ten_tai_lieu="Danh mục kiểm tra toàn vẹn",
            nguoi_lap=cls.user,
        )
        cls.subtype = LoaiTaiLieu.objects.create(
            dm_tai_lieu=cls.category,
            ten_loai="Loại tài liệu kiểm tra toàn vẹn",
        )
        cls.document = TaiLieuChiTiet.objects.create(
            dm_tai_lieu=cls.category,
            tieu_de="Tài liệu kiểm tra toàn vẹn",
            ngay_dang=date(2026, 1, 1),
            don_vi_id=cls.unit.pk,
            nguoi_tao=cls.user,
        )

    def test_through_table_has_physical_composite_primary_key(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT ARRAY(
                          SELECT att.attname
                          FROM unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord)
                          JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = key.attnum
                          ORDER BY key.ord
                      )
                   FROM pg_constraint con
                   WHERE con.conrelid = 'records_chitiettailieu_loaitailieu'::regclass
                     AND con.contype = 'p'"""
            )
            self.assertEqual(tuple(cursor.fetchone()[0]), ("chitiettailieu_id", "loaitailieu_id"))

    def test_orphan_unit_and_duplicate_through_pair_are_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TaiLieuChiTiet.objects.create(
                    dm_tai_lieu=self.category,
                    tieu_de="Đơn vị không tồn tại",
                    ngay_dang=date(2026, 1, 2),
                    don_vi_id=9223372036854770000,
                    nguoi_tao=self.user,
                )

        row = ChiTietTaiLieuLoaiTaiLieu.objects.create(
            chitiettailieu=self.document,
            loaitailieu=self.subtype,
        )
        self.assertEqual(row.pk, (self.document.pk, self.subtype.pk))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChiTietTaiLieuLoaiTaiLieu.objects.create(
                    chitiettailieu=self.document,
                    loaitailieu=self.subtype,
                )

    def test_detail_delete_cascades_to_links_and_attachments(self):
        ChiTietTaiLieuLoaiTaiLieu.objects.create(
            chitiettailieu=self.document,
            loaitailieu=self.subtype,
        )
        attachment = ChiTietTaiLieuAttachment.objects.create(
            document=self.document,
            name="phu-luc.pdf",
            path="phu-luc.pdf",
            nguoi_tao=self.user,
        )

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM records_chitiettailieu WHERE id = %s", [self.document.pk])

        self.assertFalse(
            ChiTietTaiLieuLoaiTaiLieu.objects.filter(chitiettailieu_id=self.document.pk).exists()
        )
        self.assertFalse(ChiTietTaiLieuAttachment.objects.filter(pk=attachment.pk).exists())

    def test_parent_category_delete_is_restricted_by_detail(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM records_tailieu WHERE id = %s", [self.category.pk])
