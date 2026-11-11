"""
Services cho Module Văn Bản — Kiến trúc 2 Model (VanBanDen, VanBanDi).

Bao gồm:
1. Tự sinh số thứ tự (Số đến / Số đi) an toàn concurrency (select_for_update)
2. Tự động chuyển hết hiệu lực khi quá hạn (quét trên cả 2 model Đến & Đi)
3. Ghi log người xem (upsert vào documents_view_log theo document_type + document_id)
4. Sinh file Excel mẫu trực tiếp từ DB
5. Import dữ liệu từ Excel vào đúng model tương ứng
6. Export danh sách ra Excel theo bộ lọc
"""

import io
import math
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .models import (
    HieuLuc,
    LoaiVanBan,
    PhamVi,
    VanBanDen,
    VanBanDenAttachment,
    VanBanDi,
    VanBanDiAttachment,
    VanBanMat,
    VanBanMatAttachment,
    DocumentViewLog,
    get_document_model,
    canonical_document_kind,
)


# ═══════════════════════════════════════════════════════════════════
# 1. TỰ SINH SỐ THỨ TỰ — An toàn concurrency (select_for_update)
# ═══════════════════════════════════════════════════════════════════

def generate_so_thu_tu(loai: str, nam: int) -> int:
    """
    Sinh số thứ tự tự động tăng dần theo năm + loại văn bản.
    An toàn race-condition bằng select_for_update() trong transaction.

    - VB Đến: loai='DEN' → Số đến (1, 2, 3, ...)
    - VB Đi:  loai='DI'  → Số đi  (1, 2, 3, ...)
    """
    loai_str = str(loai).strip().upper()
    model = VanBanDi if loai_str in ("DI", "VANBANDI") else VanBanDen

    with transaction.atomic():
        last = (
            model.objects
            .select_for_update()
            .filter(nam=nam)
            .aggregate(max_so=models.Max("so_thu_tu"))
        )
        return (last["max_so"] or 0) + 1


# ═══════════════════════════════════════════════════════════════════
# 2. TỰ ĐỘNG CHUYỂN HẾT HIỆU LỰC KHI QUÁ HẠN
# ═══════════════════════════════════════════════════════════════════

def check_and_update_expired_documents() -> int:
    """
    Quét và tự động chuyển trạng thái các văn bản đã tới hoặc quá ngày hết hiệu lực
    sang 'HET_HIEU_LUC' trên cả 3 model: Đến, Đi và Mật.
    Áp dụng cho cả CON_HIEU_LUC và CON_HIEU_LUC_1_PHAN.
    """
    now = timezone.now()
    active_statuses = [HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN]

    count_den = VanBanDen.objects.filter(
        hieu_luc__in=active_statuses,
        ngay_het_hieu_luc__isnull=False,
        ngay_het_hieu_luc__lte=now,
    ).update(hieu_luc=HieuLuc.HET_HIEU_LUC)

    count_di = VanBanDi.objects.filter(
        hieu_luc__in=active_statuses,
        ngay_het_hieu_luc__isnull=False,
        ngay_het_hieu_luc__lte=now,
    ).update(hieu_luc=HieuLuc.HET_HIEU_LUC)

    count_mat = VanBanMat.objects.filter(
        hieu_luc__in=active_statuses,
        ngay_het_hieu_luc__isnull=False,
        ngay_het_hieu_luc__lte=now,
    ).update(hieu_luc=HieuLuc.HET_HIEU_LUC)

    return count_den + count_di + count_mat


# ═══════════════════════════════════════════════════════════════════
# 2.1 TRUY VẤN ĐỘNG VÀ ĐỒNG BỘ QUAN HỆ THAY THẾ (Replacements)
# ═══════════════════════════════════════════════════════════════════

def parse_replacement_target(target_str: str) -> dict:
    """
    Phân tích chuỗi mục tiêu thay thế thành các thành phần định danh:
    - base_so_hieu: Số hiệu văn bản gốc (ví dụ: '1' hoặc '125/CV-NEW')
    - so_thu_tu: Số thứ tự trong năm (nếu có, ví dụ: 16)
    - extra_info: Thông tin bổ sung (nơi ban hành / người ký)
    - raw: Chuỗi gốc
    """
    raw = (target_str or "").strip()
    if not raw:
        return {"base_so_hieu": "", "so_thu_tu": None, "extra_info": "", "raw": ""}

    match = re.match(r"^(.+?)\s*(?:\[|\()([^\]\)]+)(?:\]|\))$", raw)
    if match:
        base_so = match.group(1).strip()
        bracket_content = match.group(2).strip()
        stt_match = re.search(r"#(\d+)", bracket_content)
        if not stt_match:
            stt_match = re.search(r"(?:Số đến|Số đi|STT)\s*[:#]?\s*(\d+)", bracket_content, re.IGNORECASE)
        stt = int(stt_match.group(1)) if stt_match else None
        extra = bracket_content
        if stt_match:
            extra = re.sub(r"(?:Số đến|Số đi|STT)\s*[:#]?\s*\d+", "", extra, flags=re.IGNORECASE)
            extra = re.sub(r"#\d+", "", extra)
            extra = re.sub(r"Nơi ban hành\s*:\s*", "", extra, flags=re.IGNORECASE)
            extra = re.sub(r"Người ký\s*:\s*", "", extra, flags=re.IGNORECASE)
            extra = extra.strip(" -:;,[]()")
        return {
            "base_so_hieu": base_so,
            "so_thu_tu": stt,
            "extra_info": extra,
            "raw": raw,
        }

    return {
        "base_so_hieu": raw,
        "so_thu_tu": None,
        "extra_info": "",
        "raw": raw,
    }


def _model_has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def find_replacement_target_document(target_str: str, current_doc=None, target_model=None, current_pham_vi=None):
    """
    Truy vấn chính xác văn bản mục tiêu thay thế theo bộ ba định danh:
    (so_hieu, so_thu_tu, noi_ban_hanh/nguoi_ky) kết hợp phạm vi (NOI_BO/HAN_CHE) và phân hệ (DEN/DI).
    """
    parsed = parse_replacement_target(target_str)
    base_so = parsed["base_so_hieu"]
    target_stt = parsed["so_thu_tu"]
    extra = parsed["extra_info"]
    if not base_so:
        return None

    from .models import VanBanDen, VanBanDi, VanBanMat

    models_to_check = [target_model] if target_model else (
        [current_doc.__class__] if current_doc else [VanBanDen, VanBanDi, VanBanMat]
    )

    for model in models_to_check:
        if not model:
            continue
        qs = model.objects.filter(so_hieu__iexact=base_so)
        if current_doc and getattr(current_doc, "pk", None):
            qs = qs.exclude(pk=current_doc.pk)

        # 1. Khóa theo phạm vi (NOI_BO / HAN_CHE)
        scope = current_pham_vi or (getattr(current_doc, "pham_vi", None) if current_doc else None)
        scoped_qs = qs.filter(pham_vi=scope) if scope else qs

        # 2. Khóa chính xác theo số thứ tự (Số đến / Số đi trong năm)
        if target_stt is not None:
            match_stt = scoped_qs.filter(so_thu_tu=target_stt).first()
            if match_stt:
                return match_stt
            match_stt_fallback = qs.filter(so_thu_tu=target_stt).first()
            if match_stt_fallback:
                return match_stt_fallback

        # 3. Khớp theo nơi ban hành hoặc người ký nếu có (chỉ filter nếu là database field thực tế)
        if extra:
            if _model_has_field(model, "noi_ban_hanh"):
                match_extra = scoped_qs.filter(noi_ban_hanh__icontains=extra).first()
                if match_extra:
                    return match_extra
            if _model_has_field(model, "nguoi_ky"):
                match_extra = scoped_qs.filter(nguoi_ky__icontains=extra).first()
                if match_extra:
                    return match_extra

        # 4. Nếu không có định danh phụ, ưu tiên bản ghi trong cùng phạm vi
        match_scope = scoped_qs.first()
        if match_scope:
            return match_scope

        # 5. Fallback nếu không có trong scope
        fallback_match = qs.first()
        if fallback_match:
            return fallback_match

    return None


def get_replacement_relations(doc) -> dict:
    """
    Phân định rõ ràng 2 chiều quan hệ thay thế:
    - thay_the_cho (list[str]): Các số hiệu văn bản cũ mà doc đi thay thế (Active replaces).
    - bi_thay_boi (list[str]): Các số hiệu văn bản mới đã thay thế doc (Superseded by).
    """
    if isinstance(doc, str):
        so_hieu = doc.strip()
        doc_obj = None
    else:
        so_hieu = (getattr(doc, "so_hieu", "") or "").strip()
        doc_obj = doc

    so_hieu_clean = so_hieu.lower()
    thay_the_cho: list[str] = []
    bi_thay_boi: list[str] = []

    if not so_hieu:
        return {"thay_the_cho": [], "bi_thay_boi": []}

    from .models import VanBanDen, VanBanDi, VanBanMat, HieuLuc
    doc_date = (
        getattr(doc_obj, "ngay_van_ban", None)
        or getattr(doc_obj, "ngay_den", None)
        or getattr(doc_obj, "ngay_ban_hanh", None)
    ) if doc_obj else None

    # Chiều 1: doc.link_thay_the chứa các số hiệu mục tiêu
    own_link = (getattr(doc_obj, "link_thay_the", "") or "").strip() if doc_obj else ""
    target_raws = [s.strip() for s in own_link.split(",") if s.strip()]

    # Chiều 2: Các văn bản khác có link_thay_the chứa so_hieu của doc
    referencing_docs = []
    for model in (VanBanDen, VanBanDi, VanBanMat):
        try:
            qs = model.objects.filter(link_thay_the__icontains=so_hieu)
            if doc_obj and getattr(doc_obj, "pk", None):
                qs = qs.exclude(pk=doc_obj.pk)
            for other in qs:
                other_targets = [t.strip() for t in (other.link_thay_the or "").split(",") if t.strip()]
                for ot in other_targets:
                    p = parse_replacement_target(ot)
                    if p["base_so_hieu"].lower() == so_hieu_clean:
                        is_match = True
                        if p["so_thu_tu"] is not None and getattr(doc_obj, "so_thu_tu", None) is not None:
                            is_match = (doc_obj.so_thu_tu == p["so_thu_tu"])
                        elif p["extra_info"] and hasattr(doc_obj, "noi_ban_hanh") and getattr(doc_obj, "noi_ban_hanh", None):
                            is_match = (p["extra_info"].lower() in doc_obj.noi_ban_hanh.lower())
                        
                        if is_match and other not in referencing_docs:
                            referencing_docs.append(other)
        except Exception:
            pass

    def to_date_norm(d):
        if not d:
            return None
        return d.date() if hasattr(d, "date") and callable(d.date) else d

    norm_doc_date = to_date_norm(doc_date)

    # Phân loại theo bản chất quan hệ, thời gian và trạng thái hiệu lực
    for raw_target in target_raws:
        parsed_target = parse_replacement_target(raw_target)
        target_obj = find_replacement_target_document(raw_target, current_doc=doc_obj)
        if not target_obj:
            continue
        if doc_obj and getattr(doc_obj, "pk", None) and target_obj.pk == doc_obj.pk:
            continue

        if target_obj:
            target_date = (
                getattr(target_obj, "ngay_van_ban", None)
                or getattr(target_obj, "ngay_den", None)
                or getattr(target_obj, "ngay_ban_hanh", None)
            )
            norm_target_date = to_date_norm(target_date)
            if getattr(doc_obj, "hieu_luc", "") in (HieuLuc.HET_VA_THAY_THE, HieuLuc.HET_HIEU_LUC):
                if target_obj.so_hieu not in bi_thay_boi:
                    bi_thay_boi.append(target_obj.so_hieu)
            elif getattr(doc_obj, "hieu_luc", "") == HieuLuc.CON_HIEU_LUC_1_PHAN and (
                (target_obj.hieu_luc == HieuLuc.CON_HIEU_LUC and any(parse_replacement_target(s)["base_so_hieu"].lower() == so_hieu_clean for s in (target_obj.link_thay_the or "").split(",") if s.strip()))
                or (norm_doc_date and norm_target_date and norm_target_date > norm_doc_date)
            ):
                if target_obj.so_hieu not in bi_thay_boi:
                    bi_thay_boi.append(target_obj.so_hieu)
            elif target_obj.hieu_luc == HieuLuc.HET_VA_THAY_THE and (not norm_doc_date or not norm_target_date or norm_target_date <= norm_doc_date):
                if target_obj.so_hieu not in thay_the_cho:
                    thay_the_cho.append(target_obj.so_hieu)
            elif getattr(doc_obj, "hieu_luc", "") in (HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN):
                if target_obj.so_hieu not in thay_the_cho:
                    thay_the_cho.append(target_obj.so_hieu)
            else:
                if target_obj.so_hieu not in bi_thay_boi:
                    bi_thay_boi.append(target_obj.so_hieu)

    for ref_doc in referencing_docs:
        ref_so = ref_doc.so_hieu
        ref_date = (
            getattr(ref_doc, "ngay_van_ban", None)
            or getattr(ref_doc, "ngay_den", None)
            or getattr(ref_doc, "ngay_ban_hanh", None)
        )
        norm_ref_date = to_date_norm(ref_date)
        if ref_doc.hieu_luc in (HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN) or (norm_doc_date and norm_ref_date and norm_ref_date > norm_doc_date):
            if ref_so not in bi_thay_boi and ref_so not in thay_the_cho:
                bi_thay_boi.append(ref_so)
        elif ref_doc.hieu_luc == HieuLuc.HET_VA_THAY_THE and (not norm_doc_date or not norm_ref_date or norm_ref_date <= norm_doc_date):
            if ref_so not in thay_the_cho and ref_so not in bi_thay_boi:
                thay_the_cho.append(ref_so)
        elif getattr(doc_obj, "hieu_luc", "") == HieuLuc.HET_VA_THAY_THE:
            if ref_so not in bi_thay_boi and ref_so not in thay_the_cho:
                bi_thay_boi.append(ref_so)
        else:
            if ref_so not in thay_the_cho and ref_so not in bi_thay_boi:
                thay_the_cho.append(ref_so)

    return {
        "thay_the_cho": thay_the_cho,
        "bi_thay_boi": bi_thay_boi,
    }


