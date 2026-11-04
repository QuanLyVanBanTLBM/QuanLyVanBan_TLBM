"""
Serializers cho phân hệ Quản lý Cán bộ Nhân viên (CBNV - Issue #24).
Tác giả: Lê Duy Khánh (leduykhanhdevs). Chuyển sang Employee (Custom User Model) theo SQL_Fix4.
"""
from datetime import date
import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers

from organizations.models import DonVi
from .models import (
    MAX_DISPLAY_ORDER,
    Employee,
    EmployeeAssignment,
    EmployeePasswordResetAudit,
    Position,
    vietnam_phone_regex,
)


def validate_employee_birthday(value: date) -> date:
    """Kiểm tra ngày sinh hợp lệ: không ở tương lai và độ tuổi trong khoảng [18, 100]."""
    today = date.today()
    if value > today:
        raise serializers.ValidationError("employees.messages.birthdayInFuture")
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18 or age > 100:
        raise serializers.ValidationError("employees.messages.birthdayOutOfRange")
    return value


SENSITIVE_PERMISSION = "view_full_cbnv"


def user_can_view_sensitive(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_superuser or user.has_perm(SENSITIVE_PERMISSION))



class ChangePasswordSerializer(serializers.Serializer):
    """Serializer xác thực payload đổi mật khẩu."""

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Mật khẩu hiện tại",
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Mật khẩu mới (tối thiểu 8 ký tự)",
    )


class EmployeeAdminPasswordChangeSerializer(serializers.Serializer):
    """Xác thực mật khẩu mới do admin đặt cho một hồ sơ CBNV."""

    reason_code = serializers.ChoiceField(
        choices=EmployeePasswordResetAudit.Reason.choices,
        error_messages={
            "required": "employees.validation.passwordReasonRequired",
            "blank": "employees.validation.passwordReasonRequired",
            "invalid_choice": "employees.validation.passwordReasonInvalid",
        },
    )
    reason_detail = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=500,
        error_messages={
            "max_length": "employees.validation.passwordReasonDetailTooLong",
        },
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        min_length=8,
        max_length=128,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        min_length=8,
        max_length=128,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("employees.messages.passwordMismatch")
        reason_detail = (attrs.get("reason_detail") or "").strip()
        if attrs["reason_code"] == EmployeePasswordResetAudit.Reason.OTHER:
            if not reason_detail:
                raise serializers.ValidationError(
                    {"reason_detail": "employees.validation.passwordReasonDetailRequired"}
                )
            attrs["reason_detail"] = reason_detail
        else:
            attrs["reason_detail"] = None
        try:
            validate_password(attrs["new_password"], user=self.context.get("employee"))
        except DjangoValidationError:
            raise serializers.ValidationError("employees.messages.passwordNotAccepted")
        return attrs


