"""Opaque E2EE transport. Crypto here verifies public signatures, never decrypts."""
import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .confidential_models import ConfidentialDocument, ConfidentialEvent, ConfidentialGrant, ConfidentialKey

MAX_CIPHERTEXT = 16 * 1024 * 1024


def encoded_bytes(value, size=None, maximum=MAX_CIPHERTEXT):
    if not isinstance(value, str) or len(value) > (maximum + 2) // 3 * 4:
        raise ValidationError("confidential.invalidPayload")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ValidationError("confidential.invalidPayload")
    if not raw or len(raw) > maximum or (size is not None and len(raw) != size):
        raise ValidationError("confidential.invalidPayload")
    return raw


def canonical(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def public_keys(encryption, signing):
    try:
        enc_raw = encoded_bytes(encryption, maximum=1024)
        sign_raw = encoded_bytes(signing, maximum=256)
        enc = serialization.load_der_public_key(enc_raw)
        sign = serialization.load_der_public_key(sign_raw)
        if not isinstance(enc, rsa.RSAPublicKey) or enc.key_size != 3072 or enc.public_numbers().e != 65537:
            raise ValueError()
        if not isinstance(sign, ec.EllipticCurvePublicKey) or not isinstance(sign.curve, ec.SECP256R1):
            raise ValueError()
        return digest(enc_raw + sign_raw)
    except (ValueError, TypeError):
        raise ValidationError("confidential.invalidKey")


def verify_signature(signing_key, signature, message):
    raw = encoded_bytes(signature, size=64, maximum=64)
    try:
        key = serialization.load_der_public_key(encoded_bytes(signing_key, maximum=256))
        der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        key.verify(der, message, ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError):
        raise ValidationError("confidential.invalidSignature")


VAULT_FIELDS = {"salt", "nonce", "ciphertext", "recovery_nonce", "recovery_ciphertext"}


def validated_vault(value):
    if not isinstance(value, dict) or set(value) != VAULT_FIELDS:
        raise ValidationError("confidential.invalidVault")
    encoded_bytes(value["salt"], size=16, maximum=16)
    for field in ("nonce", "recovery_nonce"):
        encoded_bytes(value[field], size=12, maximum=12)
    for field in ("ciphertext", "recovery_ciphertext"):
        encoded_bytes(value[field], maximum=8192)
    return value


def vault_message(user_id, fingerprint, vault):
    return canonical(["vault-v1", user_id, fingerprint, *[vault[k] for k in sorted(VAULT_FIELDS)]])


def document_message(document_id, author_id, fingerprint, nonce, ciphertext, envelopes):
    return canonical(["document-v1", str(document_id), author_id, fingerprint, nonce,
                      digest(encoded_bytes(ciphertext)),
                      [[e["key_id"], e["wrapped_key"]] for e in sorted(envelopes, key=lambda e: e["key_id"])]])


class BoundedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        raw = stream.read(24 * 1024 * 1024 + 1)
        if len(raw) > 24 * 1024 * 1024:
            raise ParseError("confidential.tooLarge")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ParseError("confidential.invalidPayload")


class ConfidentialAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [BoundedJSONParser]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_active:
            raise PermissionDenied("confidential.inactive")


def key_public(key):
    return {"id": key.pk, "user_id": key.user_id, "username": key.user.username,
            "encryption_public_key": key.encryption_public_key, "signing_public_key": key.signing_public_key,
            "fingerprint": key.fingerprint}


class ConfidentialKeyView(ConfidentialAPIView):
    def get(self, request):
        key = ConfidentialKey.objects.filter(user=request.user).first()
        return Response({"user_id": request.user.pk,
                         "can_create": request.user.is_superuser or request.user.has_perm("create_confidential_document"),
                         "key": {**key_public(key), "vault": key.vault} if key else None})

    def post(self, request):
        data = request.data
        if not isinstance(data, dict) or set(data) != {"encryption_public_key", "signing_public_key", "vault", "signature"}:
            raise ValidationError("confidential.invalidPayload")
        fingerprint = public_keys(data["encryption_public_key"], data["signing_public_key"])
        vault = validated_vault(data["vault"])
        verify_signature(data["signing_public_key"], data["signature"], vault_message(request.user.pk, fingerprint, vault))
        try:
            with transaction.atomic():
                key = ConfidentialKey.objects.create(user=request.user, fingerprint=fingerprint, vault=vault,
                    encryption_public_key=data["encryption_public_key"], signing_public_key=data["signing_public_key"])
        except IntegrityError:
            return Response({"detail": "confidential.keyExists"}, status=status.HTTP_409_CONFLICT)
        return Response(key_public(key), status=status.HTTP_201_CREATED)

    def put(self, request):
        # Recovery/password change retains identity. Login alone cannot replace keys or vault.
        key = get_object_or_404(ConfidentialKey, user=request.user)
        if not isinstance(request.data, dict) or set(request.data) != {"vault", "signature"}:
            raise ValidationError("confidential.invalidPayload")
        vault = validated_vault(request.data["vault"])
        verify_signature(key.signing_public_key, request.data["signature"], vault_message(request.user.pk, key.fingerprint, vault))
        key.vault = vault
        key.save(update_fields=["vault"])
        return Response({"ok": True})


class ConfidentialDirectoryView(ConfidentialAPIView):
    def get(self, request):
        # Public keys only. Vault backups are never included in the directory.
        keys = ConfidentialKey.objects.filter(user__is_active=True).select_related("user").order_by("user_id")
        return Response([key_public(key) for key in keys])


def summary(doc):
    return {"id": str(doc.pk), "author_id": doc.author_key.user_id,
            "author_username": doc.author_key.user.username, "author_fingerprint": doc.author_key.fingerprint,
            "created_at": doc.created_at.isoformat()}


class ConfidentialDocumentView(ConfidentialAPIView):
    def get(self, request):
        qs = ConfidentialDocument.objects.visible_to(request.user).select_related("author_key__user").defer("ciphertext")
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([summary(doc) for doc in page])

    def post(self, request):
        if not (request.user.is_superuser or request.user.has_perm("create_confidential_document")):
            raise PermissionDenied("confidential.cannotCreate")
        data = request.data
        if not isinstance(data, dict) or set(data) != {"id", "nonce", "ciphertext", "envelopes", "signature"}:
            raise ValidationError("confidential.invalidPayload")
        import uuid
        try:
            doc_id = uuid.UUID(data["id"])
        except (ValueError, TypeError, AttributeError):
            raise ValidationError("confidential.invalidPayload")
        if str(doc_id) != data["id"]:
            raise ValidationError("confidential.invalidPayload")
        encoded_bytes(data["nonce"], size=12, maximum=12)
        if len(encoded_bytes(data["ciphertext"])) < 16:
            raise ValidationError("confidential.invalidPayload")
        envelopes = data["envelopes"]
        if not isinstance(envelopes, list) or not 1 <= len(envelopes) <= 100:
            raise ValidationError("confidential.invalidRecipients")
        ids = []
        for item in envelopes:
            if not isinstance(item, dict) or set(item) != {"key_id", "wrapped_key"} or type(item["key_id"]) is not int:
                raise ValidationError("confidential.invalidRecipients")
            encoded_bytes(item["wrapped_key"], size=384, maximum=384)
            ids.append(item["key_id"])
        keys = {key.pk: key for key in ConfidentialKey.objects.filter(pk__in=ids, user__is_active=True)}
        if len(set(ids)) != len(ids) or len(keys) != len(ids):
            raise ValidationError("confidential.invalidRecipients")
        author = next((key for key in keys.values() if key.user_id == request.user.pk), None)
        if not author:
            raise ValidationError("confidential.creatorRequired")
        verify_signature(author.signing_public_key, data["signature"], document_message(
            doc_id, author.user_id, author.fingerprint, data["nonce"], data["ciphertext"], envelopes))
        try:
            with transaction.atomic():
                doc = ConfidentialDocument.objects.create(id=doc_id, author_key=author, nonce=data["nonce"],
                    ciphertext=data["ciphertext"], signature=data["signature"])
                ConfidentialGrant.objects.bulk_create([ConfidentialGrant(document=doc, key=keys[e["key_id"]],
                    wrapped_key=e["wrapped_key"]) for e in envelopes])
                ConfidentialEvent.objects.create(document=doc, user=request.user, action="CREATE")
        except IntegrityError:
            return Response({"detail": "confidential.documentExists"}, status=status.HTTP_409_CONFLICT)
        return Response(summary(doc), status=status.HTTP_201_CREATED)


class ConfidentialDetailView(ConfidentialAPIView):
    def get(self, request, pk):
        # Access and delivery share a lock with revocation. A delivery already in flight cannot be recalled.
        with transaction.atomic():
            grant = ConfidentialGrant.objects.select_for_update().filter(document_id=pk,
                key__user=request.user, revoked_at__isnull=True).first()
            if not grant:
                doc = ConfidentialDocument.objects.filter(pk=pk).first()
                if doc:
                    ConfidentialEvent.objects.create(document=doc, user=request.user, action="DENY")
                # Return, rather than raise inside atomic, so denial event commits.
                return Response({"detail": "confidential.notFound"}, status=status.HTTP_404_NOT_FOUND)
            doc = ConfidentialDocument.objects.select_related("author_key__user").get(pk=pk)
            ConfidentialEvent.objects.create(document=doc, user=request.user, action="DELIVER")
            return Response({**summary(doc), "nonce": doc.nonce, "ciphertext": doc.ciphertext,
                "signature": doc.signature,
                "envelopes": [{"key_id": g.key_id, "wrapped_key": g.wrapped_key,
                    "user_id": g.key.user_id, "revoked": g.revoked_at is not None}
                    for g in doc.grants.select_related("key").order_by("key_id")]})


class ConfidentialRevokeView(ConfidentialAPIView):
    def post(self, request, pk):
        doc = ConfidentialDocument.objects.visible_to(request.user).filter(pk=pk).first()
        if not doc:
            raise NotFound("confidential.notFound")
        if doc.author_key.user_id != request.user.pk:
            raise PermissionDenied("confidential.ownerOnly")
        if not isinstance(request.data, dict) or set(request.data) != {"user_id"} or type(request.data["user_id"]) is not int:
            raise ValidationError("confidential.invalidPayload")
        target = request.data["user_id"]
        if target == request.user.pk:
            raise ValidationError("confidential.creatorRequired")
        with transaction.atomic():
            grant = get_object_or_404(ConfidentialGrant.objects.select_for_update(), document=doc, key__user_id=target)
            if grant.revoked_at is None:
                grant.revoked_at = timezone.now()
                grant.save(update_fields=["revoked_at"])
                ConfidentialEvent.objects.create(document=doc, user=request.user, action="REVOKE", target_id=target)
        return Response({"ok": True})