def get_dynamic_replacements(doc) -> list[str]:
    """
    Truy vấn động quan hệ thay thế tổng hợp (hợp nhất thay_the_cho và bi_thay_boi).
    Đảm bảo tương thích ngược 100% cho mọi serializer và component.
    """
    rels = get_replacement_relations(doc)
    results: list[str] = []
    for item in rels.get("thay_the_cho", []) + rels.get("bi_thay_boi", []):
        if item not in results:
            results.append(item)
    return results


def sync_replacement_document(doc):
    """Đồng bộ quan hệ thay thế 2 chiều giữa các văn bản (hỗ trợ nhiều văn bản phân tách bằng dấu phẩy)."""
    raw_target = (getattr(doc, "link_thay_the", "") or "").strip()
    if not raw_target:
        return

    targets = [t.strip() for t in raw_target.split(",") if t.strip()]
    from .models import VanBanDen, VanBanDi, VanBanMat, HieuLuc

    for target in targets:
        other_doc = find_replacement_target_document(
            target,
            current_doc=doc,
            target_model=doc.__class__,
            current_pham_vi=getattr(doc, "pham_vi", None),
        )
        if not other_doc:
            continue

        existing_links = [s.strip() for s in (other_doc.link_thay_the or "").split(",") if s.strip()]
        doc_so = (doc.so_hieu or "").strip()

        def is_already_linked(link: str) -> bool:
            p = parse_replacement_target(link)
            if p["base_so_hieu"].lower() != doc_so.lower():
                return False
            if p["so_thu_tu"] is not None and getattr(doc, "so_thu_tu", None) is not None:
                return p["so_thu_tu"] == doc.so_thu_tu
            if p["extra_info"]:
                doc_extra = getattr(doc, "noi_ban_hanh", None) or getattr(doc, "nguoi_ky", None) or ""
                return p["extra_info"].lower() in str(doc_extra).lower()
            return True

        already_linked = any(is_already_linked(link) for link in existing_links)
        if doc_so and not already_linked:
            # Tạo định danh phân biệt chiều ngược lại
            if hasattr(doc, "noi_ban_hanh") and getattr(doc, "noi_ban_hanh", None) and getattr(doc, "so_thu_tu", None):
                back_link = f"{doc_so} [Nơi ban hành: {doc.noi_ban_hanh} - Số đến #{doc.so_thu_tu}]"
            elif hasattr(doc, "nguoi_ky") and getattr(doc, "nguoi_ky", None) and getattr(doc, "so_thu_tu", None):
                back_link = f"{doc_so} [Người ký: {doc.nguoi_ky} - Số đi #{doc.so_thu_tu}]"
            else:
                back_link = doc_so
            existing_links.append(back_link)
        other_doc.link_thay_the = ", ".join(existing_links)

        # Trạng thái hiệu lực (Phương án A):
        # Khi văn bản A thay thế cho B, nếu B đang Còn hiệu lực (CON_HIEU_LUC),
        # tự động chuyển B sang trạng thái Còn hiệu lực 1 phần (CON_HIEU_LUC_1_PHAN).
        # Nếu B đã là Còn hiệu lực 1 phần hoặc Hết hiệu lực, bảo lưu trạng thái hiện tại.
        if getattr(doc, "hieu_luc", "") in (HieuLuc.CON_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN):
            if other_doc.hieu_luc == HieuLuc.CON_HIEU_LUC:
                other_doc.hieu_luc = HieuLuc.CON_HIEU_LUC_1_PHAN
                other_doc.save(update_fields=["hieu_luc", "link_thay_the"])
            else:
                other_doc.save(update_fields=["link_thay_the"])
        else:
            other_doc.save(update_fields=["link_thay_the"])


def cleanup_old_replacement_link(old_target_so_hieu, current_so_hieu, new_target_so_hieu=None):
    """Dọn dẹp quan hệ thay thế cũ khi văn bản sửa đổi/xóa link_thay_the."""
    if not old_target_so_hieu:
        return

    from .models import VanBanDen, VanBanDi, VanBanMat, HieuLuc

    old_list = [s.strip() for s in str(old_target_so_hieu).split(",") if s.strip()]
    new_list = [s.strip() for s in str(new_target_so_hieu or "").split(",") if s.strip()]

    # Những mục tiêu thực sự bị gỡ bỏ khỏi link_thay_the
    if new_list:
        removed_targets = [
            ot for ot in old_list
            if not any(
                parse_replacement_target(ot)["base_so_hieu"].lower() == parse_replacement_target(nt)["base_so_hieu"].lower()
                and (
                    parse_replacement_target(ot)["so_thu_tu"] is None
                    or parse_replacement_target(nt)["so_thu_tu"] is None
                    or parse_replacement_target(ot)["so_thu_tu"] == parse_replacement_target(nt)["so_thu_tu"]
                )
                for nt in new_list
            )
        ]
    else:
        removed_targets = old_list

    for old_target in removed_targets:
        parsed = parse_replacement_target(old_target)
        target_doc = find_replacement_target_document(old_target)
        docs_to_clean = [target_doc] if target_doc else []

        if not docs_to_clean:
            for model in (VanBanDen, VanBanDi, VanBanMat):
                docs_to_clean.extend(list(model.objects.filter(so_hieu__iexact=parsed["base_so_hieu"])))

        for doc in docs_to_clean:
            updated_fields = []
            if current_so_hieu and doc.link_thay_the:
                cur_so_clean = str(current_so_hieu).strip().lower()
                links = [l.strip() for l in doc.link_thay_the.split(",") if l.strip()]
                remaining_links = [
                    l for l in links
                    if parse_replacement_target(l)["base_so_hieu"].lower() != cur_so_clean
                ]
                new_link_str = ", ".join(remaining_links)
                if new_link_str != doc.link_thay_the:
                    doc.link_thay_the = new_link_str
                    updated_fields.append("link_thay_the")

            if doc.hieu_luc in (HieuLuc.HET_VA_THAY_THE, HieuLuc.HET_HIEU_LUC, HieuLuc.CON_HIEU_LUC_1_PHAN):
                doc.hieu_luc = HieuLuc.CON_HIEU_LUC
                doc.ngay_het_hieu_luc = None
                if "ngay_het_hieu_luc" not in updated_fields:
                    updated_fields.append("ngay_het_hieu_luc")
                if "hieu_luc" not in updated_fields:
                    updated_fields.append("hieu_luc")

            if updated_fields:
                doc.save(update_fields=updated_fields)


def cleanup_replacement_links_on_delete(instance_or_so_hieu):
    """Dọn dẹp và khôi phục văn bản liên quan khi một văn bản bị xóa."""
    if isinstance(instance_or_so_hieu, str):
        so_hieu = instance_or_so_hieu.strip()
        link_target = ""
    else:
        so_hieu = (getattr(instance_or_so_hieu, "so_hieu", "") or "").strip()
        link_target = (getattr(instance_or_so_hieu, "link_thay_the", "") or "").strip()
    if not so_hieu and not link_target:
        return

    from .models import VanBanDen, VanBanDi, VanBanMat, HieuLuc
    from django.db.models import Q
    query = Q()
    if so_hieu:
        query |= Q(link_thay_the__icontains=so_hieu)
    if link_target:
        for t in link_target.split(","):
            p = parse_replacement_target(t)
            if p["base_so_hieu"]:
                query |= Q(so_hieu__iexact=p["base_so_hieu"])

    exclude_pk = getattr(instance_or_so_hieu, "pk", None)
    for model in (VanBanDen, VanBanDi, VanBanMat):
        qs = model.objects.filter(query)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        for doc in qs:
            updated_fields = []
            if so_hieu and doc.link_thay_the and so_hieu.lower() in doc.link_thay_the.lower():
                links = [l.strip() for l in doc.link_thay_the.split(",") if l.strip()]
                remaining_links = [
                    l for l in links
                    if parse_replacement_target(l)["base_so_hieu"].lower() != so_hieu.lower()
                ]
                new_str = ", ".join(remaining_links)
                if new_str != doc.link_thay_the:
                    doc.link_thay_the = new_str
                    updated_fields.append("link_thay_the")

                # Chỉ khôi phục trạng thái nếu không còn văn bản nào khác thay thế
                if not remaining_links:
                    now = timezone.now()
                    is_date_expired = bool(doc.ngay_het_hieu_luc and doc.ngay_het_hieu_luc <= now)
                    if is_date_expired:
                        if doc.hieu_luc == HieuLuc.HET_VA_THAY_THE:
                            doc.hieu_luc = HieuLuc.HET_HIEU_LUC
                            if "hieu_luc" not in updated_fields:
                                updated_fields.append("hieu_luc")
                    else:
                        if doc.hieu_luc in (HieuLuc.HET_VA_THAY_THE, HieuLuc.CON_HIEU_LUC_1_PHAN):
                            doc.hieu_luc = HieuLuc.CON_HIEU_LUC
                            if "hieu_luc" not in updated_fields:
                                updated_fields.append("hieu_luc")

            if updated_fields:
                doc.save(update_fields=updated_fields)


# ═══════════════════════════════════════════════════════════════════
# 2.2 QUERYSET DÙNG CHUNG / KIỂM QUYỀN TRUY CẬP (Mục B4 & B5 Issue #53)
# ═══════════════════════════════════════════════════════════════════

def get_accessible_documents(user, doc_type: str = "vanbanden", strict_need_to_know: bool = False):
    """
    QuerySet chuẩn hoá dùng chung cho:
    - Module Văn Bản (Nhóm 2)
    - Dashboard / KPI (Nhóm 1)
    - Trợ lý AI (Nhóm 8)

    Đồng bộ 100% với selectors.van_ban_xem_duoc theo Issue #82 & Issue #83.
    """
    from .selectors import van_ban_xem_duoc
    return van_ban_xem_duoc(user, doc_type)


# ═══════════════════════════════════════════════════════════════════
# 3. GHI LOG NGƯỜI XEM — Upsert vào documents_view_log
# ═══════════════════════════════════════════════════════════════════

def log_document_view(document, user, doc_type=None):
    """
    Ghi nhận người dùng đã xem văn bản.
    Khớp với bảng `documents_view_log` (document_type, document_id, user_id).
    """
    if not user or not user.is_authenticated:
        return

    if not doc_type:
        doc_type = getattr(document, "document_kind", None)
        if not doc_type:
            loai = getattr(document, "loai", "DEN")
            if loai == "MAT":
                doc_type = "vanbanmat"
            elif loai == "DI":
                doc_type = "vanbandi"
            else:
                doc_type = "vanbanden"

    doc_id = document.pk if hasattr(document, "pk") else document.id
    doc_type = canonical_document_kind(doc_type)

    DocumentViewLog.objects.update_or_create(
        document_type=doc_type,
        document_id=doc_id,
        user=user,
        defaults={"viewed_at": timezone.now()},
    )


# ═══════════════════════════════════════════════════════════════════
# 4. EXCEL — Cấu hình & Sinh file mẫu
# ═══════════════════════════════════════════════════════════════════