class PositionSerializer(serializers.ModelSerializer):
    """
    Danh mục Chức vụ (accounts_position, Issue #20). Key API trùng tên cột DDL: display_order, name, is_public, note.
    """

    display_order = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_DISPLAY_ORDER,
        error_messages={
            "min_value": "positions.messages.sttInvalid",
            "max_value": "positions.messages.sttTooLarge",
            "invalid": "positions.messages.sttInvalid",
        },
    )
    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "positions.messages.nameRequired",
            "required": "positions.messages.nameRequired",
            "null": "positions.messages.nameRequired",
            "max_length": "positions.messages.nameTooLong",
        },
    )
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # Không đặt default: cập nhật (PUT) thiếu trường này không được âm thầm đổi chức vụ Nội bộ thành Công khai; tạo mới dùng default của model (True).
    is_public = serializers.BooleanField(required=False)

    class Meta:
        model = Position
        fields = ["id", "display_order", "name", "is_public", "note"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        trimmed = " ".join(value.split())
        if not trimmed:
            raise serializers.ValidationError("positions.messages.nameRequired")
        # So khớp bằng casefold ở Python: iexact của SQLite không phân biệt hoa/thường với chữ có dấu.
        others = Position.objects.all()
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if trimmed.casefold() in {n.casefold() for n in others.values_list("name", flat=True)}:
            raise serializers.ValidationError("positions.messages.nameExists")
        return trimmed

    def validate_display_order(self, value):
        duplicated = Position.objects.filter(display_order=value)
        if self.instance is not None:
            duplicated = duplicated.exclude(pk=self.instance.pk)
        if duplicated.exists():
            raise serializers.ValidationError("positions.messages.sttExists")
        return value

    def validate_note(self, value):
        return (value or "").strip()

    def create(self, validated_data):
        if "display_order" in validated_data:
            return super().create(validated_data)
        # Không truyền STT: tự lấy MAX + 1; thử lại nếu hai request cùng lúc chọn trùng số.
        for _ in range(5):
            validated_data["display_order"] = Position.get_next_display_order()
            try:
                with transaction.atomic():
                    return super().create(validated_data)
            except IntegrityError:
                continue
        raise serializers.ValidationError({"display_order": ["positions.messages.sttExists"]})


class GroupSimpleSerializer(serializers.ModelSerializer):
    """Serializer nhóm quyền RBAC."""

    class Meta:
        model = Group
        fields = ["id", "name"]


class EmployeeAssignmentSerializer(serializers.ModelSerializer):
    """Serializer cho phân công phòng ban & chức vụ kiêm nhiệm."""

    don_vi_id = serializers.IntegerField(source="don_vi.id", read_only=True)
    don_vi_ten = serializers.CharField(source="don_vi.ten", read_only=True)
    khoi_ten = serializers.CharField(source="don_vi.khoi.ten", read_only=True)

    chuc_vu_id = serializers.IntegerField(source="chuc_vu.id", read_only=True)
    chuc_vu_ten = serializers.CharField(source="chuc_vu.name", read_only=True)

    class Meta:
        model = EmployeeAssignment
        fields = [
            "id",
            "don_vi_id",
            "don_vi_ten",
            "khoi_ten",
            "chuc_vu_id",
            "chuc_vu_ten",
            "chuc_danh",
            "created_at",
        ]
        read_only_fields = fields


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Hiển thị danh sách và chi tiết CBNV.
    Che năm sinh và ẩn nhóm quyền nếu người xem thiếu quyền accounts.view_full_cbnv.
    """

    don_vi_id = serializers.IntegerField(read_only=True)
    don_vi_ten = serializers.CharField(source="don_vi.ten", read_only=True)
    khoi_ten = serializers.CharField(source="don_vi.khoi.ten", read_only=True)

    chuc_vu_id = serializers.IntegerField(read_only=True)
    chuc_vu_ten = serializers.CharField(source="chuc_vu.name", read_only=True)

    ngay_sinh = serializers.SerializerMethodField()
    ngay_sinh_iso = serializers.SerializerMethodField()
    is_birthday_masked = serializers.SerializerMethodField()

    nhom_quyen = serializers.SerializerMethodField()
    trang_thai_display = serializers.CharField(source="get_trang_thai_display", read_only=True)
    has_sensitive_permission = serializers.SerializerMethodField()
    temporary_password = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "username",
            "email",
            "ho_ten",
            "ngay_sinh",
            "ngay_sinh_iso",
            "is_birthday_masked",
            "don_vi_id",
            "don_vi_ten",
            "khoi_ten",
            "chuc_vu_id",
            "chuc_vu_ten",
            "chuc_danh",
            "sdt",
            "trang_thai",
            "trang_thai_display",
            "is_active",
            "is_public",
            "ghi_chu",
            "nhom_quyen",
            "has_sensitive_permission",
            "temporary_password",
            "assignments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _can_view_sensitive(self, obj=None) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        # Chủ hồ sơ được xem ngày sinh và thông tin cá nhân đầy đủ của chính mình
        if obj is not None and user.id == obj.id:
            return True
        return user_can_view_sensitive(user)

    def get_temporary_password(self, obj):
        return getattr(obj, "raw_temporary_password", None)

    def get_has_sensitive_permission(self, obj) -> bool:
        return self._can_view_sensitive(obj)

    def get_ngay_sinh(self, obj):
        if not obj.ngay_sinh:
            return None
        if self._can_view_sensitive(obj):
            return obj.ngay_sinh.strftime("%d/%m/%Y")
        return obj.ngay_sinh.strftime("%d/%m/----")

    def get_ngay_sinh_iso(self, obj):
        if not obj.ngay_sinh:
            return None
        if self._can_view_sensitive(obj):
            return obj.ngay_sinh.isoformat()
        return None

    def get_is_birthday_masked(self, obj) -> bool:
        return not self._can_view_sensitive(obj)

    def get_nhom_quyen(self, obj):
        if not self._can_view_sensitive(obj):
            return []
        return [{"id": g.id, "name": g.name} for g in obj.groups.all()]

    def get_assignments(self, obj):
        # Dùng assignments đã prefetch để tránh N+1 queries
        assignments = list(obj.assignments.all())
        assignments.sort(key=lambda a: a.id)
        return EmployeeAssignmentSerializer(assignments, many=True).data


# Bảng ánh xạ mã nhóm quyền mặc định theo chức vụ do nhóm trưởng chốt (Issue #24 / PR #211):
# Tra nhóm theo mã ma_nhom_quyen qua authorization.GroupInfo, không tra theo tên nhóm.
POSITION_DEFAULT_GROUP_CODES = {
    # Quản trị viên không tự nhận nhóm nào: nhóm ADMIN chỉ do tài khoản ADMIN hoặc superuser gán thủ công.
    # Ban Giám đốc (BGD)
    "Chủ tịch HĐQT": ["BGD"],
    "Phó Chủ tịch HĐQT": ["BGD"],
    "Tổng Giám đốc": ["BGD"],
    "Lãnh đạo cơ quan": ["BGD"],
    "Phó Tổng Giám đốc điều hành": ["BGD"],
    "Phó Tổng Giám đốc kinh doanh": ["BGD"],
    # Trưởng phòng (TP)
    "Giám đốc Khối": ["TP"],
    "Phó Giám đốc Khối": ["TP"],
    "Giám đốc Vùng": ["TP"],
    "Giám đốc": ["TP"],
    "Phó Giám đốc": ["TP"],
    "Trưởng Ban": ["TP"],
    "Phó Ban": ["TP"],
    "Trưởng Bộ phận": ["TP"],
    "Trưởng phòng": ["TP"],
    "Phó phòng": ["TP"],
    # Chuyên viên (CV)
    "Thành viên HĐQT": ["CV"],
    "Trưởng nhóm": ["CV"],
    "Chuyên viên": ["CV"],
    "Nhân viên": ["CV"],
    "Thành viên": ["CV"],
    # Văn thư (VT)
    "Văn thư": ["VT"],
    # CV + Trợ lý Ban Giám đốc (TLBGD)
    "Trợ lý TGĐ": ["CV", "TLBGD"],
    # CV + Kiểm toán (KT)
    "Kiểm toán viên": ["CV", "KT"],
}


ADMIN_GROUP_CODE = "ADMIN"


def _admin_group_ids():
    from authorization.models import GroupInfo

    return set(GroupInfo.objects.filter(ma_nhom_quyen=ADMIN_GROUP_CODE).values_list("id", flat=True))


def requester_can_grant_admin(request):
    """Chỉ superuser hoặc thành viên nhóm ADMIN mới được gán hoặc gỡ nhóm Quản trị hệ thống."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(id__in=_admin_group_ids()).exists()


def check_admin_group_assignment(request, requested_groups, current_group_ids=()):
    """Từ chối khi người không phải ADMIN làm thay đổi việc CBNV thuộc nhóm ADMIN."""
    admin_ids = _admin_group_ids()
    if not admin_ids or requester_can_grant_admin(request):
        return
    requested_ids = {group.id for group in requested_groups}
    if (requested_ids & admin_ids) != (set(current_group_ids) & admin_ids):
        raise serializers.ValidationError("employees.messages.adminGroupForbidden")


def get_default_groups_for_position(position):
    """
    Tra cứu danh sách auth.models.Group mặc định theo chức vụ qua mã ma_nhom_quyen
    (bảng authorization.GroupInfo).
    - Tra cứu qua GroupInfo.ma_nhom_quyen, lấy các Group tương ứng.
    - Một chức vụ có thể nhận 1 hoặc 2 nhóm (ví dụ: Trợ lý TGĐ -> CV + TLBGD, Kiểm toán viên -> CV + KT).
    - Nhóm chưa tồn tại trong DB thì bỏ qua, không gây lỗi 500.
    """
    if not position:
        return []
    pos_name = getattr(position, "name", "")
    if not pos_name:
        return []
    codes = POSITION_DEFAULT_GROUP_CODES.get(pos_name.strip())
    if not codes:
        return []
    from authorization.models import GroupInfo

    group_ids = list(
        GroupInfo.objects.filter(ma_nhom_quyen__in=codes).values_list("id", flat=True)
    )
    if not group_ids:
        return []
    return list(Group.objects.filter(id__in=group_ids))


class EmployeeCreateSerializer(serializers.Serializer):
    """Thêm mới CBNV kèm tài khoản đăng nhập; không lưu mật khẩu thô, trả mật khẩu tạm một lần."""

    ho_ten = serializers.CharField(
        max_length=150,
        required=True,
        error_messages={
            "required": "employees.validation.nameRequired",
            "blank": "employees.validation.nameRequired",
            "max_length": "employees.messages.nameTooLong",
        },
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "employees.validation.emailRequired",
            "blank": "employees.validation.emailRequired",
            "invalid": "employees.messages.invalidEmail",
        },
    )
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(
        max_length=128, required=False, allow_blank=True, write_only=True
    )
    ngay_sinh = serializers.DateField(
        required=True,
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        error_messages={
            "required": "employees.validation.birthdayRequired",
            "invalid": "employees.import.errors.invalidBirthday",
        },
    )
    don_vi_id = serializers.PrimaryKeyRelatedField(
        queryset=DonVi.objects.all(),
        required=True,
        error_messages={
            "required": "employees.import.errors.unitRequired",
            "does_not_exist": "employees.messages.unitNotFound",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    chuc_vu_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(),
        required=True,
        error_messages={
            "required": "employees.import.errors.positionRequired",
            "does_not_exist": "employees.messages.positionNotFound",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    chuc_danh = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    sdt = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default="", validators=[vietnam_phone_regex]
    )
    nhom_quyen_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "employees.messages.invalidFilterParam",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    def validate_nhom_quyen_ids(self, value):
        check_admin_group_assignment(self.context.get("request"), value)
        return value

    trang_thai = serializers.ChoiceField(
        choices=Employee.Status.choices,
        default=Employee.Status.LAM_VIEC,
        error_messages={"invalid_choice": "employees.messages.invalidFilterParam"},
    )
    is_public = serializers.BooleanField(default=True)
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default="")
    assignments = serializers.ListField(
        child=serializers.DictField(), required=False, default=list, write_only=True
    )

    def validate_ho_ten(self, value):
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("employees.validation.nameRequired")
        if len(trimmed) > 150:
            raise serializers.ValidationError("employees.messages.nameTooLong")
        return trimmed

    def validate_ngay_sinh(self, value):
        return validate_employee_birthday(value)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if get_user_model().objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("employees.messages.emailExists")
        return normalized

    def validate_username(self, value):
        if value:
            trimmed = value.strip()
            if get_user_model().objects.filter(username__iexact=trimmed).exists():
                raise serializers.ValidationError("employees.messages.usernameExists")
            return trimmed
        return value

    def validate_password(self, value):
        if value:
            trimmed = value.strip()
            try:
                validate_password(trimmed)
            except DjangoValidationError as e:
                raise serializers.ValidationError(list(e.messages))
            return trimmed
        return value

    def validate_assignments(self, value):
        if not value:
            return []
        validated = []
        seen_units = set()
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("employees.messages.invalidDataFormat")
            u_id = item.get("don_vi_id")
            p_id = item.get("chuc_vu_id")
            if not u_id:
                raise serializers.ValidationError("employees.messages.unitNotFound")
            if not p_id:
                raise serializers.ValidationError("employees.messages.positionNotFound")
            try:
                u_id = int(u_id)
                p_id = int(p_id)
            except (ValueError, TypeError):
                raise serializers.ValidationError("employees.messages.invalidDataFormat")

            if u_id in seen_units:
                raise serializers.ValidationError("employees.fields.duplicateAssignmentUnit")
            seen_units.add(u_id)

            if not DonVi.objects.filter(id=u_id).exists():
                raise serializers.ValidationError("employees.messages.unitNotFound")
            if not Position.objects.filter(id=p_id).exists():
                raise serializers.ValidationError("employees.messages.positionNotFound")

            chuc_danh_val = str(item.get("chuc_danh") or "").strip()
            if len(chuc_danh_val) > 150:
                raise serializers.ValidationError("employees.messages.assignmentTitleTooLong")

            validated.append({
                "don_vi_id": u_id,
                "chuc_vu_id": p_id,
                "chuc_danh": chuc_danh_val,
            })
        return validated

    def validate(self, attrs):
        primary_unit = attrs.get("don_vi_id")
        assignments = attrs.get("assignments") or []
        if primary_unit and assignments:
            p_unit_id = primary_unit.id if hasattr(primary_unit, "id") else primary_unit
            if any(item["don_vi_id"] == p_unit_id for item in assignments):
                raise serializers.ValidationError({"assignments": ["employees.fields.duplicateAssignmentUnit"]})
        return attrs

    def create(self, validated_data):
        UserModel = get_user_model()
        email = validated_data["email"]
        username = validated_data.get("username")
        if not username:
            local_part = email.split("@")[0]
            candidate = local_part
            idx = 1
            while UserModel.objects.filter(username__iexact=candidate).exists():
                candidate = f"{local_part}{idx}"
                idx += 1
            username = candidate

        raw_password = validated_data.get("password")
        if not raw_password:
            alphabet = string.ascii_letters + string.digits
            raw_password = "".join(secrets.choice(alphabet) for _ in range(10))

        trang_thai = validated_data.get("trang_thai", Employee.Status.LAM_VIEC)
        assignments_data = validated_data.pop("assignments", [])

        with transaction.atomic():
            employee = UserModel.objects.create_user(
                username=username,
                password=raw_password,
                email=email,
                ho_ten=validated_data["ho_ten"],
                ngay_sinh=validated_data["ngay_sinh"],
                don_vi=validated_data["don_vi_id"],
                chuc_vu=validated_data["chuc_vu_id"],
                chuc_danh=validated_data.get("chuc_danh", ""),
                sdt=validated_data.get("sdt", ""),
                trang_thai=trang_thai,
                is_active=(trang_thai != Employee.Status.NGHI_VIEC),
                is_public=validated_data.get("is_public", True),
                ghi_chu=validated_data.get("ghi_chu", ""),
            )
            groups = validated_data.get("nhom_quyen_ids")
            if groups:
                employee.groups.set(groups)
            else:
                default_groups = get_default_groups_for_position(employee.chuc_vu)
                if default_groups:
                    employee.groups.set(default_groups)

            for item in assignments_data:
                EmployeeAssignment.objects.create(
                    employee=employee,
                    don_vi_id=item["don_vi_id"],
                    chuc_vu_id=item["chuc_vu_id"],
                    chuc_danh=item.get("chuc_danh", ""),
                )

            employee.raw_temporary_password = raw_password
            return employee


class EmployeeUpdateSerializer(serializers.Serializer):
    """Cập nhật thông tin CBNV."""

    ho_ten = serializers.CharField(
        max_length=150,
        required=False,
        error_messages={
            "blank": "employees.validation.nameRequired",
            "max_length": "employees.messages.nameTooLong",
        },
    )
    email = serializers.EmailField(
        required=False,
        error_messages={
            "blank": "employees.validation.emailRequired",
            "invalid": "employees.messages.invalidEmail",
        },
    )
    ngay_sinh = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        error_messages={
            "invalid": "employees.import.errors.invalidBirthday",
        },
    )
    don_vi_id = serializers.PrimaryKeyRelatedField(
        queryset=DonVi.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "employees.messages.unitNotFound",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    chuc_vu_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "employees.messages.positionNotFound",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    chuc_danh = serializers.CharField(max_length=150, required=False, allow_blank=True)
    sdt = serializers.CharField(
        max_length=20, required=False, allow_blank=True, validators=[vietnam_phone_regex]
    )
    nhom_quyen_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "employees.messages.invalidFilterParam",
            "incorrect_type": "employees.messages.invalidFilterParam",
        },
    )
    def validate_nhom_quyen_ids(self, value):
        current = self.instance.groups.values_list("id", flat=True) if self.instance else ()
        check_admin_group_assignment(self.context.get("request"), value, current)
        return value

    trang_thai = serializers.ChoiceField(
        choices=Employee.Status.choices,
        required=False,
        error_messages={"invalid_choice": "employees.messages.invalidFilterParam"},
    )
    is_active = serializers.BooleanField(
        required=False,
        error_messages={"invalid": "employees.messages.invalidDataFormat"},
    )
    is_public = serializers.BooleanField(required=False)
    ghi_chu = serializers.CharField(required=False, allow_blank=True)
    assignments = serializers.ListField(
        child=serializers.DictField(), required=False, write_only=True
    )

    def validate_ho_ten(self, value):
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("employees.validation.nameRequired")
        if len(trimmed) > 150:
            raise serializers.ValidationError("employees.messages.nameTooLong")
        return trimmed

    def validate_ngay_sinh(self, value):
        if value is None:
            return value
        return validate_employee_birthday(value)

    def validate_email(self, value):
        normalized = value.strip().lower()
        duplicated = get_user_model().objects.filter(email__iexact=normalized).exclude(pk=self.instance.pk)
        if duplicated.exists():
            raise serializers.ValidationError("employees.messages.emailExists")
        return normalized

    def validate_assignments(self, value):
        if value is None:
            return None
        validated = []
        seen_units = set()
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("employees.messages.invalidDataFormat")
            u_id = item.get("don_vi_id")
            p_id = item.get("chuc_vu_id")
            if not u_id:
                raise serializers.ValidationError("employees.messages.unitNotFound")
            if not p_id:
                raise serializers.ValidationError("employees.messages.positionNotFound")
            try:
                u_id = int(u_id)
                p_id = int(p_id)
            except (ValueError, TypeError):
                raise serializers.ValidationError("employees.messages.invalidDataFormat")

            if u_id in seen_units:
                raise serializers.ValidationError("employees.fields.duplicateAssignmentUnit")
            seen_units.add(u_id)

            if not DonVi.objects.filter(id=u_id).exists():
                raise serializers.ValidationError("employees.messages.unitNotFound")
            if not Position.objects.filter(id=p_id).exists():
                raise serializers.ValidationError("employees.messages.positionNotFound")

            chuc_danh_val = str(item.get("chuc_danh") or "").strip()
            if len(chuc_danh_val) > 150:
                raise serializers.ValidationError("employees.messages.assignmentTitleTooLong")

            validated.append({
                "don_vi_id": u_id,
                "chuc_vu_id": p_id,
                "chuc_danh": chuc_danh_val,
            })
        return validated

    def validate(self, attrs):
        primary_unit = attrs.get("don_vi_id")
        if primary_unit is None and self.instance:
            primary_unit = self.instance.don_vi_id
        elif primary_unit and hasattr(primary_unit, "id"):
            primary_unit = primary_unit.id

        assignments = attrs.get("assignments")
        if primary_unit and assignments:
            if any(item["don_vi_id"] == primary_unit for item in assignments):
                raise serializers.ValidationError({"assignments": ["employees.fields.duplicateAssignmentUnit"]})
        return attrs

    def update(self, instance, validated_data):
        with transaction.atomic():
            if "ho_ten" in validated_data:
                instance.ho_ten = validated_data["ho_ten"].strip()
            if "email" in validated_data:
                instance.email = validated_data["email"]
            if "ngay_sinh" in validated_data:
                instance.ngay_sinh = validated_data["ngay_sinh"]
            if "don_vi_id" in validated_data:
                instance.don_vi = validated_data["don_vi_id"]
            if "chuc_vu_id" in validated_data:
                instance.chuc_vu = validated_data["chuc_vu_id"]
            for field in ("chuc_danh", "sdt", "is_public", "ghi_chu"):
                if field in validated_data:
                    setattr(instance, field, validated_data[field])

            if "is_active" in validated_data:
                instance.is_active = validated_data["is_active"]
                if not instance.is_active and "trang_thai" not in validated_data:
                    instance.trang_thai = Employee.Status.NGHI_VIEC
                elif instance.is_active and "trang_thai" not in validated_data and instance.trang_thai == Employee.Status.NGHI_VIEC:
                    instance.trang_thai = Employee.Status.LAM_VIEC

            if "trang_thai" in validated_data:
                new_status = validated_data["trang_thai"]
                if new_status == Employee.Status.LAM_VIEC and instance.trang_thai == Employee.Status.NGHI_VIEC:
                    if "is_active" not in validated_data:
                        instance.is_active = True
                elif new_status == Employee.Status.NGHI_VIEC:
                    if "is_active" not in validated_data:
                        instance.is_active = False
                instance.trang_thai = new_status

            instance.save()

            if "nhom_quyen_ids" in validated_data:
                instance.groups.set(validated_data["nhom_quyen_ids"])

            if "assignments" in validated_data:
                instance.assignments.all().delete()
                for item in validated_data["assignments"]:
                    EmployeeAssignment.objects.create(
                        employee=instance,
                        don_vi_id=item["don_vi_id"],
                        chuc_vu_id=item["chuc_vu_id"],
                        chuc_danh=item.get("chuc_danh", ""),
                    )

            return instance
