"""
Bằng chứng tổng hợp của lượt trình — phần lõi Phase 10 (#80; plan mục 3.2, 5.2 `signing_manifest`).

- chot_bang_chung: khi cấp cuối ký đủ, trong cùng transaction hoàn tất, chụp nội dung chuẩn hóa của lượt
  (mã băm tệp, cấp, người ký, chữ ký hiện hành, khóa công khai, thời điểm) và lưu `DA_CHOT` (bất biến ở model
  và trigger PostgreSQL).
- Mã băm bằng chứng = SHA-256 trên JSON chuẩn hóa (khóa sắp xếp, không khoảng trắng, UTF-8). JSONB không giữ
  thứ tự khóa nên luôn chuẩn hóa lại khi băm; nội dung chỉ dùng chuỗi, số nguyên, boolean, null.
- xac_minh: băm lại nội dung, verify lại từng chữ ký Ed25519 bằng khóa công khai ghi trong bằng chứng
  (xác minh được cả khi không tra CSDL khóa), đối chiếu tệp gốc và tệp hoàn tất đang lưu.
"""

import json
from datetime import timezone as dt_timezone

from django.db.models import Prefetch

from .. import crypto, enums
from ..models import SigningManifest, SigningRequestStep, SigningRequestStepSigner, SigningSignature
from ..storage import StorageError, get_storage
from ..tich_hop.to_chuc import ten_hien_thi
from ..tich_hop.van_ban import mo_ta_van_ban
from .audit import ghi_nhat_ky

PHIEN_BAN_BANG_CHUNG = 1
NHAN_DIEN = "BẢN DUYỆT NỘI BỘ, CHƯA PHÁT HÀNH"


def _thoi_diem(dt):
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z") if dt else None


