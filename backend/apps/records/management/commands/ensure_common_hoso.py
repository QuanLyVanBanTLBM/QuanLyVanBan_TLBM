from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, IntegrityError, transaction

from records.models import HoSo


class Command(BaseCommand):
    help = "Tạo Hồ sơ chung đúng một lần sau khi tài khoản admin đã tồn tại."

    def add_arguments(self, parser):
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS)

    def handle(self, *args, **options):
        using = options["database"]
        user_model = get_user_model()
        admin = user_model._default_manager.db_manager(using).filter(
            **{user_model.USERNAME_FIELD: "admin"}
        ).first()
        if admin is None:
            raise CommandError("Chưa có tài khoản admin; chưa thể tạo Hồ sơ chung.")

        try:
            with transaction.atomic(using=using):
                if HoSo.objects.using(using).filter(is_he_thong=True).exists():
                    self.stdout.write("Hồ sơ chung đã tồn tại.")
                    return

                existing_hsc = HoSo.objects.using(using).filter(
                    so_ky_hieu="HSC"
                ).first()
                if existing_hsc is not None:
                    existing_hsc.is_he_thong = True
                    existing_hsc.save(
                        using=using,
                        update_fields=["is_he_thong", "updated_at"],
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Đã đánh dấu hồ sơ HSC hiện có là Hồ sơ chung."
                        )
                    )
                    return

                first_priority_available = not HoSo.objects.using(using).filter(
                    stt_uu_tien=1
                ).exists()
                HoSo(
                    stt_uu_tien=1 if first_priority_available else None,
                    so_ky_hieu="HSC",
                    ten_ho_so="Hồ sơ chung",
                    nguoi_lap=admin,
                    is_he_thong=True,
                    ghi_chu="Hồ sơ chung mặc định của hệ thống - không được xóa",
                ).save(using=using)
        except IntegrityError as exc:
            raise CommandError(
                "Không thể tạo Hồ sơ chung do dữ liệu thay đổi đồng thời; "
                "hãy chạy lại lệnh sau khi kiểm tra dữ liệu."
            ) from exc
        self.stdout.write(self.style.SUCCESS("Đã tạo Hồ sơ chung."))
