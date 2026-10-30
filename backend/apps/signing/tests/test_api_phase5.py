import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Position
from signing import enums
from signing.models import SigningAuditLog, SigningKey, SigningProcess
from signing.permissions import co_quyen

from .helpers import cap_quyen, tao_chuc_vu, them_vao_nhom_quan_tri

User = get_user_model()

BASE = "/api/v1/signing"


def new_keypair():
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return private, base64.b64encode(raw).decode()


class ApiBase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.position = Position.objects.create(
            display_order=Position.get_next_display_order(), name="Trưởng phòng"
        )
        # u1: quản lý quy trình và ký; u2: chỉ xem và ký
        cap_quyen(self.u1, "view_trinhky", "manage_signing_process", "sign_trinhky")
        cap_quyen(self.u2, "view_trinhky", "sign_trinhky")
        self.c1, self.c2, self.anon = APIClient(), APIClient(), APIClient()
        self.c1.force_authenticate(self.u1)
        self.c2.force_authenticate(self.u2)
        self.chuc_vu = tao_chuc_vu()


class ProcessApiTests(ApiBase):
    def payload(self, ma="QT1", **kw):
        data = {
            "ma_quy_trinh": ma, "ten_quy_trinh": "Quy trình duyệt", "pham_vi": "CONG_TY",
            "cap_ky": [
                {"cap_ky": 1, "ten_cap_ky": "Trưởng phòng", "thu_tu": 1,
                 "nguoi_ky": [{"nguoi_ky": self.u2.pk, "thu_tu": 1}]},
                {"cap_ky": 2, "ten_cap_ky": "Giám đốc", "thu_tu": 2,
                 "nguoi_ky": [{"chuc_vu_id": self.position.pk, "thu_tu": 1}]},
            ],
        }
        data.update(kw)
        return data

    def create(self, ma="QT1", **kw):
        response = self.c1.post(f"{BASE}/quy-trinh/", self.payload(ma, **kw), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_requires_authentication(self):
        for method, url in [("get", "/quy-trinh/"), ("post", "/quy-trinh/"), ("get", "/khoa/"), ("post", "/khoa/")]:
            self.assertEqual(getattr(self.anon, method)(f"{BASE}{url}").status_code, 401, url)

    def test_create_returns_nested_structure(self):
        body = self.create()
        self.assertEqual(body["trang_thai"], "NHAP")
        self.assertEqual(body["phien_ban"], 1)
        self.assertEqual(body["create_by"], self.u1.pk)
        self.assertEqual(set(body), {  # Phase 6c: không còn trường cách thức ký
            "id", "ma_quy_trinh", "ten_quy_trinh", "mo_ta", "phien_ban", "trang_thai", "pham_vi",
            "don_vi_ap_dung_id", "ten_don_vi_ap_dung", "cau_hinh_nhac_han", "create_by", "created_at", "update_by",
            "update_at", "cap_ky", "so_ho_so",
        })
        self.assertEqual([c["thu_tu"] for c in body["cap_ky"]], [1, 2])
        self.assertEqual(body["cap_ky"][1]["nguoi_ky"][0]["vai_tro_ky"], "KY_CHINH")

    def test_validation_errors_grouped_by_field(self):
        response = self.c1.post(f"{BASE}/quy-trinh/", {"ten_quy_trinh": "x", "pham_vi": "SAI"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "du_lieu_khong_hop_le")
        self.assertEqual(set(response.data["fields"]), {"ma_quy_trinh", "pham_vi"})

    def test_signer_person_and_position_together_rejected(self):
        data = self.payload("QT9")
        data["cap_ky"][0]["nguoi_ky"][0]["chuc_vu_id"] = self.position.pk
        response = self.c1.post(f"{BASE}/quy-trinh/", data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "nguoi_ky_hoac_chuc_vu")
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT9").exists())

    def test_duplicate_code_conflict(self):
        self.create()
        response = self.c1.post(f"{BASE}/quy-trinh/", self.payload(), format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "quy_trinh_trung_ma")

    def test_missing_reference_ids_return_400_without_writes_or_audit(self):
        admin = User.objects.create_superuser("signing_reference_admin")
        client = APIClient()
        client.force_authenticate(admin)

        missing_position = self.payload("QT_MISSING_POSITION")
        missing_position["cap_ky"][1]["nguoi_ky"][0]["chuc_vu_id"] = 987654321
        missing_step_unit = self.payload("QT_MISSING_STEP_UNIT")
        missing_step_unit["cap_ky"][0]["don_vi_id"] = 987654321
        missing_process_unit = self.payload("QT_MISSING_PROCESS_UNIT", pham_vi="PHONG_BAN")
        missing_process_unit["don_vi_ap_dung_id"] = 987654321
        cases = (
            (
                "QT_MISSING_POSITION",
                missing_position,
                "chuc_vu_id",
                "chuc_vu_khong_ton_tai",
                "Chức vụ không tồn tại.",
            ),
            ("QT_MISSING_STEP_UNIT", missing_step_unit, "don_vi_id", "don_vi_khong_ton_tai", "Đơn vị không tồn tại."),
            (
                "QT_MISSING_PROCESS_UNIT",
                missing_process_unit,
                "don_vi_ap_dung_id",
                "don_vi_khong_ton_tai",
                "Đơn vị không tồn tại.",
            ),
        )

        for ma, payload, field, expected_code, message in cases:
            with self.subTest(field=field):
                response = client.post(f"{BASE}/quy-trinh/", payload, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(response.data["code"], expected_code)
                self.assertEqual(response.data["fields"], {field: [message]})
                self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh=ma).exists())
                self.assertFalse(SigningAuditLog.objects.filter(loai_doi_tuong="signing_process").exists())

    def test_non_manager_sees_only_active_processes(self):
        body = self.create()
        self.assertEqual(self.c2.get(f"{BASE}/quy-trinh/{body['id']}/").status_code, 404)
        self.assertEqual(len(self.c2.get(f"{BASE}/quy-trinh/").data), 0)
        self.assertEqual(self.c1.get(f"{BASE}/quy-trinh/{body['id']}/").status_code, 200)
        self.assertEqual(self.c1.post(f"{BASE}/quy-trinh/{body['id']}/kich-hoat/").status_code, 200)
        # quy trình hoạt động: người có view_trinhky xem được
        self.assertEqual(self.c2.get(f"{BASE}/quy-trinh/{body['id']}/").status_code, 200)
        self.assertEqual(len(self.c2.get(f"{BASE}/quy-trinh/").data), 1)

    def test_non_manager_cannot_change_state(self):
        body = self.create()
        self.c1.post(f"{BASE}/quy-trinh/{body['id']}/kich-hoat/")
        for action in ("ngung", "nhan-ban"):
            response = self.c2.post(f"{BASE}/quy-trinh/{body['id']}/{action}/")
            self.assertEqual(response.status_code, 403, action)
            self.assertEqual(response.data["code"], "khong_co_quyen")
            self.assertEqual(response.data["fields"], {"quyen": ["manage_signing_process"]})
        self.assertEqual(SigningProcess.objects.get(pk=body["id"]).trang_thai, enums.TrangThaiQuyTrinh.HOAT_DONG)

    def test_lifecycle_activate_deactivate_clone(self):
        pid = self.create()["id"]
        r = self.c1.post(f"{BASE}/quy-trinh/{pid}/kich-hoat/")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "HOAT_DONG"))
        self.assertEqual(self.c1.post(f"{BASE}/quy-trinh/{pid}/kich-hoat/").status_code, 409)
        clone = self.c1.post(f"{BASE}/quy-trinh/{pid}/nhan-ban/")
        self.assertEqual((clone.status_code, clone.data["phien_ban"], clone.data["trang_thai"]), (201, 2, "NHAP"))
        self.assertEqual(len(clone.data["cap_ky"]), 2)
        r = self.c1.post(f"{BASE}/quy-trinh/{pid}/ngung/")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "NGUNG"))

    def test_activation_error_has_stable_code(self):
        pid = self.create("QT5", cap_ky=[])["id"]
        response = self.c1.post(f"{BASE}/quy-trinh/{pid}/kich-hoat/")
        self.assertEqual((response.status_code, response.data["code"]), (400, "quy_trinh_khong_co_cap"))

    def test_status_filter(self):
        a = self.create("A")["id"]
        self.create("B")
        self.c1.post(f"{BASE}/quy-trinh/{a}/kich-hoat/")
        rows = self.c1.get(f"{BASE}/quy-trinh/", {"trang_thai": "HOAT_DONG"}).data
        self.assertEqual([r["ma_quy_trinh"] for r in rows], ["A"])

    def test_unknown_process_404(self):
        self.assertEqual(self.c1.get(f"{BASE}/quy-trinh/99999/").status_code, 404)


