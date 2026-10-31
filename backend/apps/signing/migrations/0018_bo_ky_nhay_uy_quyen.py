from django.db import migrations, models


def kiem_tra_khong_con_ky_nhay_uy_quyen(apps, schema_editor):
    """Dừng khi còn dữ liệu ký nháy hoặc ủy quyền; không tự đổi vai trò vì làm đổi ý nghĩa chữ ký."""
    nguoi_ky_ho_so = apps.get_model("signing", "SigningRequestStepSigner")
    nguoi_ky_cau_hinh = apps.get_model("signing", "SigningProcessStepSigner")
    vuong = {
        "dòng người ký của hồ sơ": nguoi_ky_ho_so.objects.filter(
            models.Q(vai_tro_ky="KY_NHAY") | models.Q(uy_quyen_tu__isnull=False)
        ).count(),
        "cấu hình người ký của quy trình": nguoi_ky_cau_hinh.objects.filter(vai_tro_ky="KY_NHAY").count(),
    }
    con_lai = {ten: so for ten, so in vuong.items() if so}
    if con_lai:
        chi_tiet = ", ".join(f"{ten}: {so}" for ten, so in con_lai.items())
        raise RuntimeError(
            f"Còn dữ liệu ký nháy hoặc ủy quyền ({chi_tiet}). Dọn dữ liệu này trước khi áp dụng migration."
        )


class Migration(migrations.Migration):
    dependencies = [("signing", "0017_signingrequest_uq_signing_completed_doc")]

    operations = [
        migrations.RunPython(kiem_tra_khong_con_ky_nhay_uy_quyen, migrations.RunPython.noop),
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
