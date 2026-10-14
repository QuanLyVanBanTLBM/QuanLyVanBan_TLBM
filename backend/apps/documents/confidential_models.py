"""E2EE snapshots. No plaintext document fields or public media paths."""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ConfidentialKey(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    encryption_public_key = models.TextField()
    signing_public_key = models.TextField()
    fingerprint = models.CharField(max_length=64, unique=True)
    vault = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_confidential_key"
        default_permissions = ()


class ConfidentialDocumentQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated or not user.is_active:
            return self.none()
        # No superuser, staff, department or generic view-permission override.
        return self.filter(grants__key__user=user, grants__revoked_at__isnull=True)


class ConfidentialDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_key = models.ForeignKey(ConfidentialKey, on_delete=models.PROTECT)
    nonce = models.CharField(max_length=16)
    ciphertext = models.TextField()
    signature = models.CharField(max_length=88)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ConfidentialDocumentQuerySet.as_manager()

    class Meta:
        db_table = "documents_confidential_document"
        default_permissions = ()
        ordering = ["-created_at", "id"]


class ConfidentialGrant(models.Model):
    document = models.ForeignKey(ConfidentialDocument, on_delete=models.CASCADE, related_name="grants")
    key = models.ForeignKey(ConfidentialKey, on_delete=models.PROTECT)
    wrapped_key = models.CharField(max_length=512)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "documents_confidential_grant"
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["document", "key"], name="uq_confidential_grant")]


class ConfidentialEvent(models.Model):
    """Records server delivery/revocation, never claims proof of local reading."""
    document = models.ForeignKey(ConfidentialDocument, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=16)
    target_id = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_confidential_event"
        default_permissions = ()
        constraints = [models.CheckConstraint(condition=Q(action__in=["CREATE", "DELIVER", "DENY", "REVOKE"]), name="chk_confidential_event_action")]