EXCEL_COLUMNS = {
    (LoaiVanBan.DEN, PhamVi.NOI_BO): [
        ("nam", "Năm", 10),
        ("so_hieu", "Số, ký hiệu VB", 24),
        ("pham_vi", "Phạm vi", 16),
        ("ngay_den", "Ngày đến", 18),
        ("ngay_van_ban", "Ngày văn bản", 18),
        ("trich_yeu", "Trích yếu nội dung", 65),
        ("danh_muc_ho_so", "Danh mục hồ sơ (Số ký hiệu)", 32),
        ("ten_loai_van_ban", "Loại văn bản", 26),
        ("noi_ban_hanh", "Nơi ban hành", 32),
        ("don_vi_nhan", "Đơn vị nhận / chủ trì", 30),
        ("nguoi_nhan", "Cán bộ nhận / xử lý", 30),
        ("nguoi_ky", "Người ký", 22),
        ("chuc_vu", "Chức vụ", 20),
        ("hieu_luc", "Hiệu lực", 20),
        ("ngay_het_hieu_luc", "Ngày hết hiệu lực", 20),
        ("tep_dinh_kem", "Tệp đính kèm", 32),
        ("link_thay_the", "Link văn bản thay thế", 28),
        ("ghi_chu", "Ghi chú", 36),
    ],
    (LoaiVanBan.DEN, PhamVi.HAN_CHE): [
        ("nam", "Năm", 10),
        ("so_hieu", "Số, ký hiệu VB", 24),
        ("pham_vi", "Phạm vi", 16),
        ("ngay_den", "Ngày đến", 18),
        ("ngay_van_ban", "Ngày văn bản", 18),
        ("trich_yeu", "Trích yếu nội dung", 65),
        ("danh_muc_ho_so", "Danh mục hồ sơ (Số ký hiệu)", 32),
        ("ten_loai_van_ban", "Loại văn bản", 26),
        ("noi_ban_hanh", "Nơi ban hành", 32),
        ("don_vi_nhan", "Đơn vị nhận / chủ trì", 30),
        ("nguoi_nhan", "Cán bộ nhận / xử lý", 30),
        ("nguoi_ky", "Người ký", 22),
        ("chuc_vu", "Chức vụ", 20),
        ("hieu_luc", "Hiệu lực", 20),
        ("ngay_het_hieu_luc", "Ngày hết hiệu lực", 20),
        ("tep_dinh_kem", "Tệp đính kèm", 32),
        ("link_thay_the", "Link văn bản thay thế", 28),
        ("ghi_chu", "Ghi chú", 36),
    ],
    (LoaiVanBan.DI, PhamVi.NOI_BO): [
        ("nam", "Năm", 10),
        ("so_hieu", "Số, ký hiệu VB", 24),
        ("pham_vi", "Phạm vi", 16),
        ("ngay_ban_hanh", "Ngày ban hành", 18),
        ("ngay_van_ban", "Ngày văn bản", 18),
        ("trich_yeu", "Trích yếu nội dung", 65),
        ("danh_muc_ho_so", "Danh mục hồ sơ (Số ký hiệu)", 32),
        ("ten_loai_van_ban", "Loại văn bản", 26),
        ("noi_ban_hanh", "Nơi ban hành", 32),
        ("don_vi_nhan", "Đơn vị nhận / chủ trì", 30),
        ("nguoi_nhan", "Cán bộ nhận / xử lý", 30),
        ("nguoi_ky", "Người ký", 22),
        ("chuc_vu", "Chức vụ", 20),
        ("hieu_luc", "Hiệu lực", 20),
        ("ngay_het_hieu_luc", "Ngày hết hiệu lực", 20),
        ("tep_dinh_kem", "Tệp đính kèm", 32),
        ("link_thay_the", "Link văn bản thay thế", 28),
        ("ghi_chu", "Ghi chú", 36),
    ],
    (LoaiVanBan.DI, PhamVi.HAN_CHE): [
        ("nam", "Năm", 10),
        ("so_hieu", "Số, ký hiệu VB", 24),
        ("pham_vi", "Phạm vi", 16),
        ("ngay_ban_hanh", "Ngày ban hành", 18),
        ("ngay_van_ban", "Ngày văn bản", 18),
        ("trich_yeu", "Trích yếu nội dung", 65),
        ("danh_muc_ho_so", "Danh mục hồ sơ (Số ký hiệu)", 32),
        ("ten_loai_van_ban", "Loại văn bản", 26),
        ("noi_ban_hanh", "Nơi ban hành", 32),
        ("don_vi_nhan", "Đơn vị nhận / chủ trì", 30),
        ("nguoi_nhan", "Cán bộ nhận / xử lý", 30),
        ("nguoi_ky", "Người ký", 22),
        ("chuc_vu", "Chức vụ", 20),
        ("hieu_luc", "Hiệu lực", 20),
        ("ngay_het_hieu_luc", "Ngày hết hiệu lực", 20),
        ("tep_dinh_kem", "Tệp đính kèm", 32),
        ("link_thay_the", "Link văn bản thay thế", 28),
        ("ghi_chu", "Ghi chú", 36),
    ],
}

# 4 mẫu chuẩn của dự án: Đến Nội bộ, Đến Hạn chế, Đi Nội bộ, Đi Hạn chế
# Tương thích ngược: LoaiVanBan.MAT trỏ trực tiếp về Văn bản Đến - Hạn chế
EXCEL_COLUMNS[LoaiVanBan.DEN] = EXCEL_COLUMNS[(LoaiVanBan.DEN, PhamVi.NOI_BO)]
EXCEL_COLUMNS[LoaiVanBan.DI] = EXCEL_COLUMNS[(LoaiVanBan.DI, PhamVi.NOI_BO)]
EXCEL_COLUMNS[LoaiVanBan.MAT] = EXCEL_COLUMNS[(LoaiVanBan.DEN, PhamVi.HAN_CHE)]

SAMPLE_DATA = {
    (LoaiVanBan.DEN, PhamVi.NOI_BO): {
        "nam": "2026",
        "so_hieu": "15/CV-BGDDT",
        "pham_vi": "Nội bộ",
        "ngay_den": "15/09/2026 08:30:00",
        "ngay_van_ban": "14/09/2026",
        "trich_yeu": "V/v hướng dẫn công tác tuyển sinh và đào tạo năm học 2026-2027",
        "danh_muc_ho_so": "HS-HSHC-QT",
        "ten_loai_van_ban": "Công văn",
        "noi_ban_hanh": "Bộ Giáo dục và Đào tạo",
        "don_vi_nhan": "Ban công nghệ thông tin",
        "nguoi_nhan": "admin",
        "nguoi_ky": "Nguyễn Văn A",
        "chuc_vu": "Thứ trưởng",
        "hieu_luc": "Còn hiệu lực",
        "ngay_het_hieu_luc": "",
        "tep_dinh_kem": "To_trinh_01.pdf",
        "link_thay_the": "12/QĐ-BGDDT",
        "ghi_chu": "(Dòng ví dụ mẫu — xóa trước khi import)",
    },
    (LoaiVanBan.DEN, PhamVi.HAN_CHE): {
        "nam": "2026",
        "so_hieu": "04/TB-SGDDT",
        "pham_vi": "Hạn chế",
        "ngay_den": "18/09/2026 09:15:00",
        "ngay_van_ban": "17/09/2026",
        "trich_yeu": "Thông báo danh sách điều động thanh tra công tác tài chính nội bộ (Hạn chế)",
        "danh_muc_ho_so": "HS-HSTC-CB",
        "ten_loai_van_ban": "Thông báo",
        "noi_ban_hanh": "Sở Giáo dục và Đào tạo",
        "don_vi_nhan": "Ban công nghệ thông tin",
        "nguoi_nhan": "admin",
        "nguoi_ky": "Trần Thị C",
        "chuc_vu": "Phó Giám đốc Sở",
        "hieu_luc": "Còn hiệu lực",
        "ngay_het_hieu_luc": "",
        "tep_dinh_kem": "Thong_bao_thanh_tra.pdf",
        "link_thay_the": "02/TB-SGDDT",
        "ghi_chu": "(Dòng ví dụ mẫu — xóa trước khi import)",
    },
    (LoaiVanBan.DI, PhamVi.NOI_BO): {
        "nam": "2026",
        "so_hieu": "88/QD-SNN",
        "pham_vi": "Nội bộ",
        "ngay_ban_hanh": "20/09/2026",
        "ngay_van_ban": "20/09/2026",
        "trich_yeu": "Quyết định về việc ban hành quy chế chi tiêu nội bộ năm học 2026",
        "danh_muc_ho_so": "HS-HSTC-CB",
        "ten_loai_van_ban": "Quyết định",
        "noi_ban_hanh": "Phòng Hành chính - Tổng hợp",
        "don_vi_nhan": "Ban công nghệ thông tin",
        "nguoi_nhan": "admin",
        "nguoi_ky": "Lê Văn D",
        "chuc_vu": "Hiệu trưởng",
        "hieu_luc": "Còn hiệu lực",
        "ngay_het_hieu_luc": "",
        "tep_dinh_kem": "88_QD_Ban_hanh_quy_che.pdf",
        "link_thay_the": "45/QĐ-SNN",
        "ghi_chu": "(Dòng ví dụ mẫu — xóa trước khi import)",
    },
    (LoaiVanBan.DI, PhamVi.HAN_CHE): {
        "nam": "2026",
        "so_hieu": "12/BC-SNN-HC",
        "pham_vi": "Hạn chế",
        "ngay_ban_hanh": "22/09/2026",
        "ngay_van_ban": "22/09/2026",
        "trich_yeu": "Báo cáo rà soát đánh giá quy hoạch cán bộ chủ chốt giai đoạn 2026-2030 (Hạn chế)",
        "danh_muc_ho_so": "HS-HSKH-TC",
        "ten_loai_van_ban": "Báo cáo",
        "noi_ban_hanh": "Ban Giám hiệu",
        "don_vi_nhan": "Ban công nghệ thông tin",
        "nguoi_nhan": "admin",
        "nguoi_ky": "Lê Văn D",
        "chuc_vu": "Hiệu trưởng",
        "hieu_luc": "Còn hiệu lực",
        "ngay_het_hieu_luc": "",
        "tep_dinh_kem": "12_BC_Danh_gia_can_bo.pdf",
        "link_thay_the": "08/BC-SNN-HC",
        "ghi_chu": "(Dòng ví dụ mẫu — xóa trước khi import)",
    },
}

# 4 mẫu chuẩn của dự án: Đến Nội bộ, Đến Hạn chế, Đi Nội bộ, Đi Hạn chế
# Tương thích ngược: LoaiVanBan.MAT trỏ trực tiếp về Văn bản Đến - Hạn chế
SAMPLE_DATA[LoaiVanBan.DEN] = SAMPLE_DATA[(LoaiVanBan.DEN, PhamVi.NOI_BO)]
SAMPLE_DATA[LoaiVanBan.DI] = SAMPLE_DATA[(LoaiVanBan.DI, PhamVi.NOI_BO)]
SAMPLE_DATA[LoaiVanBan.MAT] = SAMPLE_DATA[(LoaiVanBan.DEN, PhamVi.HAN_CHE)]

HEADER_COMMENTS = {
    "nam": (
        "• TÙY CHỌN: Năm tiếp nhận / phát hành của văn bản (số nguyên dương, VD: 1890, 2024).\n"
        "• Để trống hệ thống sẽ tự động lấy năm hiện tại.\n"
        "• Số đến / Số đi tự động được đánh số riêng theo từng năm."
    ),
    "danh_muc_ho_so": (
        "• BẮT BUỘC: Nhập Số ký hiệu của Hồ sơ (VD: HS-HSHC-QT, 01/HCTH).\n"
        "• Hồ sơ phải có sẵn trong hệ thống (không tự tạo mới khi import).\n"
        "• Thiếu hoặc sai sẽ bị chặn toàn bộ file."
    ),
    "ten_loai_van_ban": (
        "• BẮT BUỘC: Tên loại văn bản (Công văn, Quyết định, Báo cáo...).\n"
        "• Phải có sẵn và trực thuộc đúng Danh mục hồ sơ đã chỉ định ở Cấp 1.\n"
        "• Thiếu hoặc sai sẽ bị chặn toàn bộ file."
    ),
    "don_vi_nhan": (
        "• BẮT BUỘC (Hạn chế): Tên Đơn vị/Phòng ban nhận hoặc chủ trì xử lý.\n"
        "• Đơn vị phải có sẵn trong cơ cấu tổ chức; nhiều đơn vị ngăn cách bằng dấu phẩy (,) hoặc chấm phẩy (;).\n"
        "• Thiếu hoặc sai sẽ bị chặn toàn bộ file."
    ),
    "nguoi_nhan": (
        "• BẮT BUỘC (Hạn chế): Cán bộ nhận / xử lý (nhập Username hoặc Họ tên).\n"
        "• Cán bộ phải thuộc biên chế hoặc kiêm nhiệm của ít nhất 1 Đơn vị nhận đã chỉ định; nhiều cán bộ ngăn cách bằng dấu , hoặc ;.\n"
        "• Thiếu hoặc không thuộc đơn vị sẽ bị chặn toàn bộ file."
    ),
    "nguoi_ky": (
        "• BẮT BUỘC: Họ và tên người ký văn bản.\n"
        "• Không được để trống (thiếu sẽ bị chặn import)."
    ),
    "chuc_vu": (
        "• BẮT BUỘC: Chức vụ của người ký văn bản.\n"
        "• Không được để trống (thiếu sẽ bị chặn import)."
    ),
    "hieu_luc": (
        "• BẮT BUỘC: Chấp nhận: 'Còn hiệu lực', 'Còn hiệu lực 1 phần', 'Hết hiệu lực'.\n"
        "• Mặc định là 'Còn hiệu lực'."
    ),
    "ngay_het_hieu_luc": (
        "• TÙY CHỌN: Ngày văn bản hết hiệu lực (định dạng DD/MM/YYYY).\n"
        "• Có thể để trống nếu văn bản có hiệu lực lâu dài/không xác định thời hạn."
    ),
    "tep_dinh_kem": (
        "• BẮT BUỘC: Tên file đính kèm trong kho tệp (oldfile) hoặc file tải lên kèm request.\n"
        "• Nhiều file phân tách nhau bằng dấu chấm phẩy (;).\n"
        "• Thiếu tên tệp sẽ bị chặn toàn bộ file."
    ),
    "link_thay_the": (
        "• TÙY CHỌN: Số hiệu văn bản bị thay thế trong hệ thống.\n"
        "• Nếu có nhập: Phải tồn tại trong CSDL, cùng phân hệ (Đến/Đi) và cùng phạm vi (Nội bộ/Hạn chế).\n"
        "• Để trống nếu không thay thế."
    ),
    "ghi_chu": (
        "• TÙY CHỌN: Ghi chú bổ sung (nếu có).\n"
        "• Có thể để trống."
    ),
}

