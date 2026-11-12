import logging
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import VanBanDen, VanBanDenAttachment, VanBanDi, VanBanDiAttachment
from .tasks import sync_sql_document_vectors

logger = logging.getLogger(__name__)


def _trigger_sync(source_type: str, document_id: int):
    if not document_id:
        return
    transaction.on_commit(
        lambda: sync_sql_document_vectors.delay(source_type, int(document_id))
    )


@receiver(post_save, sender=VanBanDen)
@receiver(post_delete, sender=VanBanDen)
def handle_vanbanden_change(sender, instance, **kwargs):
    _trigger_sync("vanbanden", instance.pk)


@receiver(post_save, sender=VanBanDenAttachment)
@receiver(post_delete, sender=VanBanDenAttachment)
def handle_vanbanden_attachment_change(sender, instance, **kwargs):
    _trigger_sync("vanbanden", instance.document_id)


@receiver(post_save, sender=VanBanDi)
@receiver(post_delete, sender=VanBanDi)
def handle_vanbandi_change(sender, instance, **kwargs):
    _trigger_sync("vanbandi", instance.pk)


@receiver(post_save, sender=VanBanDiAttachment)
@receiver(post_delete, sender=VanBanDiAttachment)
def handle_vanbandi_attachment_change(sender, instance, **kwargs):
    _trigger_sync("vanbandi", instance.document_id)


def handle_tailieu_change(sender, instance, **kwargs):
    _trigger_sync("tailieu", instance.pk)


def handle_tailieu_attachment_change(sender, instance, **kwargs):
    _trigger_sync("tailieu", instance.document_id)


def register_tailieu_signals():
    try:
        from document_templates.models import ChiTietTaiLieuAttachment, TaiLieuChiTiet

        post_save.connect(handle_tailieu_change, sender=TaiLieuChiTiet)
        post_delete.connect(handle_tailieu_change, sender=TaiLieuChiTiet)

        post_save.connect(handle_tailieu_attachment_change, sender=ChiTietTaiLieuAttachment)
        post_delete.connect(handle_tailieu_attachment_change, sender=ChiTietTaiLieuAttachment)
    except (ImportError, RuntimeError) as exc:
        logger.warning("Could not register tailieu signals for AI indexing: %s", exc)
