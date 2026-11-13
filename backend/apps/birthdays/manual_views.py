import hashlib
import json
from datetime import date, timedelta

from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from accounts.models import Employee
from authorization.permissions import is_system_admin

from .models import BirthdayEmailLog, BirthdayEmailSource, BirthdayEmailTemplate
from .services import (
    LEADERSHIP_POSITIONS,
    _birthday_card_data,
    _claim_delivery,
    create_manual_resend_log,
    deliver_claimed_email,
    generate_birthday_card_url,
    is_birthday_on_date,
    other_birthday_logs,
    require_delivery_backend,
)
from .templates_service import (
    LAYOUT_DEFAULTS,
    get_employee_role_category,
    get_template_pool,
    render_email_draft,
    saved_template,
    template_catalog,
    valid_placeholders,
)
from .views import serialize_email_log


PREVIEW_SALT = "birthdays.manual-email-preview"
PREVIEW_MAX_AGE = 15 * 60


class SystemAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return is_system_admin(request.user)


class DraftSerializer(serializers.Serializer):
    layout = serializers.ChoiceField(choices=tuple(LAYOUT_DEFAULTS))
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=6000)

    def validate(self, attrs):
        subject = attrs["subject"]
        if subject.splitlines() != [subject] or not all(
            valid_placeholders(attrs[field]) for field in ("subject", "message")
        ):
            raise serializers.ValidationError("invalidDraft")
        return attrs


class SavedTemplateSerializer(DraftSerializer):
    name = serializers.CharField(max_length=120)