_HEADER_COMMENTS_NOI_BO = {
    "don_vi_nhan": (
        "• TÙY CHỌN (Nội bộ): Có thể để trống nếu không chỉ định đơn vị cụ thể.\n"
        "• Nếu nhập: tên Đơn vị/Phòng ban phải có sẵn trong hệ thống; nhiều đơn vị ngăn cách bằng dấu phẩy (,) hoặc chấm phẩy (;)."
    ),
    "nguoi_nhan": (
        "• TÙY CHỌN (Nội bộ): Có thể để trống nếu không chỉ định cán bộ cụ thể.\n"
        "• Nếu nhập cán bộ thì BẮT BUỘC phải nhập Đơn vị nhận trước và mỗi cán bộ phải thuộc biên chế hoặc kiêm nhiệm của ít nhất 1 đơn vị đã nhập.\n"
        "• Nhiều cán bộ ngăn cách bằng dấu phẩy (,) hoặc chấm phẩy (;)."
    ),
}

COMMENT_SIZES = {
    "nam": (360, 95),
    "danh_muc_ho_so": (400, 95),
    "ten_loai_van_ban": (400, 95),
    "don_vi_nhan": (420, 105),
    "nguoi_nhan": (430, 115),
    "nguoi_ky": (300, 80),
    "chuc_vu": (300, 80),
    "tep_dinh_kem": (380, 110),
    "link_thay_the": (250, 85),
    "hieu_luc": (380, 135),
    "ngay_het_hieu_luc": (380, 85),
    "ghi_chu": (250, 75),
}

_header_font = Font(name="Arial", bold=True, size=11, color="FFFFFF")
_header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
_header_fill_den_noibo = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")    # Xanh dương đậm
_header_fill_den_hanche = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")   # Đỏ đậm hạn chế
_header_fill_di_noibo = PatternFill(start_color="047857", end_color="047857", fill_type="solid")     # Xanh lục bảo
_header_fill_di_hanche = PatternFill(start_color="C2410C", end_color="C2410C", fill_type="solid")    # Cam đất / Nâu hổ phách
_header_fill_mat = PatternFill(start_color="922B21", end_color="922B21", fill_type="solid")          # Đỏ đô bảo mật
_header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
_sample_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
_sample_font = Font(name="Arial", size=10, color="374151")
_cell_font = Font(name="Arial", size=10)
_cell_font_han_che = Font(name="Arial", size=10, color="922B21")
_cell_font_han_che_bold = Font(name="Arial", size=10, bold=True, color="C00000")
_fill_han_che = PatternFill(start_color="FFF1F2", end_color="FFF1F2", fill_type="solid")
_cell_alignment = Alignment(vertical="center", wrap_text=True)
_thin_border = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def generate_excel_template(loai: str, pham_vi: str = "NOI_BO") -> io.BytesIO:
    """Sinh file Excel mẫu trực tiếp từ cấu hình DB, phân biệt rõ theo hệ và phạm vi."""
    loai_str = str(loai).strip().upper()
    pv_str = str(pham_vi).strip().upper() if pham_vi else "NOI_BO"
    is_han_che = (pv_str in ("HAN_CHE", "HẠN CHẾ", "HANCHE") or loai_str in ("MAT", "VANBANMAT"))
    norm_pv = PhamVi.HAN_CHE if is_han_che else PhamVi.NOI_BO

    if loai_str in ("DI", "VANBANDI"):
        norm_loai = LoaiVanBan.DI
        active_fill = _header_fill_di_hanche if is_han_che else _header_fill_di_noibo
        sheet_title = "Mẫu VB Đi - Hạn chế" if is_han_che else "Mẫu VB Đi - Nội bộ"
    else:
        # Văn bản Đến (bao gồm cả trường hợp gọi MAT / Văn bản Mật Đến)
        norm_loai = LoaiVanBan.DEN
        active_fill = _header_fill_den_hanche if is_han_che else _header_fill_den_noibo
        sheet_title = "Mẫu VB Đến - Hạn chế" if is_han_che else "Mẫu VB Đến - Nội bộ"

    columns = EXCEL_COLUMNS.get((norm_loai, norm_pv)) or EXCEL_COLUMNS[LoaiVanBan.DEN]
    sample = SAMPLE_DATA.get((norm_loai, norm_pv)) or SAMPLE_DATA[LoaiVanBan.DEN]

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title

    ws.row_dimensions[1].height = 28
    for col_idx, (field_name, col_title, col_width) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_title)
        cell.font = _header_font
        cell.fill = active_fill
        cell.alignment = _header_alignment
        cell.border = _thin_border
        if not is_han_che and field_name in _HEADER_COMMENTS_NOI_BO:
            cmt_text = _HEADER_COMMENTS_NOI_BO[field_name]
        else:
            cmt_text = HEADER_COMMENTS.get(field_name)
        if cmt_text:
            cmt = Comment(cmt_text, "Hệ thống QLVB")
            w, h = COMMENT_SIZES.get(field_name, (400, 120))
            cmt.width = w
            cmt.height = h
            cell.comment = cmt
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    ws.row_dimensions[2].height = 36
    for col_idx, (field_name, _, _) in enumerate(columns, start=1):
        val = sample.get(field_name, "")
        cell = ws.cell(row=2, column=col_idx, value=val)
        cell.font = _sample_font
        cell.fill = _sample_fill
        cell.alignment = _cell_alignment
        cell.border = _thin_border

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    wb.close()
    return output


# ═══════════════════════════════════════════════════════════════════
# 5. IMPORT DỮ LIỆU TỪ EXCEL VÀO ĐÚNG MODEL
# ═══════════════════════════════════════════════════════════════════

HEADER_TO_FIELD = {
    "Năm": "nam",
    "Năm phát hành": "nam",
    "Năm ban hành": "nam",
    "Năm tiếp nhận": "nam",
    "Nam": "nam",
    "Số, ký hiệu VB": "so_hieu",
    "Số hiệu": "so_hieu",
    "Số ký hiệu": "so_hieu",
    "Phạm vi": "pham_vi",
    "Phân loại": "pham_vi",
    "Số đi": "so_thu_tu",
    "Số đến": "so_thu_tu",
    "Số thứ tự": "so_thu_tu",
    "Ngày đến": "ngay_den",
    "Ngày ban hành": "ngay_ban_hanh",
    "Ngày văn bản": "ngay_van_ban",
    "Trích yếu nội dung": "trich_yeu",
    "Trích yếu": "trich_yeu",
    "Danh mục hồ sơ (Số ký hiệu)": "danh_muc_ho_so",
    "Danh mục hồ sơ": "danh_muc_ho_so",
    "Danh mục": "danh_muc_ho_so",
    "Hồ sơ": "danh_muc_ho_so",
    "Mã hồ sơ": "danh_muc_ho_so",
    "Số ký hiệu hồ sơ": "danh_muc_ho_so",
    "Loại văn bản": "ten_loai_van_ban",
    "Tên loại văn bản": "ten_loai_van_ban",
    "Loại VB": "ten_loai_van_ban",
    "Nơi ban hành": "noi_ban_hanh",
    "Phòng ban": "noi_ban_hanh",
    "Đơn vị ban hành": "noi_ban_hanh",
    "Đơn vị nhận / chủ trì": "don_vi_nhan",
    "Đơn vị nhận": "don_vi_nhan",
    "Nơi nhận / Đơn vị nhận": "don_vi_nhan",
    "Nơi nhận": "don_vi_nhan",
    "Cán bộ nhận / xử lý": "nguoi_nhan",
    "Cán bộ nhận / xử lý (Username)": "nguoi_nhan",
    "Cán bộ nhận (Username)": "nguoi_nhan",
    "Cán bộ nhận": "nguoi_nhan",
    "Cán bộ xử lý": "nguoi_nhan",
    "Người nhận": "nguoi_nhan",
    "Người ký": "nguoi_ky",
    "Chức vụ": "chuc_vu",
    "Chức vụ người ký": "chuc_vu",
    "Hiệu lực": "hieu_luc",
    "Trạng thái hiệu lực": "hieu_luc",
    "Ngày hết hiệu lực": "ngay_het_hieu_luc",
    "Ngày hết hạn": "ngay_het_hieu_luc",
    "Hết hiệu lực ngày": "ngay_het_hieu_luc",
    "Link văn bản thay thế": "link_thay_the",
    "Số hiệu văn bản thay thế": "link_thay_the",
    "Văn bản thay thế": "link_thay_the",
    "Link thay thế": "link_thay_the",
    "Tệp đính kèm": "tep_dinh_kem",
    "File đính kèm": "tep_dinh_kem",
    "Tệp tin đính kèm": "tep_dinh_kem",
    "Tập tin đính kèm": "tep_dinh_kem",
    "Tên file": "tep_dinh_kem",
    "Tên tệp": "tep_dinh_kem",
    "File": "tep_dinh_kem",
    "Ghi chú": "ghi_chu",
}


def _parse_excel_year(raw_val):
    """Phân tích cột Năm từ ô Excel. Trả về (year_int_or_None, is_valid)."""
    if raw_val is None:
        return None, True
    if isinstance(raw_val, bool):
        return None, False
    if isinstance(raw_val, int):
        return (raw_val, True) if 1 <= raw_val <= 32767 else (None, False)
    if isinstance(raw_val, float):
        if not math.isfinite(raw_val) or not raw_val.is_integer():
            return None, False
        year_val = int(raw_val)
        return (year_val, True) if 1 <= year_val <= 32767 else (None, False)
    text = str(raw_val).strip()
    if not text:
        return None, True
    if not re.fullmatch(r"\d+", text):
        return None, False
    year_val = int(text)
    return (year_val, True) if 1 <= year_val <= 32767 else (None, False)


def _resolve_don_vi_list(raw_donvi, don_vi_model):
    """Tách nhiều đơn vị phân tách bởi dấu ',', ';' hoặc xuống dòng và tra cứu trong CSDL."""
    if not raw_donvi or not don_vi_model:
        return [], []
    text = str(raw_donvi).strip()
    if not text:
        return [], []

    def _find_one(token: str):
        tok = token.strip()
        if not tok:
            return None
        if tok.isdigit():
            dv = don_vi_model.objects.filter(pk=int(tok)).first()
            if dv:
                return dv
        return don_vi_model.objects.filter(ten__iexact=tok).first()

    if ";" not in text and "\n" not in text:
        whole = _find_one(text)
        if whole:
            return [whole], []

    tokens = [t.strip() for t in re.split(r"[,;\n]+", text) if t.strip()]
    found = []
    missing = []
    seen_ids = set()
    for tok in tokens:
        dv = _find_one(tok)
        if dv:
            if dv.id not in seen_ids:
                seen_ids.add(dv.id)
                found.append(dv)
        else:
            missing.append(tok)
    return found, missing


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value
    if isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())
        return timezone.make_aware(dt)
    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            return timezone.make_aware(dt)
        except ValueError:
            continue
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(text)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt)
        return dt
    except Exception:
        pass
    return None


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _parse_hieu_luc(value):
    if value is None:
        return HieuLuc.CON_HIEU_LUC
    raw = str(value).strip()
    if not raw:
        return HieuLuc.CON_HIEU_LUC
    text = raw.upper()
    norm = _normalize_text(raw)

    # 1. Còn hiệu lực 1 phần (nhận diện: "Còn hiệu lực 1 phần", "Một phần", "CON_HIEU_LUC_1_PHAN", v.v.)
    if (
        text in ("CON_HIEU_LUC_1_PHAN", "CON_HIEU_LUC_MOT_PHAN", "1_PHAN", "MOT_PHAN", "PARTIAL")
        or "1 phan" in norm
        or "mot phan" in norm
        or "sua doi" in norm
        or "bo sung" in norm
    ):
        return HieuLuc.CON_HIEU_LUC_1_PHAN

    # 2. Hết hiệu lực (nhận diện: "Hết hiệu lực", "HET_HIEU_LUC", "Đã thay thế", "HET_VA_THAY_THE", v.v.)
    if (
        text in ("HET_HIEU_LUC", "HET_VA_THAY_THE", "EXPIRED", "THAY_THE")
        or "het" in norm
        or "thay the" in norm
        or "bai bo" in norm
    ):
        return HieuLuc.HET_HIEU_LUC

    # 3. Mặc định là Còn hiệu lực (kể cả khi gõ "Còn hiệu lực", "CON_HIEU_LUC", hoặc để trống)
    return HieuLuc.CON_HIEU_LUC


