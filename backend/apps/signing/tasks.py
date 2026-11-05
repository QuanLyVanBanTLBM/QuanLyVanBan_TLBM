import logging

from celery import shared_task
from django.db import OperationalError

logger = logging.getLogger(__name__)


class LoiTamThoiTaoTep(Exception):
    """Lỗi PDF đã ghi trạng thái LOI và có thể thử lại sau."""


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def gui_email_thong_bao(tb_id: int) -> bool:
    """Gửi một dòng outbox; lỗi SMTP được lưu để lịch outbox hiện tại gửi lại."""
    from signing.services.thong_bao import gui_email

    logger.info("Celery gửi thông báo Trình ký %s", tb_id)
    return gui_email(tb_id)


@shared_task(
    autoretry_for=(OperationalError, LoiTamThoiTaoTep),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def tao_tep_hoan_tat(luot_id: int, nguoi_id: int) -> str:
    """Tạo PDF theo ID; lỗi tạm được phục hồi an toàn trước mỗi lần retry."""
    from signing import enums
    from signing.models import SigningAttempt
    from signing.services.tep_hoan_tat import (
        la_loi_vinh_vien,
        phuc_hoi_mot_luot_tep_hoan_tat,
        tao_tep_hoan_tat as tao_tep,
    )

    luot = SigningAttempt.objects.filter(pk=luot_id).first()
    if luot is None:
        logger.warning("Bỏ qua task PDF cho lượt không còn tồn tại %s", luot_id)
        return "KHONG_TON_TAI"

    if luot.trang_thai_tep_hoan_tat == enums.TrangThaiTepHoanTat.LOI:
        if la_loi_vinh_vien(luot.loi_tep_hoan_tat):
            return luot.trang_thai_tep_hoan_tat
        ket_qua = phuc_hoi_mot_luot_tep_hoan_tat(luot_id)
        if ket_qua is None:
            luot.refresh_from_db(fields=["trang_thai_tep_hoan_tat", "loi_tep_hoan_tat"])
            return luot.trang_thai_tep_hoan_tat
        luot.refresh_from_db(fields=["trang_thai_tep_hoan_tat", "loi_tep_hoan_tat"])
    else:
        luot = tao_tep(luot_id, nguoi_id)

    if (
        luot.trang_thai_tep_hoan_tat == enums.TrangThaiTepHoanTat.LOI
        and not la_loi_vinh_vien(luot.loi_tep_hoan_tat)
    ):
        raise LoiTamThoiTaoTep(f"Lỗi tạm khi tạo PDF cho lượt {luot_id}: {luot.loi_tep_hoan_tat}")

    logger.info("Celery hoàn tất tạo PDF cho lượt %s: %s", luot_id, luot.trang_thai_tep_hoan_tat)
    return luot.trang_thai_tep_hoan_tat
