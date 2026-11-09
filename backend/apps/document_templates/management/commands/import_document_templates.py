import os
import json
from datetime import date, datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings

from document_templates.models import (
    DanhMucTaiLieu,
    LoaiTaiLieu,
    TaiLieuChiTiet,
    ChiTietTaiLieuAttachment,
)


def parse_date(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Nạp dữ liệu Tài liệu & Biểu mẫu từ file JSON hoặc Excel (.xlsx)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/mau_tai_lieu_bieu_mau.json",
            help="Đường dẫn đến file .json hoặc .xlsx chứa dữ liệu mẫu",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Xóa toàn bộ dữ liệu tài liệu hiện tại trước khi nạp mới",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ kiểm tra tính hợp lệ của dữ liệu, không ghi vào database",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        is_clear = options["clear"]
        is_dry_run = options["dry_run"]

        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.BASE_DIR, "..", file_path)
            file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            raise CommandError(f"Không tìm thấy file tại đường dẫn: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".json", ".xlsx"]:
            raise CommandError(f"Định dạng file không hỗ trợ: {ext}. Chỉ hỗ trợ .json và .xlsx")

        self.stdout.write(self.style.NOTICE(f"==> Đang đọc dữ liệu từ: {file_path}"))

        if ext == ".json":
            categories_data, types_data, documents_data = self._read_json(file_path)
        else:
            categories_data, types_data, documents_data = self._read_excel(file_path)

        self.stdout.write(
            f"-> Đã đọc: {len(categories_data)} Danh mục, {len(types_data)} Loại tài liệu, {len(documents_data)} Tài liệu chi tiết"
        )

        User = get_user_model()
        admin_user = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(username="admin").first()
            or User.objects.first()
        )
        if not admin_user:
            admin_user = User.objects.create(
                username="admin",
                email="admin@baolong.vn",
                first_name="Quản trị",
                last_name="Hệ thống",
                is_staff=True,
                is_superuser=True,
            )

        with transaction.atomic():
            if is_clear and not is_dry_run:
                self.stdout.write(self.style.WARNING("-> Đang xóa sạch dữ liệu cũ..."))
                ChiTietTaiLieuAttachment.objects.all().delete()
                TaiLieuChiTiet.objects.all().delete()
                LoaiTaiLieu.objects.all().delete()
                DanhMucTaiLieu.objects.all().delete()

            # 1. Danh mục Cấp 1
            cat_map = {}
            for c in categories_data:
                cid = c.get("id")
                ten = c.get("ten_tai_lieu", "").strip()
                if not ten or ten.startswith("Nhập tên"):
                    continue

                defaults = {
                    "stt_uu_tien": c.get("stt_uu_tien") or cid or 1,
                    "ky_hieu": c.get("ky_hieu") or None,
                    "ten_tai_lieu": ten,
                    "ngay_lap": parse_date(c.get("ngay_lap")),
                    "ghi_chu": c.get("ghi_chu") or "",
                    "nguoi_lap": admin_user,
                }

                if not is_dry_run:
                    cat, _ = DanhMucTaiLieu.objects.update_or_create(id=cid, defaults=defaults)
                    cat_map[cid] = cat
                else:
                    cat_map[cid] = defaults

            # 2. Loại tài liệu Cấp 2
            type_map = {}
            for t in types_data:
                tid = t.get("id")
                dm_id = t.get("dm_id")
                ten_loai = t.get("ten_loai", "").strip()
                if not ten_loai or ten_loai.startswith("Nhập tên"):
                    continue

                if dm_id not in cat_map and not DanhMucTaiLieu.objects.filter(id=dm_id).exists():
                    self.stdout.write(
                        self.style.WARNING(f"Bỏ qua loại '{ten_loai}': không tìm thấy danh mục ID {dm_id}")
                    )
                    continue

                defaults = {
                    "ten_loai": ten_loai,
                    "is_public": bool(t.get("is_public", True)),
                    "ghi_chu": t.get("ghi_chu") or "",
                }

                if not is_dry_run:
                    dm_obj = cat_map.get(dm_id) or DanhMucTaiLieu.objects.get(id=dm_id)
                    defaults["dm_tai_lieu"] = dm_obj
                    loai, _ = LoaiTaiLieu.objects.update_or_create(id=tid, defaults=defaults)
                    type_map[tid] = loai
                else:
                    type_map[tid] = defaults

            # 3. Tài liệu chi tiết
            doc_count = 0
            for d in documents_data:
                did = d.get("id")
                dm_id = d.get("dm_id")
                tieu_de = d.get("tieu_de", "").strip()
                if not tieu_de or tieu_de.startswith("Nhập tiêu đề"):
                    continue

                if dm_id not in cat_map and not DanhMucTaiLieu.objects.filter(id=dm_id).exists():
                    self.stdout.write(
                        self.style.WARNING(f"Bỏ qua tài liệu '{tieu_de}': không tìm thấy danh mục ID {dm_id}")
                    )
                    continue

                hieu_luc = d.get("hieu_luc", "CON_HIEU_LUC")
                if hieu_luc not in dict(TaiLieuChiTiet.HIEU_LUC_CHOICES):
                    hieu_luc = "CON_HIEU_LUC"

                hien_thi = d.get("hien_thi", "TAT_CA")
                if hien_thi not in dict(TaiLieuChiTiet.HIEN_THI_CHOICES):
                    hien_thi = "TAT_CA"

                noi_ban_hanh = d.get("noi_ban_hanh") or None
                don_vi_id = d.get("don_vi_id")
                if not don_vi_id and noi_ban_hanh:
                    try:
                        from organizations.models import DonVi
                        u = DonVi.objects.filter(ten__iexact=str(noi_ban_hanh).strip()).first()
                        if u:
                            don_vi_id = u.id
                    except Exception:
                        pass

                defaults = {
                    "ky_hieu": d.get("ky_hieu") or None,
                    "tieu_de": tieu_de,
                    "ngay_dang": parse_date(d.get("ngay_dang")) or date.today(),
                    "noi_ban_hanh": noi_ban_hanh,
                    "don_vi_id": don_vi_id,
                    "hieu_luc": hieu_luc,
                    "ngay_het_hieu_luc": parse_date(d.get("ngay_het_hieu_luc")),
                    "link_thay_the": d.get("link_thay_the") or "",
                    "ghi_chu": d.get("ghi_chu") or "",
                    "hien_thi": hien_thi,
                    "nguoi_tao": admin_user,
                }

                if not is_dry_run:
                    dm_obj = cat_map.get(dm_id) or DanhMucTaiLieu.objects.get(id=dm_id)
                    defaults["dm_tai_lieu"] = dm_obj
                    doc, _ = TaiLieuChiTiet.objects.update_or_create(id=did, defaults=defaults)

                    # Many-to-many loai_tai_lieu
                    type_ids = d.get("loai_tai_lieu_ids", [])
                    matched_types = LoaiTaiLieu.objects.filter(id__in=type_ids)
                    doc.loai_tai_lieu.set(matched_types)

                    # Attachment
                    file_name = d.get("file_name", "").strip()
                    if file_name:
                        ChiTietTaiLieuAttachment.objects.update_or_create(
                            document=doc,
                            name=file_name,
                            defaults={
                                "path": f"document_templates/{file_name}",
                                "file_size": 1024,
                                "mime_type": "application/pdf" if file_name.lower().endswith(".pdf") else "application/octet-stream",
                                "nguoi_tao": admin_user,
                            },
                        )
                doc_count += 1

            if is_dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY-RUN] Dữ liệu hoàn toàn hợp lệ! Sẽ nạp: {len(cat_map)} Danh mục, {len(type_map)} Loại tài liệu, {doc_count} Tài liệu chi tiết."
                    )
                )
                transaction.set_rollback(True)
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"==> Nạp dữ liệu THÀNH CÔNG! Đã lưu: {len(cat_map)} Danh mục, {len(type_map)} Loại tài liệu, {doc_count} Tài liệu chi tiết."
                    )
                )

    def _read_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (
            data.get("danh_muc", []),
            data.get("loai_tai_lieu", []),
            data.get("tai_lieu_chi_tiet", []),
        )

    def _read_excel(self, path):
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=True)

        categories = []
        if "1_DanhMuc_Cap1" in wb.sheetnames:
            ws = wb["1_DanhMuc_Cap1"]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue
                try:
                    cid = int(row[0])
                except (ValueError, TypeError):
                    continue
                categories.append({
                    "id": cid,
                    "stt_uu_tien": int(row[1]) if row[1] is not None else cid,
                    "ky_hieu": str(row[2]).strip() if row[2] else "",
                    "ten_tai_lieu": str(row[3]).strip() if row[3] else "",
                    "ngay_lap": row[4],
                    "ghi_chu": str(row[5]).strip() if row[5] else "",
                })

        types = []
        if "2_LoaiTaiLieu_Cap2" in wb.sheetnames:
            ws = wb["2_LoaiTaiLieu_Cap2"]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue
                try:
                    tid = int(row[0])
                    dm_id = int(row[1])
                except (ValueError, TypeError):
                    continue
                is_pub = True
                if row[3] is not None:
                    val_pub = str(row[3]).strip().upper()
                    is_pub = val_pub in ["TRUE", "1", "CÓ", "YES"]
                types.append({
                    "id": tid,
                    "dm_id": dm_id,
                    "ten_loai": str(row[2]).strip() if row[2] else "",
                    "is_public": is_pub,
                    "ghi_chu": str(row[4]).strip() if row[4] else "",
                })

        documents = []
        if "3_ChiTietTaiLieu" in wb.sheetnames:
            ws = wb["3_ChiTietTaiLieu"]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or not row[0]:
                    continue
                try:
                    did = int(row[0])
                    dm_id = int(row[1])
                except (ValueError, TypeError):
                    continue

                type_ids = []
                if row[2]:
                    raw_types = str(row[2]).replace(";", ",").split(",")
                    for t in raw_types:
                        t = t.strip()
                        if t.isdigit():
                            type_ids.append(int(t))

                documents.append({
                    "id": did,
                    "dm_id": dm_id,
                    "loai_tai_lieu_ids": type_ids,
                    "ky_hieu": str(row[3]).strip() if row[3] else "",
                    "tieu_de": str(row[4]).strip() if row[4] else "",
                    "ngay_dang": row[5],
                    "noi_ban_hanh": str(row[6]).strip() if row[6] else "",
                    "hieu_luc": str(row[7]).strip() if row[7] else "CON_HIEU_LUC",
                    "ngay_het_hieu_luc": row[8],
                    "link_thay_the": str(row[9]).strip() if row[9] else "",
                    "hien_thi": str(row[10]).strip() if row[10] else "TAT_CA",
                    "ghi_chu": str(row[11]).strip() if row[11] else "",
                    "file_name": str(row[12]).strip() if row[12] else "",
                })

        return categories, types, documents
