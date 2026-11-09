"""Tạo và xác minh mã OTP một lần cho việc tạo hoặc khôi phục PIN ký."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from ..errors import ConflictError, SigningError
from ..models import SigningPinOtpChallenge
from . import pin
from .audit import ghi_nhat_ky

logger = logging.getLogger(__name__)
HET_HAN_OTP = timedelta(minutes=10)
GIAN_CACH_GUI = timedelta(minutes=2)
SO_LAN_SAI_TOI_DA = 5


def _tao_ma():
    return f"{secrets.randbelow(1_000_000):06d}"


def _bam(user_id, challenge_id, ma):
    du_lieu = f"signing-pin-otp-v1:{user_id}:{challenge_id}:{ma}".encode()
    return hmac.new(pin._bi_mat_may_chu(), du_lieu, hashlib.sha256).hexdigest()


def _gui_sms(user, ma):
    url = getattr(settings, "SIGNING_SMS_URL", "")
    authorization = getattr(settings, "SIGNING_SMS_AUTHORIZATION", "")
    sender = getattr(settings, "SIGNING_SMS_FROM", "")
    if not url or not authorization or not sender or not url.startswith("https://"):
        raise SigningError(
            code="otp_sms_chua_cau_hinh", detail="SMS OTP chưa được cấu hình trên máy chủ.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    payload = json.dumps({
        "from": sender,
        "to": user.sdt,
        "text": f"Ma OTP xac nhan PIN ky cua ban la {ma}. Ma co hieu luc trong 10 phut.",
    }).encode("utf-8")
    request = Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": authorization,
    }, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise SigningError(code="gui_otp_that_bai", detail="Nhà cung cấp SMS từ chối gửi mã OTP.")
    except HTTPError as exc:
        logger.warning("SMS OTP delivery rejected with HTTP %s", exc.code)
        raise SigningError(code="gui_otp_that_bai", detail="Không gửi được SMS OTP.") from None
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("SMS OTP delivery failed (%s)", type(exc).__name__)
        raise SigningError(code="gui_otp_that_bai", detail="Không gửi được SMS OTP.") from None


def _gui_email(user, ma):
    # Dùng mailer chung của phân hệ để tương thích cả cấu hình Django 5.2 và 6.1.
    from .thong_bao import ket_noi_email

    message = EmailMessage(
        subject="Mã xác nhận PIN ký",
        body=f"Mã OTP của bạn là {ma}. Mã có hiệu lực trong 10 phút.",
        from_email=None,
        to=[user.email],
        connection=ket_noi_email(),
    )
    if message.send() != 1:
        raise SigningError(code="gui_otp_that_bai", detail="Không gửi được email OTP.")


def _gui_otp(user, kenh, ma):
    try:
        if kenh == "SMS":
            _gui_sms(user, ma)
        else:
            _gui_email(user, ma)
    except SigningError:
        raise
    except Exception as exc:
        logger.warning("OTP delivery failed over %s (%s)", kenh, type(exc).__name__)
        raise SigningError(code="gui_otp_that_bai", detail="Không gửi được OTP.") from None


def _dich_den(user, kenh):
    if kenh == "SMS":
        return (getattr(user, "sdt", "") or "").strip()
    return (getattr(user, "email", "") or "").strip()


@transaction.atomic
def yeu_cau_ma(user, pin_moi, pin_xac_nhan, kenh="SMS", *, dia_chi_ip=None):
    pin.kiem_tra_pin(pin_moi, "pin_moi")
    if pin_moi != pin_xac_nhan:
        raise SigningError(code="pin_xac_nhan_khong_khop", detail="Hai lần nhập PIN không khớp.")
    kenh = str(kenh).upper()
    if kenh not in {"SMS", "EMAIL"}:
        raise SigningError(code="kenh_otp_khong_hop_le", detail="Chọn SMS hoặc email để nhận mã OTP.")
    if not _dich_den(user, kenh):
        raise SigningError(code="kenh_otp_khong_kha_dung", detail="Tài khoản chưa có thông tin liên hệ cho kênh đã chọn.")

    get_user_model().objects.select_for_update().get(pk=user.pk)
    bay_gio = timezone.now()
    SigningPinOtpChallenge.objects.filter(
        nguoi_dung=user, da_dung_luc__isnull=True, da_huy_luc__isnull=True, het_han__lte=bay_gio,
    ).update(da_huy_luc=bay_gio, pin_moi_verifier="", ma_bam="")
    gan_nhat = (SigningPinOtpChallenge.objects.select_for_update().filter(
        nguoi_dung=user, da_dung_luc__isnull=True, da_huy_luc__isnull=True, het_han__gt=bay_gio,
    ).order_by("-created_at", "-pk").first())
    if gan_nhat and gan_nhat.created_at > bay_gio - GIAN_CACH_GUI:
        con_lai = max(1, int((gan_nhat.created_at + GIAN_CACH_GUI - bay_gio).total_seconds()))
        raise ConflictError(code="otp_gui_qua_nhanh", detail="Vui lòng chờ trước khi yêu cầu mã mới.",
                            fields={"gian_cach_giay": [con_lai]})

    verifier_pin = pin.tao_verifier(pin_moi)
    challenge = SigningPinOtpChallenge.objects.create(
        nguoi_dung=user,
        pin_moi_verifier=verifier_pin,
        ma_bam="",
        kenh=kenh,
        het_han=bay_gio + HET_HAN_OTP,
    )
    ma = _tao_ma()
    challenge.ma_bam = _bam(user.pk, challenge.pk, ma)
    challenge.save(update_fields=["ma_bam"])
    try:
        _gui_otp(user, kenh, ma)
    except Exception:
        challenge.delete()
        raise

    if gan_nhat:
        gan_nhat.da_huy_luc = bay_gio
        gan_nhat.pin_moi_verifier = ""
        gan_nhat.ma_bam = ""
        gan_nhat.save(update_fields=["da_huy_luc", "pin_moi_verifier", "ma_bam"])
    ghi_nhat_ky(user, "signing_pin_otp_challenge", challenge.pk, "GUI_OTP_PIN", dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"kenh": kenh, "het_han": challenge.het_han.isoformat()})
    return challenge


def xac_nhan_ma(user, challenge_id, ma, *, dia_chi_ip=None):
    if not isinstance(ma, str) or not ma.isdigit() or len(ma) != 6:
        raise SigningError(code="otp_khong_hop_le", detail="Mã OTP phải gồm đúng 6 chữ số.")
    loi = None
    credential = None
    with transaction.atomic():
        try:
            challenge = SigningPinOtpChallenge.objects.select_for_update().get(pk=challenge_id, nguoi_dung=user)
        except SigningPinOtpChallenge.DoesNotExist:
            raise SigningError(code="otp_khong_hop_le", detail="Yêu cầu OTP không còn hiệu lực.") from None
        bay_gio = timezone.now()
        if challenge.da_dung_luc or challenge.da_huy_luc or challenge.het_han <= bay_gio:
            raise SigningError(code="otp_het_han", detail="Mã OTP đã hết hạn hoặc đã được sử dụng.")
        if not hmac.compare_digest(_bam(user.pk, challenge.pk, ma), challenge.ma_bam):
            challenge.so_lan_sai += 1
            het_luot = challenge.so_lan_sai >= SO_LAN_SAI_TOI_DA
            if het_luot:
                challenge.da_huy_luc = bay_gio
                challenge.pin_moi_verifier = ""
                challenge.ma_bam = ""
            challenge.save(update_fields=["so_lan_sai", "da_huy_luc", "pin_moi_verifier", "ma_bam"])
            ghi_nhat_ky(user, "signing_pin_otp_challenge", challenge.pk, "OTP_SAI", dia_chi_ip=dia_chi_ip,
                        du_lieu_kem_theo={"so_lan_sai": challenge.so_lan_sai, "het_luot": het_luot})
            loi = SigningError(code="otp_sai", detail=("Mã OTP sai; yêu cầu mã mới." if het_luot else
                                f"Mã OTP không đúng. Còn {SO_LAN_SAI_TOI_DA - challenge.so_lan_sai} lần thử."),
                               fields={"so_lan_con_lai": [0 if het_luot else SO_LAN_SAI_TOI_DA - challenge.so_lan_sai]})
        else:
            verifier = challenge.pin_moi_verifier
            credential = pin.dat_verifier(
                user, verifier, dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"kenh_otp": challenge.kenh},
            )
            challenge.da_dung_luc = bay_gio
            challenge.pin_moi_verifier = ""
            challenge.ma_bam = ""
            challenge.save(update_fields=["da_dung_luc", "pin_moi_verifier", "ma_bam"])
            ghi_nhat_ky(user, "signing_pin_otp_challenge", challenge.pk, "XAC_NHAN_OTP_PIN",
                        dia_chi_ip=dia_chi_ip, du_lieu_kem_theo={"kenh": challenge.kenh})
    if loi:
        raise loi
    return credential


@transaction.atomic
def huy_yeu_cau(user, challenge_id, *, dia_chi_ip=None):
    challenge = SigningPinOtpChallenge.objects.select_for_update().filter(
        pk=challenge_id, nguoi_dung=user, da_dung_luc__isnull=True, da_huy_luc__isnull=True,
    ).first()
    if challenge is None:
        raise SigningError(code="otp_khong_hop_le", detail="Yêu cầu OTP không còn hiệu lực.")
    challenge.da_huy_luc = timezone.now()
    challenge.pin_moi_verifier = ""
    challenge.ma_bam = ""
    challenge.save(update_fields=["da_huy_luc", "pin_moi_verifier", "ma_bam"])
    ghi_nhat_ky(user, "signing_pin_otp_challenge", challenge.pk, "HUY_TAO_PIN", dia_chi_ip=dia_chi_ip,
                du_lieu_kem_theo={"kenh": challenge.kenh})
    return challenge