def _clean_attachment_name(name: str) -> str:
    """
    Chuẩn hóa tên file đính kèm để so khớp chính xác:
    - Loại bỏ khoảng trắng thừa đầu/cuối
    - Chuẩn hóa Unicode tiếng Việt sang dạng dựng sẵn (NFC)
    - Loại bỏ khoảng trắng thừa trước dấu chấm đuôi mở rộng (VD: 'tai_lieu .pdf' -> 'tai_lieu.pdf')
    - Chuyển chữ thường
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFC", str(name)).strip()
    s = re.sub(r"\s+\.([a-zA-Z0-9]+)$", r".\1", s)
    return s.lower()


def can_create_hoso_permission(user) -> bool:
    """
    Kiểm tra người dùng có quyền tạo mới Danh mục hồ sơ / Loại văn bản hay không.
    Theo quy ước Nhóm 3 & Nhóm 7 (Issue #647, release_DDL.sql [VTHS], migration 0019):
    - Admin (is_superuser=True hoặc mã nhóm ADMIN hoặc is_system_admin(user)) có đủ quyền.
    - Văn thư (VT) được cấp quyền add_hoso (dùng chung cho cả Hồ sơ và Loại văn bản).
    - Bất kỳ cán bộ nào được cấp quyền records.add_hoso / add_hoso trong phân hệ Phân quyền.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    try:
        from authorization.permissions import is_system_admin
        if is_system_admin(user):
            return True
    except Exception:
        pass
    try:
        if user.has_perm("records.add_hoso") or user.has_perm("add_hoso"):
            return True
        if hasattr(user, "groups") and user.groups.filter(groupinfo__ma_nhom_quyen__in=["VT", "ADMIN"]).exists():
            return True
        perms = getattr(user, "_user_permissions_cache", None) or set()
        if any("add_hoso" in str(p) for p in perms):
            return True
    except Exception:
        pass
    return False


def import_from_excel(file_obj, loai: str, user, pham_vi: str = None, attachments: list = None) -> dict:
    """Import dữ liệu văn bản từ file Excel vào đúng model tương ứng với Pre-validation nghiêm ngặt."""
    loai_str = str(loai).strip().upper()
    model = get_document_model(loai_str)

    # Lập bản đồ tra cứu file đính kèm tải lên theo tên file (case-insensitive & NFC-normalized)
    uploaded_files_map = {}
    uploaded_stems_map = {}
    if attachments:
        for att in attachments:
            att_name = getattr(att, "name", "")
            if att_name:
                key_clean = _clean_attachment_name(att_name)
                uploaded_files_map[key_clean] = att
                key_raw = str(att_name).strip().lower()
                if key_raw not in uploaded_files_map:
                    uploaded_files_map[key_raw] = att

                # Tương thích định dạng Office phổ biến (.doc <-> .docx, .xls <-> .xlsx, .ppt <-> .pptx)
                stem, ext = os.path.splitext(key_clean)
                if ext == ".docx":
                    uploaded_files_map.setdefault(f"{stem}.doc", att)
                elif ext == ".doc":
                    uploaded_files_map.setdefault(f"{stem}.docx", att)
                elif ext == ".xlsx":
                    uploaded_files_map.setdefault(f"{stem}.xls", att)
                elif ext == ".xls":
                    uploaded_files_map.setdefault(f"{stem}.xlsx", att)
                elif ext == ".pptx":
                    uploaded_files_map.setdefault(f"{stem}.ppt", att)
                elif ext == ".ppt":
                    uploaded_files_map.setdefault(f"{stem}.pptx", att)

                if stem and stem not in uploaded_stems_map:
                    uploaded_stems_map[stem] = att

    wb = load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return {"created": 0, "errors": [{"row": 0, "message": "File không có dữ liệu."}]}

    header_row = rows[0]
    col_map = {}
    for col_idx, header_value in enumerate(header_row):
        if header_value and str(header_value).strip() in HEADER_TO_FIELD:
            col_map[col_idx] = HEADER_TO_FIELD[str(header_value).strip()]

    if not col_map:
        return {
            "created": 0,
            "errors": [{"row": 1, "message": "Không nhận diện được cột. Vui lòng dùng file mẫu."}],
        }

    # ── Xác định phân hệ đích và phạm vi đích mong đợi ──
    norm_loai = (
        LoaiVanBan.MAT
        if loai_str in ("MAT", "VANBANMAT")
        else (LoaiVanBan.DI if loai_str in ("DI", "VANBANDI") else LoaiVanBan.DEN)
    )
    if loai_str in ("MAT", "VANBANMAT"):
        target_pv = PhamVi.HAN_CHE
    elif pham_vi:
        pv_req_norm = _normalize_text(pham_vi)
        target_pv = PhamVi.HAN_CHE if ("han" in pv_req_norm or "mat" in pv_req_norm) else PhamVi.NOI_BO
    else:
        target_pv = PhamVi.NOI_BO

    # Import văn bản Đến/Đi phạm vi Hạn chế cần quyền riêng add_han_che_vanbanden/vanbandi.
    if target_pv == PhamVi.HAN_CHE and norm_loai != LoaiVanBan.MAT:
        from .selectors import co_quyen_them_han_che

        if not co_quyen_them_han_che(user, "vanbandi" if norm_loai == LoaiVanBan.DI else "vanbanden"):
            return {
                "created": 0,
                "errors": [{
                    "row": 0,
                    "message": "Bạn không có quyền thêm văn bản hạn chế. Vui lòng liên hệ Quản trị viên để được cấp quyền.",
                }],
            }

    # ── Phân tích thông tin từ Sheet title, Cột và Dữ liệu ──
    sheet_title_norm = _normalize_text(getattr(ws, "title", ""))
    has_ngay_den_col = any(f == "ngay_den" for f in col_map.values())
    has_ngay_ban_hanh_col = any(f == "ngay_ban_hanh" for f in col_map.values())

    title_is_han_che = any(k in sheet_title_norm for k in ("han che", "mat", "bao mat"))
    title_is_noi_bo = any(k in sheet_title_norm for k in ("noi bo",))
    title_is_den = any(k in sheet_title_norm for k in ("vb den", "van ban den", "mau den"))
    title_is_di = any(k in sheet_title_norm for k in ("vb di", "van ban di", "mau di"))

    sample_rows_count = 0
    valid_data_rows_count = 0
    file_has_han_che_data = False
    file_has_noi_bo_data = False

    for r in rows[1:]:
        r_text = " ".join(str(v) for v in r if v)
        if "xóa trước khi import" in r_text.lower():
            sample_rows_count += 1
            continue
        if not any(v for v in r):
            continue
        valid_data_rows_count += 1
        for c_idx, f_name in col_map.items():
            if f_name == "pham_vi" and c_idx < len(r) and r[c_idx]:
                pv_val = _normalize_text(r[c_idx])
                if "han" in pv_val or "mat" in pv_val:
                    file_has_han_che_data = True
                elif "noi" in pv_val:
                    file_has_noi_bo_data = True

    # 1. Khóa nghiệp vụ: Phạm vi (Nội bộ vs Hạn chế)
    is_file_han_che = title_is_han_che or file_has_han_che_data
    is_file_noi_bo = title_is_noi_bo or file_has_noi_bo_data

    if target_pv == PhamVi.NOI_BO and is_file_han_che and not is_file_noi_bo:
        return {
            "created": 0,
            "errors": [{
                "row": 1,
                "message": "File Excel bạn chọn là biểu mẫu hoặc chứa dữ liệu Văn bản Hạn chế. Bạn đang ở phân hệ Văn bản Nội bộ, hệ thống từ chối nạp để ngăn ngừa lộ lọt thông tin. Vui lòng chuyển sang tab 'Văn bản Hạn chế' để import file này."
            }],
        }

    if target_pv == PhamVi.HAN_CHE and is_file_noi_bo and not is_file_han_che:
        return {
            "created": 0,
            "errors": [{
                "row": 1,
                "message": "File Excel bạn chọn là biểu mẫu hoặc chứa dữ liệu Văn bản Nội bộ. Bạn đang ở phân hệ Văn bản Hạn chế, hệ thống từ chối nạp. Vui lòng chuyển sang tab 'Văn bản Nội bộ' để import file này."
            }],
        }

    # 2. Khóa nghiệp vụ: Loại văn bản (Đến vs Đi)
    if norm_loai == LoaiVanBan.DI:
        if title_is_den or (has_ngay_den_col and not has_ngay_ban_hanh_col and not title_is_di):
            return {
                "created": 0,
                "errors": [{
                    "row": 1,
                    "message": "File Excel bạn chọn là biểu mẫu Văn bản Đến. Bạn đang ở phân hệ Văn bản Đi, vui lòng chọn đúng file mẫu Văn bản Đi để tiếp tục."
                }],
            }

    if norm_loai == LoaiVanBan.DEN:
        if title_is_di or (has_ngay_ban_hanh_col and not has_ngay_den_col and not title_is_den):
            return {
                "created": 0,
                "errors": [{
                    "row": 1,
                    "message": "File Excel bạn chọn là biểu mẫu Văn bản Đi. Bạn đang ở phân hệ Văn bản Đến, vui lòng chọn đúng file mẫu Văn bản Đến để tiếp tục."
                }],
            }

    # 3. Nếu file chỉ chứa duy nhất dòng ví dụ mẫu của template mà không có dữ liệu thực
    if valid_data_rows_count == 0 and sample_rows_count > 0:
        return {
            "created": 0,
            "errors": [{
                "row": 2,
                "message": "File tải lên chỉ chứa dòng ví dụ mẫu ('xóa trước khi import'). Vui lòng xóa dòng ví dụ hoặc nhập thêm dữ liệu văn bản thực tế trước khi thực hiện import."
            }],
        }

    # 4. Pha 1: Pre-validation quét toàn bộ file (Fail-Fast: Chặn toàn bộ nếu có bất kỳ lỗi nào)
    date_field = "ngay_ban_hanh" if norm_loai == LoaiVanBan.DI else "ngay_den"
    date_label = "Ngày ban hành" if norm_loai == LoaiVanBan.DI else "Ngày đến"
    is_restricted_target = (target_pv == PhamVi.HAN_CHE or norm_loai == LoaiVanBan.MAT)

    # Văn bản Hạn chế/Mật: bắt buộc 14 trường (gồm cả Đơn vị nhận & Cán bộ xử lý).
    # Văn bản Nội bộ: cho phép chọn hoặc để trống Đơn vị nhận & Cán bộ xử lý; cột Năm luôn tùy chọn.
    MANDATORY_FIELD_SPECS = [
        ("so_hieu", "Số, ký hiệu văn bản"),
        ("pham_vi", "Phạm vi"),
        (date_field, date_label),
        ("ngay_van_ban", "Ngày văn bản"),
        ("trich_yeu", "Trích yếu nội dung"),
        ("danh_muc_ho_so", "Danh mục hồ sơ (Số ký hiệu)"),
        ("ten_loai_van_ban", "Loại văn bản"),
        ("noi_ban_hanh", "Nơi ban hành"),
        *(
            [
                ("don_vi_nhan", "Đơn vị nhận / chủ trì"),
                ("nguoi_nhan", "Cán bộ nhận / xử lý"),
            ]
            if is_restricted_target
            else []
        ),
        ("nguoi_ky", "Người ký"),
        ("chuc_vu", "Chức vụ người ký"),
        ("hieu_luc", "Hiệu lực"),
        ("tep_dinh_kem", "Tệp đính kèm"),
    ]

    # Kiểm tra sự hiện diện của các cột bắt buộc trong header
    mapped_fields = set(col_map.values())
    missing_header_cols = []
    for f_code, f_label in MANDATORY_FIELD_SPECS:
        if f_code == date_field:
            if not ("ngay_den" in mapped_fields or "ngay_ban_hanh" in mapped_fields):
                missing_header_cols.append(f_label)
        elif f_code not in mapped_fields:
            missing_header_cols.append(f_label)

    if missing_header_cols:
        return {
            "created": 0,
            "errors": [{
                "row": 1,
                "message": f"File Excel thiếu cột bắt buộc: {', '.join(missing_header_cols)}. Vui lòng sử dụng đúng biểu mẫu của hệ thống."
            }],
        }

    try:
        from organizations.models import DonVi
    except ImportError:
        try:
            from apps.organizations.models import DonVi
        except Exception:
            DonVi = None

    try:
        from accounts.models import Employee
    except ImportError:
        try:
            from apps.accounts.models import Employee
        except Exception:
            Employee = None

    pre_validation_errors = []

    for r_idx, r in enumerate(rows[1:], start=2):
        r_text = " ".join(str(v) for v in r if v)
        if "xóa trước khi import" in r_text.lower() or not any(v for v in r):
            continue

        row_dict = {}
        raw_nam_cell = None
        has_nam_col = False
        for c_idx, f_name in col_map.items():
            val = r[c_idx] if c_idx < len(r) else None
            if f_name == "nam":
                has_nam_col = True
                raw_nam_cell = val
            row_dict[f_name] = str(val).strip() if val is not None else ""

        if has_nam_col:
            _, nam_valid = _parse_excel_year(raw_nam_cell)
            if not nam_valid:
                pre_validation_errors.append({
                    "row": r_idx,
                    "message": (
                        f"Dòng {r_idx}: Cột 'Năm' ('{raw_nam_cell}') không hợp lệ. "
                        "Vui lòng nhập số nguyên dương (1 đến 32767) hoặc để trống để lấy năm hiện tại."
                    ),
                })

        # 4.1. Kiểm tra các trường bắt buộc không được để trống
        missing_row_fields = []
        for f_code, f_label in MANDATORY_FIELD_SPECS:
            if f_code == date_field:
                val = row_dict.get(date_field) or row_dict.get("ngay_den") or row_dict.get("ngay_ban_hanh")
            else:
                val = row_dict.get(f_code)
            if not val:
                missing_row_fields.append(f_label)

        if missing_row_fields:
            pre_validation_errors.append({
                "row": r_idx,
                "message": f"Dòng {r_idx} thiếu thông tin bắt buộc: {', '.join(missing_row_fields)}. Vui lòng điền đầy đủ trước khi import."
            })
            continue

        # 4.2. Cặp 1: Phân cấp Lưu trữ (Danh mục hồ sơ -> Loại văn bản)
        r_hoso = row_dict.get("danh_muc_ho_so", "")
        r_loaivb = row_dict.get("ten_loai_van_ban", "")
        hs_obj, lvb_obj = ensure_hoso_and_doc_type(r_hoso, r_loaivb, creator=user, allow_create=False)
        if not hs_obj:
            pre_validation_errors.append({
                "row": r_idx,
                "message": f"Dòng {r_idx}: Danh mục hồ sơ '{r_hoso}' không tồn tại trong hệ thống. Vui lòng nhập đúng số ký hiệu hồ sơ đã có sẵn hoặc bổ sung vào hệ thống trước khi import."
            })
        elif not lvb_obj:
            pre_validation_errors.append({
                "row": r_idx,
                "message": f"Dòng {r_idx}: Loại văn bản '{r_loaivb}' không tồn tại trong Danh mục hồ sơ '{hs_obj.ten_ho_so}' ({hs_obj.so_ky_hieu}). Vui lòng chọn loại văn bản trực thuộc đúng hồ sơ."
            })

        # 4.3. Cặp 2: Phân cấp Tiếp nhận & Phân phối (Đơn vị nhận -> Cán bộ xử lý)
        r_donvi = row_dict.get("don_vi_nhan", "")
        r_nguoinhan = row_dict.get("nguoi_nhan", "")
        if not r_donvi and r_nguoinhan:
            pre_validation_errors.append({
                "row": r_idx,
                "message": (
                    f"Dòng {r_idx}: Đã nhập Cán bộ nhận / xử lý ('{r_nguoinhan}') nhưng để trống Đơn vị nhận. "
                    "Vui lòng nhập Đơn vị nhận tương ứng hoặc để trống cả hai (đối với văn bản Nội bộ)."
                ),
            })
        elif r_donvi:
            found_dvs, missing_dvs = _resolve_don_vi_list(r_donvi, DonVi)
            if not DonVi or missing_dvs:
                for missing_dv in (missing_dvs or [r_donvi]):
                    pre_validation_errors.append({
                        "row": r_idx,
                        "message": f"Dòng {r_idx}: Đơn vị nhận '{missing_dv}' không tồn tại trong cơ cấu tổ chức hệ thống. Vui lòng kiểm tra lại hoặc liên hệ Quản trị viên."
                    })
            elif Employee and r_nguoinhan:
                dv_ids = [dv.id for dv in found_dvs]
                dv_names = ", ".join(dv.ten for dv in found_dvs)
                raw_cbs = [u.strip() for u in re.split(r"[,;\n]+", str(r_nguoinhan)) if u.strip()]
                for cb in raw_cbs:
                    emp = Employee.objects.filter(username__iexact=cb).first() or Employee.objects.filter(ho_ten__iexact=cb).first()
                    if not emp:
                        pre_validation_errors.append({
                            "row": r_idx,
                            "message": f"Dòng {r_idx}: Cán bộ xử lý '{cb}' không tồn tại trong hệ thống."
                        })
                    else:
                        belongs = (emp.don_vi_id in dv_ids) or emp.assignments.filter(don_vi_id__in=dv_ids).exists()
                        if not belongs:
                            pre_validation_errors.append({
                                "row": r_idx,
                                "message": f"Dòng {r_idx}: Cán bộ '{cb}' không thuộc biên chế hoặc kiêm nhiệm của đơn vị '{dv_names}'."
                            })

        # 4.4. Kiểm tra Văn bản thay thế (link_thay_the) nếu có nhập
        r_link = row_dict.get("link_thay_the", "")
        if r_link:
            raw_targets = [t.strip() for t in re.split(r"[,;\n]+", str(r_link)) if t.strip()]
            for tgt in raw_targets:
                target_doc = find_replacement_target_document(
                    tgt,
                    target_model=model,
                    current_pham_vi=target_pv
                )
                if not target_doc:
                    exists_elsewhere = find_replacement_target_document(tgt)
                    module_name = "Văn bản Đến" if norm_loai == LoaiVanBan.DEN else "Văn bản Đi"
                    scope_name = "Hạn chế" if target_pv == PhamVi.HAN_CHE else "Nội bộ"
                    if exists_elsewhere:
                        other_mod = "Văn bản Đi" if isinstance(exists_elsewhere, VanBanDi) else "Văn bản Đến"
                        other_sc = "Hạn chế" if getattr(exists_elsewhere, "pham_vi", "") == PhamVi.HAN_CHE else "Nội bộ"
                        pre_validation_errors.append({
                            "row": r_idx,
                            "message": f"Dòng {r_idx}: Văn bản thay thế '{tgt}' thuộc {other_mod} ({other_sc}), không cùng phân hệ {module_name} ({scope_name}) đang import."
                        })
                    else:
                        pre_validation_errors.append({
                            "row": r_idx,
                            "message": f"Dòng {r_idx}: Văn bản thay thế '{tgt}' không tồn tại trong hệ thống."
                        })

        # 4.5. Kiểm tra Ngày hết hiệu lực (ngay_het_hieu_luc) nếu có nhập
        r_het = row_dict.get("ngay_het_hieu_luc", "")
        if r_het:
            parsed_het = _parse_date(r_het)
            if not parsed_het:
                pre_validation_errors.append({
                    "row": r_idx,
                    "message": f"Dòng {r_idx}: Ngày hết hiệu lực '{r_het}' không đúng định dạng ngày tháng hợp lệ (DD/MM/YYYY)."
                })

    if pre_validation_errors:
        wb.close()
        return {
            "created": 0,
            "errors": pre_validation_errors,
        }

    # 5. Pha 2: Thực thi nạp dữ liệu văn bản vào CSDL
    created_count = 0
    errors = []

    for row_idx, row_data in enumerate(rows[1:], start=2):
        row_text = " ".join(str(v) for v in row_data if v)
        if "xóa trước khi import" in row_text.lower() or not any(v for v in row_data):
            continue

        doc_data = {"nguoi_tao": user}

        for col_idx, field_name in col_map.items():
            value = row_data[col_idx] if col_idx < len(row_data) else None

            if field_name in ("ngay_den", "ngay_ban_hanh", "ngay_van_ban", "ngay_het_hieu_luc"):
                doc_data[field_name] = _parse_date(value)
            elif field_name == "hieu_luc":
                doc_data[field_name] = _parse_hieu_luc(value)
            elif field_name == "nam":
                parsed_nam, nam_ok = _parse_excel_year(value)
                if nam_ok and parsed_nam is not None:
                    doc_data["nam"] = parsed_nam
            else:
                doc_data[field_name] = str(value).strip() if value else ""

        if not doc_data.get("trich_yeu"):
            errors.append({"row": row_idx, "message": "Thiếu trích yếu nội dung."})
            continue

        if not doc_data.get("so_hieu"):
            errors.append({"row": row_idx, "message": "Thiếu số, ký hiệu văn bản."})
            continue

        nam = doc_data.get("nam") or timezone.localtime(timezone.now()).year
        doc_data["nam"] = nam

        if loai_str in ("MAT", "VANBANMAT"):
            doc_data["pham_vi"] = PhamVi.HAN_CHE
            doc_data["gui_mail_toan_he_thong"] = False
            doc_data.pop("so_thu_tu", None)
            if not doc_data.get("ngay_ban_hanh"):
                doc_data["ngay_ban_hanh"] = timezone.now()
            if not doc_data.get("ngay_van_ban"):
                doc_data["ngay_van_ban"] = doc_data["ngay_ban_hanh"]
        else:
            doc_data["pham_vi"] = target_pv

            current_stt = doc_data.get("so_thu_tu")
            if not current_stt or not str(current_stt).isdigit() or int(current_stt) <= 0:
                doc_data["so_thu_tu"] = generate_so_thu_tu(loai_str, nam)
            else:
                doc_data["so_thu_tu"] = int(current_stt)

            if loai_str in ("DEN", "VANBANDEN"):
                if not doc_data.get("ngay_van_ban") and doc_data.get("ngay_ban_hanh"):
                    doc_data["ngay_van_ban"] = doc_data["ngay_ban_hanh"]
                if not doc_data.get("ngay_den"):
                    doc_data["ngay_den"] = timezone.now()
                if not doc_data.get("ngay_van_ban"):
                    doc_data["ngay_van_ban"] = doc_data["ngay_den"]
            elif loai_str in ("DI", "VANBANDI"):
                if not doc_data.get("ngay_ban_hanh") and doc_data.get("ngay_den"):
                    doc_data["ngay_ban_hanh"] = doc_data["ngay_den"]
                if not doc_data.get("ngay_ban_hanh"):
                    doc_data["ngay_ban_hanh"] = timezone.now()
                if not doc_data.get("ngay_van_ban"):
                    doc_data["ngay_van_ban"] = doc_data["ngay_ban_hanh"]

        try:
            model_fields = {
                f.name for f in model._meta.get_fields()
                if hasattr(f, "attname") and not getattr(f, "many_to_many", False) and not getattr(f, "one_to_many", False)
            }
            payload = {k: v for k, v in doc_data.items() if k in model_fields and k != "nguoi_nhan"}
            if "nguoi_tao" in model_fields and user and user.is_authenticated and "nguoi_tao" not in payload:
                payload["nguoi_tao"] = user
            created_doc = model.objects.create(**payload)

            # 0. Liên kết Hồ sơ và Loại văn bản (theo nguyên tắc phân cấp 1 rồi mới tới 2, bảo đảm Database Trigger)
            raw_hoso = doc_data.get("danh_muc_ho_so")
            raw_loaivb = doc_data.get("ten_loai_van_ban")
            if raw_hoso or raw_loaivb:
                hs, lvb = ensure_hoso_and_doc_type(raw_hoso, raw_loaivb, creator=user, allow_create=False)
                if hs:
                    if loai_str in ("DI", "VANBANDI"):
                        from .models import VanBanDiHoSo, VanBanDiDanhmuc
                        VanBanDiHoSo.objects.create(vanbandi=created_doc, hoso_id=hs.id)
                        if lvb:
                            VanBanDiDanhmuc.objects.create(vanbandi=created_doc, loaivanban_id=lvb.id)
                    else:
                        from .models import VanBanDenHoSo, VanBanDenDanhmuc
                        VanBanDenHoSo.objects.create(vanbanden=created_doc, hoso_id=hs.id)
                        if lvb:
                            VanBanDenDanhmuc.objects.create(vanbanden=created_doc, loaivanban_id=lvb.id)

            # 1. Liên kết cán bộ nhận (nguoi_nhan) từ username/họ tên trong file Excel
            raw_nguoi_nhan = doc_data.get("nguoi_nhan")
            if raw_nguoi_nhan and hasattr(created_doc, "nguoi_nhan") and Employee:
                raw_cbs = [u.strip() for u in re.split(r"[,;\n]+", str(raw_nguoi_nhan)) if u.strip()]
                for cb in raw_cbs:
                    emp = Employee.objects.filter(username__iexact=cb).first() or Employee.objects.filter(ho_ten__iexact=cb).first()
                    if emp:
                        created_doc.nguoi_nhan.add(emp)

            # 2. Với văn bản Hạn chế hoặc Văn bản Mật: luôn đảm bảo người tạo/import được thêm vào nguoi_nhan
            is_restricted = (
                getattr(created_doc, "pham_vi", None) == PhamVi.HAN_CHE
                or loai_str in ("MAT", "VANBANMAT")
            )
            if is_restricted and user and user.is_authenticated and hasattr(created_doc, "nguoi_nhan"):
                created_doc.nguoi_nhan.add(user)

            # 3. Liên kết Đơn vị nhận (don_vi_nhan) nếu có (hỗ trợ nhiều đơn vị phân tách ',', ';' hoặc xuống dòng)
            raw_don_vi = doc_data.get("don_vi_nhan")
            if raw_don_vi and DonVi:
                try:
                    from .models import VanBanDenDonViNhan, VanBanDiDonViNhan

                    dvs, _ = _resolve_don_vi_list(raw_don_vi, DonVi)
                    for dv in dvs:
                        if loai_str in ("DEN", "VANBANDEN", "MAT", "VANBANMAT"):
                            VanBanDenDonViNhan.objects.get_or_create(vanbanden=created_doc, donvi_id=dv.id)
                        elif loai_str in ("DI", "VANBANDI"):
                            VanBanDiDonViNhan.objects.get_or_create(vanbandi=created_doc, donvi_id=dv.id)
                except Exception:
                    pass

            # 4. Nếu là Văn bản Đi và có nơi ban hành là tên phòng ban nội bộ, liên kết VanBanDiNoiBanHanh
            if loai_str in ("DI", "VANBANDI") and doc_data.get("noi_ban_hanh") and DonVi:
                try:
                    from .models import VanBanDiNoiBanHanh

                    nbh_val = str(doc_data["noi_ban_hanh"]).strip()
                    dv_nbh = None
                    if nbh_val.isdigit():
                        dv_nbh = DonVi.objects.filter(pk=int(nbh_val)).first()
                    if not dv_nbh:
                        dv_nbh = DonVi.objects.filter(ten__iexact=nbh_val).first()
                    if dv_nbh:
                        VanBanDiNoiBanHanh.objects.get_or_create(vanbandi=created_doc, donvi_id=dv_nbh.id)
                except Exception:
                    pass

            # 5. Đồng bộ quan hệ thay thế 2 chiều nếu file Excel có cung cấp link_thay_the
            if getattr(created_doc, "link_thay_the", None):
                sync_replacement_document(created_doc)

            # 6. Liên kết tệp đính kèm từ cột tep_dinh_kem (kho oldfile)
            raw_tep_dinh_kem = doc_data.get("tep_dinh_kem")
            if raw_tep_dinh_kem:
                raw_files_str = str(raw_tep_dinh_kem).replace("\n", ";").replace(",", ";")
                file_names = [f.strip() for f in raw_files_str.split(";") if f.strip()]
                if file_names:
                    base_module = "van-ban-di" if loai_str in ("DI", "VANBANDI") else "van-ban-den"
                    is_han_che_doc = (
                        getattr(created_doc, "pham_vi", "") == PhamVi.HAN_CHE
                        or loai_str in ("MAT", "VANBANMAT")
                    )
                    pv_folder = "han-che" if is_han_che_doc else "noi-bo"

                    doc_dt = None
                    if base_module == "van-ban-den":
                        doc_dt = getattr(created_doc, "ngay_den", None) or getattr(created_doc, "ngay_van_ban", None)
                    else:
                        doc_dt = getattr(created_doc, "ngay_ban_hanh", None) or getattr(created_doc, "ngay_van_ban", None)

                    if not doc_dt:
                        doc_dt = timezone.now()
                    elif timezone.is_aware(doc_dt):
                        doc_dt = timezone.localtime(doc_dt)

                    date_str = doc_dt.strftime("%Y/%m/%d")

                    oldfile_root = getattr(settings, "OLDFILE_STORAGE_ROOT", "")
                    if not oldfile_root:
                        if getattr(settings, "DOCUMENT_STORAGE_ROOT", ""):
                            oldfile_root = str(Path(settings.DOCUMENT_STORAGE_ROOT).parent / "oldfile")
                        else:
                            oldfile_root = str(Path(settings.BASE_DIR).parent / "storage" / "oldfile")

                    AttachmentModel = VanBanDiAttachment if base_module == "van-ban-di" else VanBanDenAttachment

                    for fn in file_names:
                        clean_fn = _clean_attachment_name(fn)
                        fn_stem, _ = os.path.splitext(clean_fn)

                        # 6.1. Ưu tiên 1: Tệp được người dùng tải lên trực tiếp trong request import
                        matched_up_file = (
                            uploaded_files_map.get(clean_fn)
                            or uploaded_files_map.get(fn.strip().lower())
                            or (uploaded_files_map.get(f"{clean_fn}x") if clean_fn.endswith((".doc", ".xls", ".ppt")) else None)
                            or (uploaded_files_map.get(clean_fn[:-1]) if clean_fn.endswith((".docx", ".xlsx", ".pptx")) else None)
                            or (uploaded_stems_map.get(fn_stem) if fn_stem else None)
                        )
                        if matched_up_file:
                            up_file = matched_up_file
                            try:
                                if hasattr(up_file, "seek"):
                                    up_file.seek(0)
                            except Exception:
                                pass

                            att_real_name = getattr(up_file, "name", "") or fn.strip()
                            final_name = fn.strip()
                            if att_real_name and os.path.splitext(att_real_name)[1].lower() != os.path.splitext(fn.strip())[1].lower():
                                final_name = att_real_name

                            AttachmentModel.objects.create(
                                document=created_doc,
                                name=final_name,
                                file=up_file,
                                file_size=getattr(up_file, "size", 0),
                                nguoi_tao=user if user and user.is_authenticated else None,
                            )
                            continue

                        # 6.2. Ưu tiên 2: Tìm trong kho tệp lịch sử (oldfile)
                        rel_oldfile_sub = f"{base_module}/{pv_folder}/{date_str}/{fn.strip()}"
                        db_path = f"oldfile/{rel_oldfile_sub}"

                        disk_file = Path(oldfile_root) / rel_oldfile_sub
                        if not (disk_file.exists() and disk_file.is_file()):
                            flex_dir = Path(oldfile_root) / base_module / pv_folder
                            if flex_dir.exists() and flex_dir.is_dir():
                                found_candidates = list(flex_dir.glob(f"**/{fn.strip()}"))
                                if not found_candidates and clean_fn:
                                    found_candidates = [
                                        cand for cand in flex_dir.glob("**/*")
                                        if cand.is_file() and (
                                            _clean_attachment_name(cand.name) == clean_fn
                                            or (fn_stem and os.path.splitext(_clean_attachment_name(cand.name))[0] == fn_stem)
                                        )
                                    ]
                                if found_candidates:
                                    disk_file = found_candidates[0]
                                    rel_sub = disk_file.relative_to(Path(oldfile_root)).as_posix()
                                    db_path = f"oldfile/{rel_sub}"

                        if disk_file.exists() and disk_file.is_file():
                            att_disk_name = disk_file.name
                            final_disk_name = fn.strip()
                            if os.path.splitext(att_disk_name)[1].lower() != os.path.splitext(fn.strip())[1].lower():
                                final_disk_name = att_disk_name

                            AttachmentModel.objects.create(
                                document=created_doc,
                                name=final_disk_name,
                                path=db_path,
                                nguoi_tao=user if user and user.is_authenticated else None,
                            )
                        else:
                            errors.append({
                                "row": row_idx,
                                "message": f"Văn bản '{created_doc.so_hieu}' đã được tạo, nhưng chưa tìm thấy tệp đính kèm '{fn.strip()}'."
                            })

            created_count += 1
        except Exception as e:
            errors.append({"row": row_idx, "message": str(e)})

    wb.close()
    return {"created": created_count, "errors": errors}


# ═══════════════════════════════════════════════════════════════════
# 6. EXPORT DANH SÁCH RA EXCEL THEO BỘ LỌC
# ═══════════════════════════════════════════════════════════════════

def export_to_excel(queryset, loai: str, pham_vi: str = None) -> io.BytesIO:
    """Xuất danh sách văn bản ra file Excel theo bộ lọc hiện tại (chuẩn 18 cột đồng bộ)."""
    loai_str = str(loai).strip().upper()
    is_han_che_only = (str(pham_vi).strip().upper() == "HAN_CHE" or loai_str in ("MAT", "VANBANMAT"))

    if loai_str in ("MAT", "VANBANMAT"):
        norm_loai = LoaiVanBan.MAT
        active_fill = _header_fill_mat
        has_so_thu_tu = False
    elif loai_str in ("DI", "VANBANDI"):
        norm_loai = LoaiVanBan.DI
        active_fill = _header_fill_mat if is_han_che_only else _header_fill
        has_so_thu_tu = True
    else:
        norm_loai = LoaiVanBan.DEN
        active_fill = _header_fill_mat if is_han_che_only else _header_fill
        has_so_thu_tu = True

    columns = EXCEL_COLUMNS.get(norm_loai, EXCEL_COLUMNS[LoaiVanBan.DEN])

    wb = Workbook()
    ws = wb.active
    loai_display = dict(LoaiVanBan.choices).get(norm_loai, norm_loai)
    if is_han_che_only:
        ws.title = f"VB {loai_display} (Hạn chế)"
    else:
        ws.title = f"Danh sách {loai_display}"

    # Cột STT
    stt_cell = ws.cell(row=1, column=1, value="STT")
    stt_cell.font = _header_font
    stt_cell.fill = active_fill
    stt_cell.alignment = _header_alignment
    stt_cell.border = _thin_border
    ws.column_dimensions["A"].width = 6

    if has_so_thu_tu:
        # Cột Số đến / Số đi
        so_label = "Số đến" if norm_loai == LoaiVanBan.DEN else "Số đi"
        so_cell = ws.cell(row=1, column=2, value=so_label)
        so_cell.font = _header_font
        so_cell.fill = active_fill
        so_cell.alignment = _header_alignment
        so_cell.border = _thin_border
        ws.column_dimensions["B"].width = 10
        col_offset = 3
    else:
        col_offset = 2

    for col_idx, (_, col_title, col_width) in enumerate(columns, start=col_offset):
        cell = ws.cell(row=1, column=col_idx, value=col_title)
        cell.font = _header_font
        cell.fill = active_fill
        cell.alignment = _header_alignment
        cell.border = _thin_border
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    ws.row_dimensions[1].height = 28

    hieu_luc_map = dict(HieuLuc.choices)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=False)
    align_left_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=False)

    center_fields = {"nam", "so_hieu", "pham_vi", "ngay_den", "ngay_ban_hanh", "ngay_van_ban", "hieu_luc", "ngay_het_hieu_luc", "link_thay_the"}
    wrap_fields = {"trich_yeu", "noi_ban_hanh", "ghi_chu", "tep_dinh_kem", "don_vi_nhan", "nguoi_nhan"}

    for row_idx, doc in enumerate(queryset, start=2):
        is_doc_han_che = (
            getattr(doc, "pham_vi", "") == PhamVi.HAN_CHE
            or getattr(doc, "loai", "") == "MAT"
            or getattr(doc, "document_kind", "") == "vanbanmat"
        )
        row_fill = _fill_han_che if is_doc_han_che else None

        trich_yeu_text = str(getattr(doc, "trich_yeu", "") or "").strip()
        noi_ban_hanh_text = str(getattr(doc, "noi_ban_hanh", "") or "").strip()
        ghi_chu_text = str(getattr(doc, "ghi_chu", "") or "").strip()

        tep_dinh_kem_text = ""
        if hasattr(doc, "attachments"):
            atts = [a.name for a in doc.attachments.all() if not getattr(a, "is_deleted", False) and a.name]
            tep_dinh_kem_text = "; ".join(atts)
        lines_att = max(1, math.ceil(len(tep_dinh_kem_text) / 28)) if tep_dinh_kem_text else 1

        lines_ty = 1
        if trich_yeu_text:
            lines_ty = sum(max(1, math.ceil(len(line.strip()) / 52)) for line in trich_yeu_text.splitlines() if line.strip()) or 1
        lines_nbh = max(1, math.ceil(len(noi_ban_hanh_text) / 26)) if noi_ban_hanh_text else 1
        lines_gc = 1
        if ghi_chu_text:
            lines_gc = sum(max(1, math.ceil(len(line.strip()) / 25)) for line in ghi_chu_text.splitlines() if line.strip()) or 1

        est_lines = max(lines_ty, lines_nbh, lines_gc, lines_att)
        if est_lines <= 1:
            ws.row_dimensions[row_idx].height = 28
        else:
            ws.row_dimensions[row_idx].height = est_lines * 19 + 10

        cell_stt = ws.cell(row=row_idx, column=1, value=row_idx - 1)
        cell_stt.font = _cell_font_han_che if is_doc_han_che else _cell_font
        cell_stt.alignment = align_center
        cell_stt.border = _thin_border
        if row_fill:
            cell_stt.fill = row_fill

        if has_so_thu_tu:
            cell_so = ws.cell(row=row_idx, column=2, value=getattr(doc, "so_thu_tu", ""))
            cell_so.font = _cell_font_han_che if is_doc_han_che else _cell_font
            cell_so.alignment = align_center
            cell_so.border = _thin_border
            if row_fill:
                cell_so.fill = row_fill

        for col_idx, (field_name, _, _) in enumerate(columns, start=col_offset):
            val = getattr(doc, field_name, "")
            if field_name == "danh_muc_ho_so":
                hs_val = getattr(doc, "_danh_muc_ho_so", None) or getattr(doc, "danh_muc_ho_so", "")
                if not hs_val and hasattr(doc, "hoso"):
                    first_hs = doc.hoso.first()
                    if first_hs:
                        try:
                            from records.models import HoSo
                            hs_obj = HoSo.objects.filter(pk=first_hs.hoso_id).first()
                            if hs_obj:
                                hs_val = hs_obj.so_ky_hieu or hs_obj.ten_ho_so
                        except Exception:
                            pass
                val = hs_val or ""
            elif field_name == "ten_loai_van_ban":
                lvb_val = getattr(doc, "_ten_loai_van_ban", None) or getattr(doc, "ten_loai_van_ban", "")
                if not lvb_val and hasattr(doc, "danhmuc"):
                    first_dm = doc.danhmuc.first()
                    if first_dm:
                        try:
                            from records.models import LoaiVanBan as RecordLoaiVanBan
                            lvb_obj = RecordLoaiVanBan.objects.filter(pk=first_dm.loaivanban_id).first()
                            if lvb_obj:
                                lvb_val = lvb_obj.ten_loai
                        except Exception:
                            pass
                if not lvb_val:
                    lvb_val = infer_doc_type(getattr(doc, "so_hieu", ""), getattr(doc, "trich_yeu", ""))
                val = lvb_val or ""
            elif field_name == "don_vi_nhan":
                dv_val = ""
                if hasattr(doc, "donvinhan"):
                    dv_ids = list(doc.donvinhan.values_list("donvi_id", flat=True))
                    if dv_ids:
                        try:
                            from organizations.models import DonVi
                            names = list(DonVi.objects.filter(id__in=dv_ids).values_list("ten", flat=True))
                            dv_val = ", ".join(names)
                        except Exception:
                            pass
                val = dv_val
            elif field_name == "nguoi_nhan":
                nn_val = ""
                if hasattr(doc, "nguoi_nhan"):
                    usernames = list(doc.nguoi_nhan.values_list("username", flat=True))
                    nn_val = ", ".join(usernames)
                val = nn_val
            elif field_name == "tep_dinh_kem":
                val = tep_dinh_kem_text
            elif field_name == "pham_vi":
                val = "Hạn chế" if is_doc_han_che else "Nội bộ"
            elif field_name == "ngay_het_hieu_luc":
                if val and isinstance(val, datetime):
                    if timezone.is_aware(val):
                        val = timezone.localtime(val)
                    val = val.strftime("%d/%m/%Y")
                elif val and isinstance(val, date):
                    val = val.strftime("%d/%m/%Y")
                else:
                    val = ""
            elif isinstance(val, datetime):
                if timezone.is_aware(val):
                    val = timezone.localtime(val)
                val = val.strftime("%d/%m/%Y %H:%M" if field_name == "ngay_den" else "%d/%m/%Y")
            elif isinstance(val, date):
                val = val.strftime("%d/%m/%Y")
            elif field_name == "hieu_luc":
                val = hieu_luc_map.get(val, val)
            elif val is None:
                val = ""

            cell = ws.cell(row=row_idx, column=col_idx, value=str(val).strip())

            # Font chữ nổi bật cho dòng Hạn chế
            if field_name == "pham_vi":
                cell.font = _cell_font_han_che_bold if is_doc_han_che else _cell_font
            elif field_name == "so_hieu" and is_doc_han_che:
                cell.font = _cell_font_han_che_bold
            else:
                cell.font = _cell_font

            if row_fill:
                cell.fill = row_fill

            cell.border = _thin_border

            if field_name in center_fields:
                cell.alignment = align_center
            elif field_name in wrap_fields:
                cell.alignment = align_left_wrap
            else:
                cell.alignment = align_left

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    wb.close()
    return output


