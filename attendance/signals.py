import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Student


logger = logging.getLogger(__name__)
SAFE_STUDENT_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _dataset_folder(student_id):
    if not student_id or not SAFE_STUDENT_ID.fullmatch(student_id):
        logger.warning("Skipped unsafe dataset path for student ID %r", student_id)
        return None
    return Path(settings.BASE_DIR) / "dataset" / student_id


def _update_class_names(old_student_id=None, new_student_id=None):
    class_names_path = Path(settings.BASE_DIR) / "ml_models" / "class_names.json"
    if not class_names_path.exists():
        return
    try:
        class_names = json.loads(class_names_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Unable to read class_names.json")
        return

    if old_student_id in class_names:
        if new_student_id:
            class_names = [new_student_id if value == old_student_id else value for value in class_names]
        else:
            class_names = [value for value in class_names if value != old_student_id]

    temporary_path = class_names_path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    temporary_path.replace(class_names_path)


def _delete_photo(storage, photo_name):
    if photo_name and storage.exists(photo_name):
        storage.delete(photo_name)


def _rename_dataset(old_student_id, new_student_id):
    source = _dataset_folder(old_student_id)
    destination = _dataset_folder(new_student_id)
    if not source or not destination or not source.exists() or source == destination:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive = destination.parent / f"_orphaned_{new_student_id}_{timestamp}"
        counter = 1
        while archive.exists():
            archive = destination.parent / f"_orphaned_{new_student_id}_{timestamp}_{counter}"
            counter += 1
        destination.rename(archive)
    source.rename(destination)


def _delete_dataset(student_id):
    folder = _dataset_folder(student_id)
    if not folder or not folder.exists():
        return
    for path in sorted(folder.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    folder.rmdir()


@receiver(pre_save, sender=Student)
def remember_previous_student_files(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_photo_name = None
        instance._previous_student_id = None
        return
    try:
        previous = sender.objects.only("photo", "student_id").get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_photo_name = None
        instance._previous_student_id = None
        return
    instance._previous_photo_name = previous.photo.name if previous.photo else None
    instance._previous_student_id = previous.student_id


@receiver(post_save, sender=Student)
def clean_updated_student_files(sender, instance, created, **kwargs):
    if created:
        return
    previous_photo_name = getattr(instance, "_previous_photo_name", None)
    current_photo_name = instance.photo.name if instance.photo else None
    previous_student_id = getattr(instance, "_previous_student_id", None)

    if previous_photo_name and previous_photo_name != current_photo_name:
        storage = instance.photo.storage
        transaction.on_commit(lambda: _delete_photo(storage, previous_photo_name))

    if previous_student_id and previous_student_id != instance.student_id:
        new_student_id = instance.student_id
        transaction.on_commit(lambda: _rename_dataset(previous_student_id, new_student_id))
        transaction.on_commit(lambda: _update_class_names(previous_student_id, new_student_id))


@receiver(post_delete, sender=Student)
def clean_deleted_student_files(sender, instance, **kwargs):
    photo_name = instance.photo.name if instance.photo else None
    storage = instance.photo.storage
    student_id = instance.student_id
    transaction.on_commit(lambda: _delete_photo(storage, photo_name))
    transaction.on_commit(lambda: _delete_dataset(student_id))
    transaction.on_commit(lambda: _update_class_names(student_id, None))
