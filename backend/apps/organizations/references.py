"""
Kiểm Đơn vị / Chức vụ còn được module khác dùng hay không trước khi xóa.

release_DDL.sql đặt ON DELETE RESTRICT cho các cột dưới đây, nhưng model của các nhóm khác hiện lưu id
bằng BigIntegerField (chưa có khóa ngoại) nên Django không tự chặn: DB dựng bằng migration sẽ xóa được và
để lại id mồ côi, DB dựng từ DDL thì báo lỗi 500. Danh sách lấy từ DDL (chỉ các cột RESTRICT không phải FK
Django); khi nhóm sở hữu đổi sang ForeignKey(on_delete=PROTECT) thì ProtectedError sẽ chặn và có thể bỏ dòng.
"""
from django.apps import apps

# (app_label, model, cột id) theo DDL: REFERENCES organizations_donvi (id) ON DELETE RESTRICT
UNIT_REFERENCES = [
    ("document_templates", "TaiLieuChiTiet", "don_vi_id"),  # records_chitiettailieu
    ("documents", "VanBanDenDonViNhan", "donvi_id"),  # documents_vanbanden_donvinhan
    ("documents", "VanBanDiDonViNhan", "donvi_id"),  # documents_vanbandi_donvinhan
    ("documents", "VanBanDiNoiBanHanh", "donvi_id"),  # documents_vanbandi_noibanhanh
    ("signing", "SigningProcess", "don_vi_ap_dung_id"),  # signing_process
]

# Theo DDL: REFERENCES accounts_position (id) ON DELETE RESTRICT
POSITION_REFERENCES = [
    ("signing", "SigningProcessStepSigner", "chuc_vu_id"),  # signing_process_step_signer
]


def _is_referenced(references, pk) -> bool:
    for app_label, model_name, field in references:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            continue  # module chưa có trên nhánh này
        if model.objects.filter(**{field: pk}).exists():
            return True
    return False


def unit_in_use(pk) -> bool:
    return _is_referenced(UNIT_REFERENCES, pk)


def position_in_use(pk) -> bool:
    return _is_referenced(POSITION_REFERENCES, pk)