# ═══════════════════════════════════════════════════════════════════
# 7. DỊCH VỤ GỬI EMAIL THÔNG BÁO VĂN BẢN
# ═══════════════════════════════════════════════════════════════════

def send_document_notification_mail(document, recipient_list=None, force_system_wide: bool = False):
    """
    Dịch vụ gửi email thông báo văn bản.
    QUY TẮC BẢO MẬT TUYỆT ĐỐI (Issue #82 & Luật BVBMNN):
    - KHÓA HOÀN TOÀN chức năng gửi mail toàn hệ thống đối với Văn bản Mật và Văn bản Hạn chế.
    - Bất kỳ nỗ lực nào gửi mail toàn hệ thống cho VB Mật sẽ bị chặn ngay lập tức (raise ValidationError).
    - Với VB Mật / Hạn chế: chỉ được gửi email đích danh cho các cán bộ trong danh sách người nhận (nguoi_nhan).
    """
    from django.core.exceptions import ValidationError

    doc_kind = getattr(document, "document_kind", "")
    is_confidential = (
        getattr(document, "loai", "") == "MAT"
        or doc_kind == "vanbanmat"
        or getattr(document, "pham_vi", "") == PhamVi.HAN_CHE
    )

    if is_confidential:
        if force_system_wide or getattr(document, "gui_mail_toan_he_thong", False) or recipient_list == "ALL":
            raise ValidationError(
                "TUYỆT ĐỐI CẤM GỬI EMAIL TOÀN HỆ THỐNG đối với văn bản mật / văn bản hạn chế theo Luật Bảo vệ BMNN."
            )

    # Đảm bảo cờ gui_mail_toan_he_thong của VB mật luôn là False
    if is_confidential and getattr(document, "gui_mail_toan_he_thong", False):
        document.gui_mail_toan_he_thong = False
        if hasattr(document, "save"):
            document.save(update_fields=["gui_mail_toan_he_thong"])

    # Xác định danh sách email người nhận hợp lệ
    emails = []
    if is_confidential:
        if recipient_list and recipient_list != "ALL":
            for u in recipient_list:
                email = getattr(u, "email", None) or (u if isinstance(u, str) and "@" in u else None)
                if email and email not in emails:
                    emails.append(email)
        elif hasattr(document, "nguoi_nhan"):
            for u in document.nguoi_nhan.all():
                if u.email and u.email not in emails:
                    emails.append(u.email)
    else:
        if getattr(document, "gui_mail_toan_he_thong", False) or force_system_wide or recipient_list == "ALL":
            from django.contrib.auth import get_user_model
            User = get_user_model()
            emails = list(User.objects.filter(is_active=True).exclude(email="").values_list("email", flat=True))
        elif recipient_list:
            for u in recipient_list:
                email = getattr(u, "email", None) or (u if isinstance(u, str) and "@" in u else None)
                if email and email not in emails:
                    emails.append(email)

    return {
        "success": True,
        "is_confidential": is_confidential,
        "recipient_count": len(emails),
        "recipients": emails,
    }