class KeyApiTests(ApiBase):
    def register(self, client=None, ma="k1"):
        private, public = new_keypair()
        response = (client or self.c1).post(f"{BASE}/khoa/", {
            "ma_khoa": ma, "khoa_cong_khai": public, "ngay_hieu_luc": "2026-10-01T00:00:00Z",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return private, response.data

    def prove(self, private, key_id, client=None):
        client = client or self.c1
        challenge = client.get(f"{BASE}/khoa/{key_id}/thach-thuc/").data["thach_thuc"]
        signature = base64.b64encode(private.sign(challenge.encode())).decode()
        return client.post(f"{BASE}/khoa/{key_id}/xac-minh/", {"chu_ky_so": signature}, format="json")

    def test_full_lifecycle(self):
        private, key = self.register()
        self.assertEqual(key["trang_thai"], "CHO_KICH_HOAT")
        self.assertEqual(self.c1.post(f"{BASE}/khoa/{key['id']}/kich-hoat/").data["code"], "khoa_chua_xac_minh_so_huu")
        self.assertEqual(self.prove(private, key["id"]).status_code, 200)
        r = self.c1.post(f"{BASE}/khoa/{key['id']}/kich-hoat/")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "HOAT_DONG"))
        r = self.c1.post(f"{BASE}/khoa/{key['id']}/thu-hoi/", {"ly_do": "Mất thiết bị"}, format="json")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "THU_HOI"))

    def test_bad_proof_rejected(self):
        _, key = self.register()
        other, _ = new_keypair()
        response = self.prove(other, key["id"])
        self.assertEqual((response.status_code, response.data["code"]), (400, "chung_minh_so_huu_that_bai"))

    def test_invalid_public_key_rejected(self):
        response = self.c1.post(f"{BASE}/khoa/", {
            "ma_khoa": "k", "khoa_cong_khai": "abc", "ngay_hieu_luc": "2026-10-01T00:00:00Z",
        }, format="json")
        self.assertEqual((response.status_code, response.data["code"]), (400, "khoa_cong_khai_khong_hop_le"))

    def test_keys_of_other_users_are_invisible(self):
        private, key = self.register()
        self.assertEqual(len(self.c2.get(f"{BASE}/khoa/").data), 0)
        for method, path, body in [
            ("get", "thach-thuc", None), ("post", "xac-minh", {"chu_ky_so": "x"}),
            ("post", "kich-hoat", None), ("post", "thu-hoi", {"ly_do": "x"}),
            ("post", "xoay-vong", {"khoa_moi": key["id"]}),
        ]:
            response = getattr(self.c2, method)(f"{BASE}/khoa/{key['id']}/{path}/", body, format="json")
            self.assertEqual(response.status_code, 404, path)
        self.assertEqual(SigningKey.objects.get(pk=key["id"]).trang_thai, enums.TrangThaiKhoa.CHO_KICH_HOAT)

    def test_rotation(self):
        p1, k1 = self.register(ma="k1")
        self.prove(p1, k1["id"])
        self.c1.post(f"{BASE}/khoa/{k1['id']}/kich-hoat/")
        p2, k2 = self.register(ma="k2")
        self.prove(p2, k2["id"])
        blocked = self.c1.post(f"{BASE}/khoa/{k2['id']}/kich-hoat/")
        self.assertEqual((blocked.status_code, blocked.data["code"]), (409, "da_co_khoa_hoat_dong"))
        r = self.c1.post(f"{BASE}/khoa/{k1['id']}/xoay-vong/", {"khoa_moi": k2["id"]}, format="json")
        self.assertEqual((r.status_code, r.data["id"], r.data["trang_thai"]), (200, k2["id"], "HOAT_DONG"))
        states = {k["ma_khoa"]: k["trang_thai"] for k in self.c1.get(f"{BASE}/khoa/").data}
        self.assertEqual(states, {"k1": "DA_XOAY_VONG", "k2": "HOAT_DONG"})

    def test_revoke_requires_reason(self):
        _, key = self.register()
        response = self.c1.post(f"{BASE}/khoa/{key['id']}/thu-hoi/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("ly_do", response.data["fields"])

    def test_response_never_contains_private_material(self):
        _, key = self.register()
        self.assertFalse([k for k in key if "rieng" in k or "private" in k or "bi_mat" in k])

    def test_audit_log_records_client_ip(self):
        _, key = self.register()
        entry = SigningAuditLog.objects.get(hanh_dong="DANG_KY_KHOA", ma_doi_tuong=key["id"])
        self.assertEqual(entry.dia_chi_ip, "127.0.0.1")
        self.assertEqual(entry.nguoi_thuc_hien, self.u1)


class PermissionApiTests(ApiBase):
    """Phase 6b (issue #64): kiểm quyền theo codename của DDL, không chỉ kiểm đăng nhập."""

    def setUp(self):
        super().setUp()
        self.u3 = User.objects.create_user("u3")  # không có quyền nào
        self.c3 = APIClient()
        self.c3.force_authenticate(self.u3)
        self.process = self.c1.post(f"{BASE}/quy-trinh/", ProcessApiTests.payload(self), format="json").data

    def test_user_without_permissions_cannot_create_or_activate_process(self):
        r = self.c3.post(f"{BASE}/quy-trinh/", ProcessApiTests.payload(self, "QT3"), format="json")
        self.assertEqual((r.status_code, r.data["code"]), (403, "khong_co_quyen"))
        self.assertFalse(SigningProcess.objects.filter(ma_quy_trinh="QT3").exists())
        r = self.c3.post(f"{BASE}/quy-trinh/{self.process['id']}/kich-hoat/")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(SigningProcess.objects.get(pk=self.process["id"]).trang_thai, enums.TrangThaiQuyTrinh.NHAP)

    def test_view_permission_required_to_read_processes(self):
        self.assertEqual(self.c3.get(f"{BASE}/quy-trinh/").status_code, 403)
        self.assertEqual(self.c3.get(f"{BASE}/quy-trinh/{self.process['id']}/").status_code, 403)

    def test_any_manager_can_manage_process_of_other_manager(self):
        cap_quyen(self.u3, "manage_signing_process")
        self.assertEqual(len(self.c3.get(f"{BASE}/quy-trinh/").data), 1)  # thấy cả bản NHAP
        r = self.c3.post(f"{BASE}/quy-trinh/{self.process['id']}/kich-hoat/")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "HOAT_DONG"))

    def test_permission_through_group(self):
        group = Group.objects.create(name="Quản trị trình ký")
        group.permissions.add(Permission.objects.get(codename="manage_signing_process"))
        self.u3.groups.add(group)
        them_vao_nhom_quan_tri(self.u3)
        r = self.c3.post(f"{BASE}/quy-trinh/", ProcessApiTests.payload(self, "QT4"), format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_superuser_allowed_without_explicit_permission(self):
        admin = User.objects.create_superuser("signing_superuser_test")
        client = APIClient()
        client.force_authenticate(admin)
        self.assertEqual(client.post(f"{BASE}/quy-trinh/{self.process['id']}/kich-hoat/").status_code, 200)

    def test_inactive_user_has_no_permission(self):
        self.u1.is_active = False
        self.u1.save(update_fields=["is_active"])
        self.assertFalse(co_quyen(self.u1, "manage_signing_process"))

    def test_sign_permission_required_for_key_registration_and_pin(self):
        _, public = new_keypair()
        r = self.c3.post(f"{BASE}/khoa/", {
            "ma_khoa": "k3", "khoa_cong_khai": public, "ngay_hieu_luc": "2026-10-01T00:00:00Z",
        }, format="json")
        self.assertEqual((r.status_code, r.data["fields"]), (403, {"quyen": ["sign_trinhky"]}))
        self.assertFalse(SigningKey.objects.filter(nguoi_so_huu=self.u3).exists())

    def test_revoke_own_key_allowed_after_sign_permission_removed(self):
        cap_quyen(self.u3, "sign_trinhky")
        _, public = new_keypair()
        key = self.c3.post(f"{BASE}/khoa/", {
            "ma_khoa": "k3", "khoa_cong_khai": public, "ngay_hieu_luc": "2026-10-01T00:00:00Z",
        }, format="json").data
        self.u3.user_permissions.clear()
        u3 = User.objects.get(pk=self.u3.pk)  # bỏ cache quyền của backend
        client = APIClient()
        client.force_authenticate(u3)
        self.assertEqual(client.post(f"{BASE}/khoa/{key['id']}/kich-hoat/").status_code, 403)
        self.assertEqual(len(client.get(f"{BASE}/khoa/").data), 1)
        r = client.post(f"{BASE}/khoa/{key['id']}/thu-hoi/", {"ly_do": "Chuyển công tác"}, format="json")
        self.assertEqual((r.status_code, r.data["trang_thai"]), (200, "THU_HOI"))

