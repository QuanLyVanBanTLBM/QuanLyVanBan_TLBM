import base64
import copy
import json
import os
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from documents.confidential_api import canonical, digest, document_message, vault_message
from documents.confidential_models import ConfidentialDocument, ConfidentialEvent, ConfidentialKey


def b64(value):
    return base64.b64encode(value).decode()


def signature(key, message):
    r, s = decode_dss_signature(key.sign(message, ec.ECDSA(hashes.SHA256())))
    return b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


class ConfidentialAcceptanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_superuser("confidential_owner", password="test-only-password")
        cls.recipient = User.objects.create_user("confidential_recipient")
        cls.outsider = User.objects.create_user("confidential_outsider")
        cls.admin = User.objects.create_superuser("confidential_unlisted_admin", password="test-only-password")
        cls.material = {}
        cls.keys = {}
        for user in (cls.owner, cls.recipient, cls.outsider, cls.admin):
            enc = rsa.generate_private_key(public_exponent=65537, key_size=3072)
            sign = ec.generate_private_key(ec.SECP256R1())
            enc_raw = enc.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            sign_raw = sign.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            vault = {"salt": b64(os.urandom(16)), "nonce": b64(os.urandom(12)), "ciphertext": b64(os.urandom(64)),
                     "recovery_nonce": b64(os.urandom(12)), "recovery_ciphertext": b64(os.urandom(64))}
            key = ConfidentialKey.objects.create(user=user, encryption_public_key=b64(enc_raw), signing_public_key=b64(sign_raw),
                fingerprint=digest(enc_raw + sign_raw), vault=vault)
            cls.material[user.pk] = (enc, sign)
            cls.keys[user.pk] = key

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def payload(self):
        doc_id = str(uuid.uuid4())
        owner_key = self.keys[self.owner.pk]
        raw_key, iv = os.urandom(32), os.urandom(12)
        aad = canonical(["document-v1", doc_id, self.owner.pk, owner_key.fingerprint])
        secret = {"title": "UNIQUE_SECRET_TITLE", "number": "UNIQUE_SECRET_NUMBER", "note": "UNIQUE_SECRET_NOTE",
                  "files": [{"name": "UNIQUE_SECRET_NAME.txt", "data": b64(b"UNIQUE_SECRET_FILE")}]}
        data = {"id": doc_id, "nonce": b64(iv), "ciphertext": b64(AESGCM(raw_key).encrypt(iv, canonical(secret), aad)), "envelopes": []}
        from cryptography.hazmat.primitives.asymmetric import padding
        for user in (self.owner, self.recipient):
            wrapped = self.material[user.pk][0].public_key().encrypt(raw_key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=aad))
            data["envelopes"].append({"key_id": self.keys[user.pk].pk, "wrapped_key": b64(wrapped)})
        data["signature"] = signature(self.material[self.owner.pk][1], document_message(doc_id, self.owner.pk,
            owner_key.fingerprint, data["nonce"], data["ciphertext"], data["envelopes"]))
        return data

    def create_document(self):
        data = self.payload()
        result = self.client.post("/api/confidential/documents/", data, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        return data

    def test_only_opaque_transport_and_database_fields(self):
        data = self.create_document()
        row = ConfidentialDocument.objects.get(pk=data["id"])
        for marker in ["UNIQUE_SECRET_TITLE", "UNIQUE_SECRET_NAME", "UNIQUE_SECRET_NOTE", "UNIQUE_SECRET_FILE"]:
            self.assertNotIn(marker, json.dumps(data))
            self.assertNotIn(marker, row.ciphertext)
        self.assertFalse(hasattr(row, "trich_yeu"))
        self.assertFalse(hasattr(row, "file"))
        self.assertEqual(ConfidentialEvent.objects.filter(action="CREATE").count(), 1)

    def test_recipient_and_creator_get_ciphertext_unlisted_admin_gets_same_404(self):
        data = self.create_document()
        for user in (self.owner, self.recipient):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(f'/api/confidential/documents/{data["id"]}/').status_code, 200)
            self.assertEqual(self.client.get('/api/confidential/documents/').data["count"], 1)
        for user in (self.outsider, self.admin):
            self.client.force_authenticate(user)
            denied = self.client.get(f'/api/confidential/documents/{data["id"]}/')
            absent = self.client.get(f'/api/confidential/documents/{uuid.uuid4()}/')
            self.assertEqual(denied.status_code, 404)
            self.assertEqual(denied.data, absent.data)
            self.assertEqual(self.client.get('/api/confidential/documents/').data["count"], 0)
        self.assertEqual(ConfidentialEvent.objects.filter(action="DENY").count(), 2)

    def test_revoke_is_owner_only_idempotent_and_blocks_future_delivery(self):
        data = self.create_document()
        path = f'/api/confidential/documents/{data["id"]}/revoke/'
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post(path, {"user_id": self.owner.pk}, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(path, {"user_id": self.recipient.pk}, format="json").status_code, 404)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(path, {"user_id": self.owner.pk}, format="json").status_code, 400)
        for _ in range(2):
            self.assertEqual(self.client.post(path, {"user_id": self.recipient.pk}, format="json").status_code, 200)
        self.assertEqual(ConfidentialEvent.objects.filter(action="REVOKE").count(), 1)
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.get(f'/api/confidential/documents/{data["id"]}/').status_code, 404)
        self.client.force_authenticate(self.owner)
        response = self.client.get(f'/api/confidential/documents/{data["id"]}/')
        self.assertEqual(response.status_code, 200)
        # Original signed envelope retained; remaining recipients can still verify signature.
        self.assertEqual(len(response.data["envelopes"]), 2)

    def test_creation_rejects_plaintext_fields_and_tampered_signatures(self):
        for extra in [{"trich_yeu": "secret"}, {"files": ["plaintext"]}, {"private_key": "secret"}]:
            self.assertEqual(self.client.post('/api/confidential/documents/', {**self.payload(), **extra}, format="json").status_code, 400)
        data = self.payload()
        for field in ("ciphertext", "nonce", "signature"):
            corrupt = copy.deepcopy(data)
            raw = bytearray(base64.b64decode(corrupt[field])); raw[0] ^= 1; corrupt[field] = b64(raw)
            self.assertEqual(self.client.post('/api/confidential/documents/', corrupt, format="json").status_code, 400)
        self.assertEqual(ConfidentialDocument.objects.count(), 0)

    def test_creator_envelope_duplicates_inactive_and_unknown_keys_rejected(self):
        data = self.payload()
        invalid = [data["envelopes"][1:], data["envelopes"] * 2,
            [{"key_id": 99999, "wrapped_key": b64(os.urandom(384))}],
            [{"key_id": True, "wrapped_key": b64(os.urandom(384))}]]
        for envelopes in invalid:
            self.assertEqual(self.client.post('/api/confidential/documents/', {**data, "envelopes": envelopes}, format="json").status_code, 400)
        self.recipient.is_active = False; self.recipient.save(update_fields=["is_active"])
        self.assertEqual(self.client.post('/api/confidential/documents/', data, format="json").status_code, 400)

    def test_read_only_snapshots_and_creation_permission(self):
        data = self.create_document()
        self.assertEqual(self.client.put(f'/api/confidential/documents/{data["id"]}/', data, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f'/api/confidential/documents/{data["id"]}/').status_code, 405)
        self.assertEqual(self.client.post('/api/confidential/documents/', data, format="json").status_code, 409)
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post('/api/confidential/documents/', self.payload(), format="json").status_code, 403)

    def test_vault_own_only_and_login_cannot_overwrite_or_replace_keys(self):
        mine = self.keys[self.owner.pk]
        self.client.force_authenticate(self.recipient)
        own = self.client.get('/api/confidential/key/').data["key"]
        self.assertEqual(own["user_id"], self.recipient.pk)
        self.assertTrue(all("vault" not in item for item in self.client.get('/api/confidential/directory/').data))
        vault = {**mine.vault, "nonce": b64(os.urandom(12))}
        update = {"vault": vault, "signature": signature(self.material[self.owner.pk][1], vault_message(self.owner.pk, mine.fingerprint, vault))}
        self.assertEqual(self.client.put('/api/confidential/key/', update, format="json").status_code, 400)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.put('/api/confidential/key/', update, format="json").status_code, 200)
        self.assertEqual(self.client.put('/api/confidential/key/', {"vault": vault, "signature": b64(os.urandom(64))}, format="json").status_code, 400)
        registration = {"encryption_public_key": mine.encryption_public_key, "signing_public_key": mine.signing_public_key,
                        **update}
        self.assertEqual(self.client.post('/api/confidential/key/', registration, format="json").status_code, 409)

    def test_locked_and_unauthenticated_accounts(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/confidential/key/').status_code, [401, 403])
        self.outsider.is_active = False; self.outsider.save(update_fields=["is_active"])
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get('/api/confidential/directory/').status_code, 403)

    def test_no_accidental_ordinary_api_or_ai_projection(self):
        data = self.create_document()
        ordinary = self.client.get('/api/documents/?loai=MAT')
        self.assertEqual(ordinary.status_code, 200)
        self.assertNotIn(data["id"], json.dumps(ordinary.data))
        from documents.models import get_document_model
        self.assertIsNot(get_document_model("MAT"), ConfidentialDocument)
        from backend.services.sql_document_source import DOCUMENT_VIEWS, SQL_VIEW_COLUMNS
        self.assertNotIn("confidential", DOCUMENT_VIEWS)
        self.assertFalse(any("confidential" in name for name in SQL_VIEW_COLUMNS))

    def test_malformed_sizes_and_recipients_do_not_crash(self):
        data = self.payload()
        for update in [{"nonce": "bad"}, {"ciphertext": "!!!"}, {"envelopes": None}, {"envelopes": []}, {"id": "not-uuid"}]:
            self.assertEqual(self.client.post('/api/confidential/documents/', {**data, **update}, format="json").status_code, 400)
        self.assertEqual(self.client.post('/api/confidential/documents/', [1], format="json").status_code, 400)
