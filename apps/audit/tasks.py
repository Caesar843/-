import logging

from celery import shared_task

from apps.audit.services import log_audit_action, verify_audit_chains_batch

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def verify_audit_chains_task(self, **kwargs):
    """
    定时校验审计链完整性与关键合同动作序列完整性。
    """
    try:
        modules = kwargs.get("modules")
        hours = int(kwargs.get("hours", 24))
        limit = int(kwargs.get("limit", 300))
        include_sequence_check = bool(kwargs.get("include_sequence_check", True))
        object_type = kwargs.get("object_type")

        result = verify_audit_chains_batch(
            modules=modules,
            hours=hours,
            limit=limit,
            object_type=object_type,
            include_sequence_check=include_sequence_check,
        )
        log_audit_action(
            action="verify_audit_chains_task",
            module="audit",
            object_type="audit.auditlog",
            object_id=None,
            before_data={
                "modules": modules,
                "hours": hours,
                "limit": limit,
                "object_type": object_type,
                "include_sequence_check": include_sequence_check,
            },
            after_data=result,
        )
        if not result.get("ok"):
            logger.warning("Audit chain verification finished with failures: %s", result)
        else:
            logger.info("Audit chain verification passed: %s", result)
        return result
    except Exception as exc:
        logger.error("Audit chain verification task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * 5)
