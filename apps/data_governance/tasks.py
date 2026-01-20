import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.data_governance.models import DataQualityIssue, DailyFinanceAgg
from apps.data_governance.utils import acquire_job_lock, release_job_lock
from apps.finance.models import FinanceRecord
from apps.store.models import Contract

logger = logging.getLogger(__name__)


def _upsert_issue(domain, rule_code, severity, object_type=None, object_id=None, details=None):
    issue, created = DataQualityIssue.objects.get_or_create(
        domain=domain,
        rule_code=rule_code,
        severity=severity,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        status=DataQualityIssue.Status.OPEN,
        defaults={"details": details or {}},
    )
    if not created:
        issue.details = details or issue.details
        issue.detected_at = timezone.now()
        issue.save(update_fields=["details", "detected_at"])
    return issue


@shared_task
def run_data_quality_checks():
    if not getattr(settings, "ENABLE_DATA_QUALITY_CHECK", False):
        logger.info("Data quality checks disabled.")
        return {"status": "disabled"}

    lock = None
    if getattr(settings, "ENABLE_JOB_LOCK", False):
        lock = acquire_job_lock(
            lock_name="data_quality_checks",
            ttl_seconds=900,
            owner="data_governance",
            payload={"task": "run_data_quality_checks"},
        )
        if not lock:
            logger.warning("Data quality check skipped due to existing lock.")
            return {"status": "locked"}

    try:
        issues = {"finance": 0, "contract": 0}

        # FinanceRecord: missing
        missing_finance = FinanceRecord.objects.filter(
            Q(amount__isnull=True)
            | Q(contract__isnull=True)
            | Q(billing_period_start__isnull=True)
            | Q(billing_period_end__isnull=True)
        )
        for record in missing_finance:
            _upsert_issue(
                DataQualityIssue.Domain.FINANCE,
                "FIN_MISSING_REQUIRED",
                DataQualityIssue.Severity.HIGH,
                "FinanceRecord",
                record.id,
                {"missing_fields": ["amount", "contract", "billing_period_start", "billing_period_end"]},
            )
            issues["finance"] += 1

        # FinanceRecord: anomaly
        anomaly_finance = FinanceRecord.objects.filter(
            Q(amount__lt=0)
            | Q(amount__gt=999999.99)
            | Q(billing_period_end__lte=F("billing_period_start"))
            | ~Q(status__in=[choice[0] for choice in FinanceRecord.Status.choices])
        )
        for record in anomaly_finance:
            _upsert_issue(
                DataQualityIssue.Domain.FINANCE,
                "FIN_ANOMALY",
                DataQualityIssue.Severity.MEDIUM,
                "FinanceRecord",
                record.id,
                {
                    "amount": str(record.amount),
                    "billing_period_start": str(record.billing_period_start),
                    "billing_period_end": str(record.billing_period_end),
                    "status": record.status,
                },
            )
            issues["finance"] += 1

        # FinanceRecord: duplicates (contract + fee_type + period)
        duplicate_finance = (
            FinanceRecord.objects.values(
                "contract_id", "fee_type", "billing_period_start", "billing_period_end"
            )
            .annotate(dup_count=Count("id"))
            .filter(dup_count__gt=1)
        )
        for dup in duplicate_finance:
            ids = list(
                FinanceRecord.objects.filter(
                    contract_id=dup["contract_id"],
                    fee_type=dup["fee_type"],
                    billing_period_start=dup["billing_period_start"],
                    billing_period_end=dup["billing_period_end"],
                ).values_list("id", flat=True)
            )
            _upsert_issue(
                DataQualityIssue.Domain.FINANCE,
                "FIN_DUPLICATE_PERIOD",
                DataQualityIssue.Severity.HIGH,
                "FinanceRecord",
                None,
                {"record_ids": ids, "group": dup},
            )
            issues["finance"] += 1

        # Contract: missing
        missing_contract = Contract.objects.filter(
            Q(shop__isnull=True) | Q(start_date__isnull=True) | Q(end_date__isnull=True)
        )
        for contract in missing_contract:
            _upsert_issue(
                DataQualityIssue.Domain.CONTRACT,
                "CONTRACT_MISSING_REQUIRED",
                DataQualityIssue.Severity.HIGH,
                "Contract",
                contract.id,
                {"missing_fields": ["shop", "start_date", "end_date"]},
            )
            issues["contract"] += 1

        # Contract: anomaly
        anomaly_contract = Contract.objects.filter(
            Q(end_date__lte=F("start_date"))
            | Q(monthly_rent__lte=0)
            | Q(deposit__lt=0)
            | ~Q(status__in=[choice[0] for choice in Contract.Status.choices])
        )
        for contract in anomaly_contract:
            _upsert_issue(
                DataQualityIssue.Domain.CONTRACT,
                "CONTRACT_ANOMALY",
                DataQualityIssue.Severity.MEDIUM,
                "Contract",
                contract.id,
                {
                    "start_date": str(contract.start_date),
                    "end_date": str(contract.end_date),
                    "monthly_rent": str(contract.monthly_rent),
                    "deposit": str(contract.deposit),
                    "status": contract.status,
                },
            )
            issues["contract"] += 1

        # Contract: duplicates (shop + start_date + end_date)
        duplicate_contracts = (
            Contract.objects.values("shop_id", "start_date", "end_date")
            .annotate(dup_count=Count("id"))
            .filter(dup_count__gt=1)
        )
        for dup in duplicate_contracts:
            ids = list(
                Contract.objects.filter(
                    shop_id=dup["shop_id"],
                    start_date=dup["start_date"],
                    end_date=dup["end_date"],
                ).values_list("id", flat=True)
            )
            _upsert_issue(
                DataQualityIssue.Domain.CONTRACT,
                "CONTRACT_DUPLICATE_PERIOD",
                DataQualityIssue.Severity.MEDIUM,
                "Contract",
                None,
                {"contract_ids": ids, "group": dup},
            )
            issues["contract"] += 1

        logger.info("Data quality checks completed: %s", issues)
        return {"status": "ok", "issues": issues}
    finally:
        if lock:
            release_job_lock(lock)