def ma_hoa_chuan(noi_dung) -> bytes:
    return json.dumps(noi_dung, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _chu_ky(ck):
    khoa = ck.khoa_ky
    return {
        "id": ck.pk, "khoa_ky": khoa.pk, "ma_khoa": khoa.ma_khoa, "dau_van_tay_khoa": khoa.dau_van_tay,
        "khoa_cong_khai": khoa.khoa_cong_khai, "thuat_toan": ck.thuat_toan, "hash_tai_lieu": ck.hash_tai_lieu,
        "chu_ky_so": ck.chu_ky_so, "ngay_ky": _thoi_diem(ck.ngay_ky), "ky_tre_han": ck.ky_tre_han,
        "so_giay_tre": ck.so_giay_tre, "ghi_chu_ky": ck.ghi_chu_ky,
        "ma_bam_anh_chu_ky": ck.ma_bam_anh_chu_ky or None,
    }


def _vi_tri(n):
    """Khung ký (tỷ lệ % theo trang, gốc trên-trái); số thập phân ghi dạng chuỗi để băm ổn định."""
    if n.trang_ky is None:
        return None
    return {"trang_ky": n.trang_ky, **{f: str(getattr(n, f)) for f in
                                        ("toa_do_x", "toa_do_y", "chieu_rong_khung", "chieu_cao_khung")}}


def noi_dung_bang_chung(luot):
    yeu_cau = luot.trinh_ky
    nguoi_ky = SigningRequestStepSigner.objects.select_related("chu_ky_hien_hanh__khoa_ky").order_by("id")
    cap_ky = SigningRequestStep.objects.filter(luot_trinh=luot).order_by("thu_tu").prefetch_related(
        Prefetch("nguoi_ky_set", queryset=nguoi_ky))
    return {
        "phien_ban": PHIEN_BAN_BANG_CHUNG,
        "nhan_dien": NHAN_DIEN,
        "ho_so": {
            "id": yeu_cau.pk, "document_type": yeu_cau.document_type, "van_ban_id": yeu_cau.van_ban_id,
            "van_ban": mo_ta_van_ban(yeu_cau.document_type, yeu_cau.van_ban_id), "muc_do": yeu_cau.muc_do,
            "quy_trinh": {"id": yeu_cau.quy_trinh_id, "ma": yeu_cau.quy_trinh.ma_quy_trinh,
                          "ten": yeu_cau.quy_trinh.ten_quy_trinh, "phien_ban": yeu_cau.phien_ban_quy_trinh},
            "nguoi_tao": {"id": yeu_cau.create_by_id, "ten": ten_hien_thi(yeu_cau.create_by)},
            "ho_so_goc": yeu_cau.ho_so_goc_id,
        },
        "luot_trinh": {
            "id": luot.pk, "so_luot": luot.so_luot, "luot_truoc": luot.luot_truoc_id,
            "phien_ban_van_ban": luot.phien_ban_van_ban, "ma_bam_tai_lieu": luot.ma_bam_tai_lieu,
            "thuat_toan_bam": "SHA-256", "thoi_diem_gui": _thoi_diem(luot.thoi_diem_gui),
            "thoi_diem_hoan_thanh": _thoi_diem(luot.thoi_diem_hoan_thanh),
        },
        "cap_ky": [{
            "thu_tu": cap.thu_tu, "cap_ky": cap.cap_ky, "ten_cap_ky": cap.ten_cap_ky,
            "han_xu_ly": _thoi_diem(cap.han_xu_ly), "thoi_diem_mo": _thoi_diem(cap.thoi_diem_mo),
            "thoi_diem_hoan_thanh": _thoi_diem(cap.thoi_diem_hoan_thanh),
            "nguoi_ky": [{
                "id": n.pk, "nguoi_ky": n.nguoi_ky_id, "ten_nguoi_ky": n.ten_nguoi_ky, "ten_chuc_vu": n.ten_chuc_vu,
                "vai_tro_ky": n.vai_tro_ky, "vi_tri": _vi_tri(n),
                "chu_ky": _chu_ky(n.chu_ky_hien_hanh) if n.chu_ky_hien_hanh else None,
            } for n in cap.nguoi_ky_set.all()],
        } for cap in cap_ky],
    }


def chot_bang_chung(luot, nguoi, thoi_diem):
    """Gọi trong transaction hoàn tất lượt (sau khi lượt `HOAN_THANH`)."""
    noi_dung = noi_dung_bang_chung(luot)
    ma_bam = crypto.sha256_hex(ma_hoa_chuan(noi_dung))
    manifest = SigningManifest.objects.create(
        luot_trinh=luot, phien_ban_bang_chung=PHIEN_BAN_BANG_CHUNG, noi_dung_chuan_hoa=noi_dung,
        ma_bam_bang_chung=ma_bam, trang_thai=enums.TrangThaiManifest.DA_CHOT, thoi_diem_chot=thoi_diem,
        create_by=nguoi,
    )
    ghi_nhat_ky(nguoi, "signing_manifest", manifest.pk, "CHOT_BANG_CHUNG", trinh_ky=luot.trinh_ky, luot_trinh=luot,
                trang_thai_sau=manifest.trang_thai, du_lieu_kem_theo={"ma_bam_bang_chung": ma_bam})
    return manifest


def bang_chung_cua(luot):
    if luot is None:
        return None
    return luot.manifest_set.filter(trang_thai=enums.TrangThaiManifest.DA_CHOT).order_by("-id").first()


def _tep_khop(vi_tri, ma_bam):
    if not vi_tri or not ma_bam:
        return None
    try:
        return crypto.sha256_hex(get_storage().read_bytes(vi_tri)) == ma_bam
    except StorageError:
        return False


def xac_minh(manifest):
    noi_dung = manifest.noi_dung_chuan_hoa
    luot = manifest.luot_trinh
    ma_bam_khop = crypto.sha256_hex(ma_hoa_chuan(noi_dung)) == manifest.ma_bam_bang_chung
    hash_tep = noi_dung["luot_trinh"]["ma_bam_tai_lieu"]
    vi_tri_anh = dict(SigningSignature.objects.filter(luot_trinh=luot).values_list("pk", "vi_tri_anh_chu_ky"))
    chu_ky = []
    for cap in noi_dung["cap_ky"]:
        for n in cap["nguoi_ky"]:
            ck = n["chu_ky"]
            hop_le = ck is not None and ck["hash_tai_lieu"] == hash_tep and (
                crypto.key_fingerprint(ck["khoa_cong_khai"]) == ck["dau_van_tay_khoa"]
            ) and crypto.verify_signature(ck["khoa_cong_khai"], bytes.fromhex(ck["hash_tai_lieu"]), ck["chu_ky_so"])
            anh_khop = _tep_khop(vi_tri_anh.get(ck["id"]), ck.get("ma_bam_anh_chu_ky")) if ck else None
            chu_ky.append({"nguoi_ky": n["id"], "ten_nguoi_ky": n["ten_nguoi_ky"],
                           "chu_ky": ck["id"] if ck else None, "hop_le": bool(hop_le), "anh_chu_ky_khop": anh_khop})
    tep_goc_khop = _tep_khop(luot.vi_tri_luu_tep, luot.ma_bam_tai_lieu)
    tep_hoan_tat_khop = _tep_khop(luot.vi_tri_tep_hoan_tat, luot.ma_bam_tep_hoan_tat)
    return {
        "ma_bam_bang_chung_khop": ma_bam_khop,
        "chu_ky": chu_ky,
        "tep_goc_khop": tep_goc_khop,
        "tep_hoan_tat_khop": tep_hoan_tat_khop,
        "hop_le": ma_bam_khop and bool(chu_ky) and all(c["hop_le"] and c["anh_chu_ky_khop"] is not False
                                                      for c in chu_ky)
        and tep_goc_khop is True and tep_hoan_tat_khop is not False,
    }