# ═══════════════════════════════════════════════════════════════════
# 7. QUẢN LÝ DANH MỤC HỒ SƠ & LOẠI VĂN BẢN ĐỒNG BỘ DDL (RECORDS)
# ═══════════════════════════════════════════════════════════════════

def infer_doc_type(so_hieu: str = "", trich_yeu: str = "") -> str:
    """Suy luận loại văn bản từ số hiệu hoặc trích yếu (hỗ trợ hiển thị và lọc dự phòng)."""
    type_mapping = {
        "QĐ": "Quyết định", "QD": "Quyết định",
        "TB": "Thông báo",
        "CV": "Công văn",
        "HD": "Hướng dẫn", "HĐ": "Hướng dẫn",
        "KH": "Kế hoạch",
        "CT": "Chỉ thị",
        "BC": "Báo cáo",
        "TTR": "Tờ trình",
        "NQ": "Nghị quyết",
    }
    if so_hieu:
        match = re.search(r"/([A-ZĐ]+)(?:-|$)", str(so_hieu), re.IGNORECASE)
        if match and match.group(1).upper() in type_mapping:
            return type_mapping[match.group(1).upper()]
    if trich_yeu:
        ty_upper = str(trich_yeu).strip().upper()
        for prefix, name in [
            ("QUYẾT ĐỊNH", "Quyết định"),
            ("THÔNG BÁO", "Thông báo"),
            ("HƯỚNG DẪN", "Hướng dẫn"),
            ("KẾ HOẠCH", "Kế hoạch"),
            ("CÔNG VĂN", "Công văn"),
            ("CHỈ THỊ", "Chỉ thị"),
            ("TỜ TRÌNH", "Tờ trình"),
            ("BÁO CÁO", "Báo cáo"),
            ("NGHỊ QUYẾT", "Nghị quyết"),
        ]:
            if ty_upper.startswith(prefix):
                return name
    return ""