@shared_task
def build_daily_finance_agg(target_date: str = None, days_back: int = 1):
    if not getattr(settings, "ENABLE_OFFLINE_AGG", False):
        logger.info("Offline aggregation disabled.")
        return {"status": "disabled"}

    lock = None
    if getattr(settings, "ENABLE_JOB_LOCK", False):
        lock = acquire_job_lock(
            lock_name="daily_finance_agg",
            ttl_seconds=900,
            owner="data_governance",
            payload={"target_date": target_date, "days_back": days_back},
        )
        if not lock:
            logger.warning("Daily finance aggregation skipped due to existing lock.")
            return {"status": "locked"}

    try:
        if target_date:
            start_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            end_date = start_date
        else:
            end_date = timezone.now().date() - timedelta(days=1)
            start_date = end_date - timedelta(days=days_back - 1)

        qs = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.PAID,
            paid_at__date__gte=start_date,
            paid_at__date__lte=end_date,
        )

        aggregates = (
            qs.values("contract__shop_id", "paid_at__date")
            .annotate(
                paid_amount=Sum("amount"),
                rent_paid_amount=Sum(
                    "amount", filter=Q(fee_type=FinanceRecord.FeeType.RENT)
                ),
                record_count=Count("id"),
                paid_count=Count("id"),
            )
            .order_by()
        )

        updated = 0
        for row in aggregates:
            shop_id = row["contract__shop_id"]
            agg_date = row["paid_at__date"]
            month_bucket = agg_date.strftime("%Y-%m")
            DailyFinanceAgg.objects.update_or_create(
                shop_id=shop_id,
                agg_date=agg_date,
                defaults={
                    "month_bucket": month_bucket,
                    "total_amount": row["paid_amount"] or 0,
                    "paid_amount": row["paid_amount"] or 0,
                    "rent_paid_amount": row["rent_paid_amount"] or 0,
                    "record_count": row["record_count"] or 0,
                    "paid_count": row["paid_count"] or 0,
                },
            )
            updated += 1

        logger.info(
            "Daily finance aggregation completed: %s rows updated for %s to %s",
            updated,
            start_date,
            end_date,
        )
        return {"status": "ok", "rows": updated}
    finally:
        if lock:
            release_job_lock(lock)
