import hashlib
from datetime import timedelta
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.audit.context import get_request_context
from apps.audit.models import AuditLog
from apps.audit.utils import normalize_for_hash


CHAINED_MODULES = {"contract", "finance"}


def log_audit_action(
    action: str,
    module: str,
    instance=None,
    object_id: Optional[str] = None,
    object_type=None,
    actor_id: Optional[int] = None,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    request=None,
    request_id: Optional[str] = None,
):
    ctx = get_request_context()
    request_user = ctx.get("user")
    resolved_actor_id = actor_id or (request_user.id if request_user and request_user.is_authenticated else None)

    if instance is not None:
        content_type = ContentType.objects.get_for_model(instance.__class__)
        resolved_object_id = str(instance.pk)
    elif object_type is not None:
        content_type = _resolve_content_type(object_type)
        resolved_object_id = str(object_id) if object_id is not None else None
    else:
        content_type = None
        resolved_object_id = str(object_id) if object_id is not None else None

    if request is not None:
        ip_address = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        resolved_request_id = request_id or request.headers.get("X-Request-ID")
    else:
        ip_address = ctx.get("ip_address")
        user_agent = ctx.get("user_agent")
        resolved_request_id = request_id or ctx.get("request_id")

    created_at = timezone.now()

    prev_hash = None
    current_hash = None
    if module in CHAINED_MODULES and content_type and resolved_object_id:
        prev_hash = _get_prev_hash(module, content_type, resolved_object_id)
        current_hash = _compute_hash(
            actor_id=resolved_actor_id,
            action=action,
            module=module,
            content_type_id=content_type.id,
            object_id=resolved_object_id,
            before_data=before_data,
            after_data=after_data,
            created_at=created_at,
            prev_hash=prev_hash,
        )

    with transaction.atomic():
        AuditLog.objects.create(
            actor_id=resolved_actor_id,
            action=action,
            module=module,
            content_type=content_type,
            object_id=resolved_object_id,
            before_data=before_data,
            after_data=after_data,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=resolved_request_id,
            prev_hash=prev_hash,
            current_hash=current_hash,
            created_at=created_at,
        )


def verify_audit_chain(object_type, object_id, module: Optional[str] = None):
    content_type = _resolve_content_type(object_type)
    modules = [module] if module else sorted(CHAINED_MODULES)
    checked_total = 0
    module_results = {}

    for current_module in modules:
        logs = (
            AuditLog.objects.filter(
                module=current_module,
                content_type=content_type,
                object_id=str(object_id),
            )
            .order_by("created_at", "id")
        )

        prev_hash = None
        checked_count = 0
        for log in logs:
            checked_count += 1
            if log.prev_hash != prev_hash:
                return {
                    "ok": False,
                    "module": current_module,
                    "error": "prev_hash_mismatch",
                    "log_id": log.id,
                    "expected_prev_hash": prev_hash,
                    "actual_prev_hash": log.prev_hash,
                }
            if not log.current_hash:
                return {
                    "ok": False,
                    "module": current_module,
                    "error": "missing_current_hash",
                    "log_id": log.id,
                }
            expected_hash = _compute_hash(
                actor_id=log.actor_id,
                action=log.action,
                module=log.module,
                content_type_id=log.content_type_id,
                object_id=log.object_id,
                before_data=log.before_data,
                after_data=log.after_data,
                created_at=log.created_at,
                prev_hash=prev_hash,
            )
            if log.current_hash != expected_hash:
                return {
                    "ok": False,
                    "module": current_module,
                    "error": "hash_mismatch",
                    "log_id": log.id,
                    "expected_hash": expected_hash,
                    "actual_hash": log.current_hash,
                }
            prev_hash = log.current_hash

        checked_total += checked_count
        module_results[current_module] = checked_count

    return {"ok": True, "checked": checked_total, "modules": module_results}