def ensure_standard_hoso_and_doc_types():
    """Tự động đảm bảo 7 Danh mục hồ sơ nghiệp vụ chuẩn và Loại văn bản con luôn tồn tại."""
    try:
        from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan
        from django.contrib.auth import get_user_model
    except Exception:
        return

    try:
        HoSo.objects.exists()
    except Exception:
        try:
            from django.core.management import call_command
            call_command("migrate", "records", interactive=False)
        except Exception:
            return

    User = get_user_model()
    admin_u = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not admin_u:
        return

    STANDARD_FOLDERS = {
        "Hồ sơ Hành chính - Quản trị": ("HS-HCQT", ["Công văn", "Thông báo", "Tờ trình"]),
        "Hồ sơ Tổ chức - Cán bộ": ("HS-TCCB", ["Quyết định", "Thông báo", "Hướng dẫn"]),
        "Hồ sơ Kế hoạch - Tài chính": ("HS-KHTC", ["Kế hoạch", "Quyết định", "Báo cáo"]),
        "Hồ sơ Chuyên môn - Nghiệp vụ": ("HS-CMNV", ["Hướng dẫn", "Công văn", "Kế hoạch"]),
        "Hồ sơ Thanh tra - Pháp chế": ("HS-TTPC", ["Quyết định", "Chỉ thị", "Nghị quyết"]),
        "Hồ sơ Kế hoạch - Dự án": ("HS-KHDA", ["Kế hoạch", "Báo cáo", "Quyết định"]),
        "Hồ sơ Lưu trữ cơ quan": ("HS-LTCQ", ["Công văn", "Quyết định", "Thông báo"]),
    }
    for ten_hs, (so_kh, types) in STANDARD_FOLDERS.items():
        hs = HoSo.objects.filter(ten_ho_so__iexact=ten_hs).first() or HoSo.objects.filter(so_ky_hieu__iexact=so_kh).first()
        if not hs:
            try:
                hs = HoSo.objects.create(ten_ho_so=ten_hs, so_ky_hieu=so_kh, nguoi_lap=admin_u)
            except Exception:
                hs = HoSo.objects.filter(so_ky_hieu__iexact=so_kh).first()
        if hs:
            for dt in types:
                if not RecordLoaiVanBan.objects.filter(ten_loai__iexact=dt, ho_so=hs).exists():
                    try:
                        RecordLoaiVanBan.objects.create(ho_so=hs, ten_loai=dt)
                    except Exception:
                        pass


def ensure_hoso_and_doc_type(ho_so_name: str, loai_van_ban_name: str = "", creator=None, allow_create: bool = True):
    """
    Tìm hoặc tự động tạo HoSo và LoaiVanBan an toàn theo nguyên tắc phân cấp 1 rồi mới tới 2:
    - Khi allow_create=False (dùng trong Import Excel): Chỉ so khớp dữ liệu CÓ SẴN trong CSDL.
      Tuyệt đối KHÔNG tự tiện tạo mới để tránh làm sai lệch danh mục chuẩn của cơ quan.
      Cấp 1: Tìm theo so_ky_hieu (ưu tiên số 1) hoặc ten_ho_so. Nếu không tìm thấy -> Trả về (None, None).
      Cấp 2: Bắt buộc chỉ tìm LoaiVanBan TRỰC THUỘC ĐÚNG HỒ SƠ Cấp 1 đã tìm thấy. Nếu không có -> Trả về (hs, None).
    - Khi allow_create=True (dùng khi API/Form hoặc seeding/khởi tạo ban đầu): Cho phép tự sinh an toàn.
    """
    try:
        from records.models import HoSo, LoaiVanBan as RecordLoaiVanBan
        from django.contrib.auth import get_user_model
    except Exception:
        return None, None

    try:
        HoSo.objects.exists()
    except Exception:
        try:
            from django.core.management import call_command
            call_command("migrate", "records", interactive=False)
        except Exception:
            return None, None

    ensure_standard_hoso_and_doc_types()

    User = get_user_model()
    admin_u = creator or User.objects.filter(is_superuser=True).first() or User.objects.first()

    clean_hs = str(ho_so_name or "").strip()
    clean_lvb = str(loai_van_ban_name or "").strip()

    hs = None
    if clean_hs:
        if clean_hs.isdigit():
            hs = HoSo.objects.filter(pk=int(clean_hs)).first()
        if not hs:
            # Ưu tiên tìm theo số ký hiệu hồ sơ trước, sau đó tên hồ sơ
            hs = HoSo.objects.filter(so_ky_hieu__iexact=clean_hs).first() or HoSo.objects.filter(ten_ho_so__iexact=clean_hs).first()
        if not hs and allow_create and admin_u and can_create_hoso_permission(admin_u):
            # Tạo mới Hồ sơ an toàn với mã chống trùng lặp (chỉ khi allow_create=True)
            words = clean_hs.split()
            abbr = "".join(w[0].upper() for w in words if w.isalnum()) or "HS"
            base_so_kh = f"HS-{abbr}"[:240]
            so_kh = base_so_kh
            counter = 1
            while HoSo.objects.filter(so_ky_hieu=so_kh).exists():
                so_kh = f"{base_so_kh}-{counter}"[:250]
                counter += 1
            try:
                hs = HoSo.objects.create(
                    ten_ho_so=clean_hs,
                    so_ky_hieu=so_kh,
                    nguoi_lap=admin_u,
                )
            except Exception:
                hs = HoSo.objects.filter(ten_ho_so__iexact=clean_hs).first() or HoSo.objects.filter(so_ky_hieu__iexact=so_kh).first()

    if not hs:
        if allow_create:
            # Fallback an toàn nếu allow_create: ưu tiên hồ sơ hệ thống HSC
            hs = HoSo.objects.filter(is_he_thong=True).first() or HoSo.objects.first()
        else:
            return None, None

    lvb = None
    if hs and clean_lvb:
        if clean_lvb.isdigit():
            lvb = RecordLoaiVanBan.objects.filter(pk=int(clean_lvb), ho_so=hs).first()
        if not lvb:
            lvb = RecordLoaiVanBan.objects.filter(ten_loai__iexact=clean_lvb, ho_so=hs).first()
        if not lvb and allow_create:
            # Tự động tạo Loại văn bản con trực thuộc chính Hồ sơ hs (chỉ khi allow_create=True)
            try:
                lvb = RecordLoaiVanBan.objects.create(
                    ho_so=hs,
                    ten_loai=clean_lvb,
                )
            except Exception:
                lvb = RecordLoaiVanBan.objects.filter(ten_loai__iexact=clean_lvb, ho_so=hs).first()

    if hs and not lvb and allow_create:
        lvb = RecordLoaiVanBan.objects.filter(ho_so=hs).first()
        if not lvb:
            default_name = clean_lvb or "Chung"
            try:
                lvb = RecordLoaiVanBan.objects.create(
                    ho_so=hs,
                    ten_loai=default_name,
                )
            except Exception:
                lvb = RecordLoaiVanBan.objects.filter(ho_so=hs).first()

    return hs, lvb
