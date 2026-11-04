from django.db import migrations, models
from django.utils import timezone


def _khoa_doi_tuong(cau_hinh):
    """Đối tượng người ký của dòng cấu hình: theo tài khoản hoặc theo chức vụ và phạm vi."""
    if cau_hinh.nguoi_ky_id is not None:
        return ("nguoi_ky", cau_hinh.nguoi_ky_id)
    return ("chuc_vu", cau_hinh.chuc_vu_id, cau_hinh.pham_vi_chuc_vu)


def chuyen_ky_nhay_thanh_ky_chinh(apps, schema_editor):
    """
    Chuyển dữ liệu ký nháy thành ký chính thay vì dừng migration; dữ liệu ủy quyền mất cùng các cột bị bỏ bên dưới
    (dòng người ký giữ nguyên tài khoản, thứ tự và trạng thái).
    - Cấu hình quy trình: ký nháy thành ký chính, giữ cấp và thứ tự; dòng trùng đối tượng với dòng ký chính khác
      trong cùng cấp bị xóa để lượt trình ký mới không báo người ký trùng trong cấp.
    - Hồ sơ đã tạo: ký nháy thành ký chính; ràng buộc (buoc_ky, nguoi_ky) không đổi nên không phát sinh trùng.
    - Cấp đang ký còn người ký chưa được mở (trước đó bị ký nháy chặn): mở ngay vì không còn cơ chế chặn.
    """
    alias = schema_editor.connection.alias
    cau_hinh_nguoi_ky = apps.get_model("signing", "SigningProcessStepSigner").objects.using(alias)
    nguoi_ky_ho_so = apps.get_model("signing", "SigningRequestStepSigner").objects.using(alias)

    buoc_co_ky_nhay = cau_hinh_nguoi_ky.filter(vai_tro_ky="KY_NHAY").values_list("buoc_quy_trinh_id", flat=True).distinct()
    for buoc_id in list(buoc_co_ky_nhay):
        dong_buoc = cau_hinh_nguoi_ky.filter(buoc_quy_trinh_id=buoc_id).order_by("thu_tu", "pk")
        da_co = {_khoa_doi_tuong(c) for c in dong_buoc if c.vai_tro_ky != "KY_NHAY"}
        for cau_hinh in dong_buoc:
            if cau_hinh.vai_tro_ky != "KY_NHAY":
                continue
            khoa = _khoa_doi_tuong(cau_hinh)
            if khoa in da_co:
                cau_hinh.delete()
                continue
            da_co.add(khoa)
            cau_hinh.vai_tro_ky = "KY_CHINH"
            cau_hinh.save(update_fields=["vai_tro_ky"])

    nguoi_ky_ho_so.filter(vai_tro_ky="KY_NHAY").update(vai_tro_ky="KY_CHINH")

    chua_mo = nguoi_ky_ho_so.filter(
        trang_thai="CHO_KY",
        thoi_diem_mo__isnull=True,
        buoc_ky__trang_thai="DANG_KY",
        buoc_ky__luot_trinh__trang_thai="CHO_KY",
    ).select_related("buoc_ky")
    for dong in list(chua_mo):
        dong.thoi_diem_mo = dong.buoc_ky.thoi_diem_mo or timezone.now()
        dong.save(update_fields=["thoi_diem_mo"])


class Migration(migrations.Migration):
    dependencies = [("signing", "0017_signingrequest_uq_signing_completed_doc")]

    operations = [
        # Không hoàn tác dữ liệu: ký nháy đã thành ký chính và dữ liệu ủy quyền đã bị bỏ cùng cột.
        migrations.RunPython(chuyen_ky_nhay_thanh_ky_chinh, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="signingrequeststepsigner", name="chk_signing_signer_ly_do_uy_quyen"),
        migrations.RemoveField(model_name="signingrequeststepsigner", name="uy_quyen_tu"),
        migrations.RemoveField(model_name="signingrequeststepsigner", name="chuc_vu_goc_uy_quyen"),
        migrations.RemoveField(model_name="signingrequeststepsigner", name="ly_do_uy_quyen"),
        migrations.RemoveField(model_name="signingrequeststepsigner", name="ngay_uy_quyen"),
        migrations.RemoveField(model_name="signingrequeststepsigner", name="chan_ky_chinh"),
        migrations.RemoveField(model_name="signingprocessstepsigner", name="chan_ky_chinh"),
        migrations.DeleteModel(name="SigningDelegationRole"),
        migrations.AlterField(
            model_name="signingprocessstepsigner",
            name="vai_tro_ky",
            field=models.CharField(choices=[("KY_CHINH", "Ký chính")], db_default="KY_CHINH", default="KY_CHINH", max_length=20),
        ),
        migrations.AlterField(
            model_name="signingrequeststepsigner",
            name="vai_tro_ky",
            field=models.CharField(choices=[("KY_CHINH", "Ký chính")], max_length=20),
        ),
    ]