def verify_contract_audit_sequence(contract_id):
    from apps.store.models import Contract

    try:
        contract = Contract.objects.get(id=contract_id)
    except Contract.DoesNotExist:
        return {
            "ok": False,
            "error": "contract_not_found",
            "contract_id": contract_id,
        }

    content_type = ContentType.objects.get_for_model(Contract)
    actions = list(
        AuditLog.objects.filter(
            module="contract",
            content_type=content_type,
            object_id=str(contract_id),
        ).values_list("action", flat=True)
    )
    action_set = set(actions)

    required_actions = []
    if contract.status != Contract.Status.DRAFT:
        required_actions.extend(["submit_contract_review", "start_approval_round"])
    if contract.status in [Contract.Status.APPROVED, Contract.Status.ACTIVE, Contract.Status.EXPIRED, Contract.Status.TERMINATED]:
        required_actions.append("approve_contract")
    if contract.status == Contract.Status.REJECTED:
        required_actions.append("reject_contract")
    if contract.status in [Contract.Status.ACTIVE, Contract.Status.EXPIRED, Contract.Status.TERMINATED]:
        required_actions.append("activate_contract")
    if contract.status == Contract.Status.TERMINATED:
        required_actions.append("terminate_contract")
    if contract.status == Contract.Status.EXPIRED:
        required_actions.append("expire_contract")
    if contract.is_archived:
        required_actions.append("archive_contract")

    missing_actions = sorted({action for action in required_actions if action not in action_set})
    return {
        "ok": not missing_actions,
        "contract_id": contract.id,
        "status": contract.status,
        "is_archived": contract.is_archived,
        "missing_actions": missing_actions,
        "action_count": len(actions),
    }


def verify_audit_chains_batch(
    *,
    modules=None,
    hours: int = 24,
    limit: int = 200,
    object_type: Optional[str] = None,
    include_sequence_check: bool = True,
):
    selected_modules = list(modules or sorted(CHAINED_MODULES))
    if not selected_modules:
        return {"ok": True, "checked_objects": 0, "failures": []}

    since = timezone.now() - timedelta(hours=max(int(hours or 1), 1))
    logs_qs = AuditLog.objects.filter(
        module__in=selected_modules,
        created_at__gte=since,
        content_type__isnull=False,
    ).exclude(object_id__isnull=True).exclude(object_id="")

    if object_type:
        logs_qs = logs_qs.filter(content_type=_resolve_content_type(object_type))

    targets = list(
        logs_qs.order_by("-created_at")
        .values_list("content_type_id", "object_id")
        .distinct()[: max(int(limit or 1), 1)]
    )

    failures = []
    sequence_failures = []
    checked = 0
    for content_type_id, object_id in targets:
        content_type = ContentType.objects.get_for_id(content_type_id)
        result = verify_audit_chain(content_type, object_id)
        checked += 1
        if not result.get("ok"):
            failures.append(
                {
                    "content_type": f"{content_type.app_label}.{content_type.model}",
                    "object_id": str(object_id),
                    "detail": result,
                }
            )
            continue

        if include_sequence_check and content_type.app_label == "store" and content_type.model == "contract":
            sequence_result = verify_contract_audit_sequence(object_id)
            if not sequence_result.get("ok"):
                sequence_failures.append(sequence_result)

    return {
        "ok": not failures and not sequence_failures,
        "checked_objects": checked,
        "window_hours": int(hours),
        "modules": selected_modules,
        "failures": failures,
        "sequence_failures": sequence_failures,
        "failure_count": len(failures),
        "sequence_failure_count": len(sequence_failures),
    }


def _resolve_content_type(object_type):
    if isinstance(object_type, ContentType):
        return object_type
    if hasattr(object_type, "_meta"):
        return ContentType.objects.get_for_model(object_type)
    if isinstance(object_type, str) and "." in object_type:
        app_label, model = object_type.split(".", 1)
        return ContentType.objects.get_by_natural_key(app_label, model.lower())
    raise ValueError("Unsupported object_type for audit chain verification")


def _get_prev_hash(module, content_type, object_id):
    last_log = (
        AuditLog.objects.filter(
            module=module,
            content_type=content_type,
            object_id=str(object_id),
        )
        .order_by("-created_at", "-id")
        .first()
    )
    return last_log.current_hash if last_log else None


def _compute_hash(
    actor_id,
    action,
    module,
    content_type_id,
    object_id,
    before_data,
    after_data,
    created_at,
    prev_hash,
):
    payload = {
        "actor_id": actor_id,
        "action": action,
        "module": module,
        "content_type_id": content_type_id,
        "object_id": object_id,
        "before_data": before_data,
        "after_data": after_data,
        "created_at": created_at.isoformat(),
        "prev_hash": prev_hash,
    }
    normalized = normalize_for_hash(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
