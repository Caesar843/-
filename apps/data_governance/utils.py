import hashlib
import json
import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.data_governance.models import JobLock

logger = logging.getLogger(__name__)


def hash_payload(payload) -> str:
    if payload is None:
        return ""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_idempotency_key(scope: str, payload: dict) -> str:
    raw = f"{scope}:{hash_payload(payload)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def acquire_job_lock(lock_name: str, ttl_seconds: int, owner: str = None, payload: dict = None):
    now = timezone.now()
    expires_at = now + timedelta(seconds=ttl_seconds)
    payload_hash = hash_payload(payload)

    with transaction.atomic():
        try:
            lock = JobLock.objects.select_for_update().get(lock_name=lock_name)
            if lock.expires_at and lock.expires_at > now:
                return None
            lock.locked_at = now
            lock.expires_at = expires_at
            lock.owner = owner
            lock.payload_hash = payload_hash
            lock.save(update_fields=["locked_at", "expires_at", "owner", "payload_hash"])
            return lock
        except JobLock.DoesNotExist:
            try:
                return JobLock.objects.create(
                    lock_name=lock_name,
                    locked_at=now,
                    expires_at=expires_at,
                    owner=owner,
                    payload_hash=payload_hash,
                )
            except IntegrityError:
                return None


def release_job_lock(lock: JobLock):
    if not lock:
        return
    try:
        lock.delete()
    except Exception as exc:
        logger.warning("Failed to release job lock %s: %s", lock.lock_name, exc)