class ManualDraftSerializer(DraftSerializer):
    employee_id = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
    year = serializers.IntegerField(min_value=1900, max_value=9998)
    template_id = serializers.RegexField(r"^(layout:[0-9]{2}|saved:[1-9][0-9]{0,17})\Z")
    preview_token = serializers.CharField(max_length=500, required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        reference = attrs["template_id"]
        if reference.startswith("saved:"):
            exists = BirthdayEmailTemplate.objects.filter(
                pk=int(reference.split(":")[1]), layout=attrs["layout"]
            ).exists()
        else:
            exists = reference == f"layout:{attrs['layout']}"
        if not exists:
            raise serializers.ValidationError("invalidDraft")
        return attrs


class BirthdayEmailResendSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
    sent_date = serializers.DateField()
    recipient = serializers.EmailField(max_length=254, required=False)


class DeliveryProblem(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code = code
        self.status = status
        super().__init__(code)

    def response(self):
        return Response({"error": self.code}, status=self.status)


def _active_birthday_recipients():
    return Employee.objects.filter(
        is_active=True, ngay_sinh__isnull=False,
    ).select_related("chuc_vu", "don_vi")


def _leadership():
    return _active_birthday_recipients().filter(chuc_vu__name__in=LEADERSHIP_POSITIONS)


def _recipient(employee: Employee) -> str:
    email = (employee.email or "").strip()
    try:
        validate_email(email)
    except ValidationError as error:
        raise DeliveryProblem("invalidRecipient") from error
    return email


def _occurrence(employee: Employee, year: int) -> date:
    birth_date = employee.ngay_sinh
    current_year = timezone.localdate().year
    if not max(birth_date.year, current_year - 1) <= year <= current_year + 1:
        raise DeliveryProblem("invalidOccurrence")
    if (birth_date.month, birth_date.day) != (2, 29):
        return birth_date.replace(year=year)
    strategy = getattr(settings, "BIRTHDAY_LEAP_DAY_STRATEGY", "FEB_28")
    first = date(year, 2, 28)
    for offset in range(3):
        candidate = first + timedelta(days=offset)
        if is_birthday_on_date(birth_date, candidate, strategy):
            return candidate
    raise DeliveryProblem("invalidOccurrence")


def _draft_for(employee: Employee, draft: dict, admin_id: int) -> dict:
    recipient = _recipient(employee)
    occurrence = _occurrence(employee, draft["year"])
    data = {**_birthday_card_data(employee), "chuc_danh": (employee.chuc_danh or "").strip()}
    card_url = generate_birthday_card_url(employee, draft["layout"])
    subject, snapshot = render_email_draft(draft, data, card_url)
    if len(subject) > 255 or subject.splitlines() != [subject] or not subject.strip():
        raise DeliveryProblem("invalidDraft")
    fingerprint = hashlib.sha256(json.dumps([
        admin_id, employee.pk, recipient, occurrence.isoformat(), data, subject,
        draft["message"], snapshot["template_version"], card_url.split("#", 1)[0],
    ], sort_keys=True).encode()).hexdigest()
    return {
        "recipient": recipient, "occurrence": occurrence, "subject": subject,
        "snapshot": snapshot, "fingerprint": fingerprint, "card_url": card_url,
    }


def _ready_to_send():
    try:
        require_delivery_backend()
    except ImproperlyConfigured as error:
        raise DeliveryProblem("smtpUnavailable", 503) from error


@api_view(["GET"])
@permission_classes([SystemAdminOnly])
def recipients_api(request):
    query = request.query_params.get("q", "").strip()[:100]
    scope = request.query_params.get("scope", "").strip().lower()
    if query or scope == "all":
        employees = _active_birthday_recipients()
        if query:
            employees = employees.filter(Q(ho_ten__icontains=query) | Q(chuc_vu__name__icontains=query))
    else:
        employees = _leadership()

    recipients_data = []
    for employee in employees.order_by("chuc_vu__display_order", "ho_ten", "pk")[:30]:
        pos_name = employee.chuc_vu.name if employee.chuc_vu else ""
        role_group = get_employee_role_category(pos_name)
        recommended_layouts = get_template_pool(role_group)
        recipients_data.append({
            "id": employee.pk,
            "name": employee.ho_ten,
            "position": pos_name,
            "email": employee.email,
            "role_group": role_group,
            "recommended_layouts": recommended_layouts,
        })

    return Response({
        "recipients": recipients_data,
        "year": timezone.localdate().year,
    })


@api_view(["GET", "POST"])
@permission_classes([SystemAdminOnly])
def templates_api(request):
    if request.method == "GET":
        return Response({"templates": template_catalog()})
    serializer = SavedTemplateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": "invalidDraft"}, status=400)
    template = BirthdayEmailTemplate.objects.create(**serializer.validated_data)
    return Response({"template": saved_template(template)}, status=201)


@api_view(["POST"])
@permission_classes([SystemAdminOnly])
def preview_api(request):
    serializer = ManualDraftSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": "invalidDraft"}, status=400)
    draft = serializer.validated_data
    employee = get_object_or_404(_active_birthday_recipients(), pk=draft["employee_id"])
    try:
        prepared = _draft_for(employee, draft, request.user.pk)
    except DeliveryProblem as error:
        return error.response()
    response = Response({
        "recipient": prepared["recipient"],
        "birthday_date": prepared["occurrence"].isoformat(),
        "subject": prepared["subject"],
        "html": prepared["snapshot"]["html"],
        "card_url": prepared["card_url"],
        "preview_token": signing.dumps(prepared["fingerprint"], salt=PREVIEW_SALT),
    })
    response["Cache-Control"] = "private, no-store"
    return response


@api_view(["POST"])
@permission_classes([SystemAdminOnly])
def send_api(request):
    serializer = ManualDraftSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": "invalidDraft"}, status=400)
    draft = serializer.validated_data
    try:
        fingerprint = signing.loads(
            draft.get("preview_token", ""), salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE,
        )
    except signing.BadSignature:
        return Response({"error": "previewExpired"}, status=409)

    try:
        _ready_to_send()
        with transaction.atomic():
            employee = get_object_or_404(
                _active_birthday_recipients().select_for_update(of=("self",)),
                pk=draft["employee_id"],
            )
            prepared = _draft_for(employee, draft, request.user.pk)
            if fingerprint != prepared["fingerprint"]:
                raise DeliveryProblem("previewExpired", 409)
            if other_birthday_logs(employee.pk, prepared["occurrence"]).exists():
                raise DeliveryProblem("deliveryConflict", 409)
            if BirthdayEmailLog.objects.filter(
                employee=employee,
                sent_date=prepared["occurrence"],
            ).exists():
                raise DeliveryProblem("deliveryConflict", 409)
            log = BirthdayEmailLog.objects.create(
                employee=employee,
                sent_date=prepared["occurrence"],
                recipient_email=prepared["recipient"],
                subject=prepared["subject"],
                delivery_source=BirthdayEmailSource.MANUAL,
            )
            if not _claim_delivery(
                log, prepared["recipient"], prepared["subject"],
                operator=request.user.get_username(), manual_snapshot=prepared["snapshot"],
            ):
                raise DeliveryProblem("deliveryConflict", 409)
    except DeliveryProblem as error:
        return error.response()

    deliver_claimed_email(log)
    return Response({"log": serialize_email_log(log)})


@api_view(["POST"])
@permission_classes([SystemAdminOnly])
def resend_api(request):
    serializer = BirthdayEmailResendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": "invalidRecipient"}, status=400)
    return _send_manual_resend(request, serializer.validated_data)


def _send_manual_resend(request, data):
    try:
        _ready_to_send()
        log, error_code = create_manual_resend_log(
            employee_id=data["employee_id"],
            sent_date=data["sent_date"],
            recipient=data.get("recipient"),
            operator=request.user.get_username(),
        )
    except DeliveryProblem as error:
        return error.response()
    if error_code:
        status_code = {
            "employeeNotFound": 404,
            "resendInProgress": 409,
            "recipientChanged": 409,
            "invalidOccurrence": 400,
            "invalidRecipient": 400,
        }.get(error_code, 400)
        return Response({"error": error_code}, status=status_code)

    deliver_claimed_email(log)
    return Response({"log": serialize_email_log(log)})


@api_view(["POST"])
@permission_classes([SystemAdminOnly])
def retry_api(request, log_id):
    log = get_object_or_404(BirthdayEmailLog.objects.only("employee_id", "sent_date"), pk=log_id)
    payload = {
        "employee_id": log.employee_id,
        "sent_date": log.sent_date.isoformat(),
    }
    if "recipient" in request.data:
        payload["recipient"] = request.data["recipient"]
    serializer = BirthdayEmailResendSerializer(data=payload)
    if not serializer.is_valid():
        return Response({"error": "invalidRecipient"}, status=400)
    return _send_manual_resend(request, serializer.validated_data)
