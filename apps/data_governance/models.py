from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.store.models import Shop


class DataQualityIssue(models.Model):
    class Domain(models.TextChoices):
        FINANCE = "finance", _("Finance")
        CONTRACT = "contract", _("Contract")
        OPS = "ops", _("Ops")

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IGNORED = "ignored", _("Ignored")
        RESOLVED = "resolved", _("Resolved")

    domain = models.CharField(max_length=20, choices=Domain.choices, db_index=True)
    rule_code = models.CharField(max_length=100)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    object_type = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=64, blank=True, null=True)
    details = models.JSONField(blank=True, null=True)
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Data Quality Issue")
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "rule_code", "object_type", "object_id", "status"],
                name="dq_issue_unique_open",
            )
        ]
        indexes = [
            models.Index(fields=["domain", "severity", "detected_at"]),
        ]

    def __str__(self):
        target = f"{self.object_type}:{self.object_id}" if self.object_type else "system"
        return f"{self.domain}-{self.rule_code}-{target}"


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=128, unique=True)
    scope = models.CharField(max_length=50, db_index=True)
    request_hash = models.CharField(max_length=64, blank=True, null=True)
    object_type = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Idempotency Key")
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.scope}:{self.key}"


class JobLock(models.Model):
    lock_name = models.CharField(max_length=100, unique=True)
    locked_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    owner = models.CharField(max_length=100, blank=True, null=True)
    payload_hash = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        verbose_name = _("Job Lock")
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.lock_name} ({self.expires_at})"


class DailyFinanceAgg(models.Model):
    """
    Logical partitioning: month_bucket (YYYY-MM) and composite indexes on shop/date.
    """

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="daily_finance_aggs",
    )
    agg_date = models.DateField(db_index=True)
    month_bucket = models.CharField(max_length=7, db_index=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rent_paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    record_count = models.IntegerField(default=0)
    paid_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Daily Finance Aggregate")
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "agg_date"], name="daily_finance_agg_unique"
            )
        ]
        indexes = [
            models.Index(fields=["shop", "agg_date"]),
            models.Index(fields=["month_bucket", "shop"]),
        ]

    def __str__(self):
        return f"{self.shop_id} {self.agg_date}"
