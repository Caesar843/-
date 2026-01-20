from django.contrib import admin

from apps.data_governance.models import DataQualityIssue, DailyFinanceAgg, IdempotencyKey, JobLock


@admin.register(DataQualityIssue)
class DataQualityIssueAdmin(admin.ModelAdmin):
    list_display = ("id", "domain", "rule_code", "severity", "status", "object_type", "object_id", "detected_at")
    list_filter = ("domain", "severity", "status", "detected_at")
    search_fields = ("rule_code", "object_type", "object_id")
    ordering = ("-detected_at",)


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "scope", "key", "object_type", "object_id", "last_seen_at")
    list_filter = ("scope",)
    search_fields = ("key", "object_type", "object_id")
    ordering = ("-last_seen_at",)


@admin.register(JobLock)
class JobLockAdmin(admin.ModelAdmin):
    list_display = ("id", "lock_name", "locked_at", "expires_at", "owner")
    list_filter = ("lock_name",)
    search_fields = ("lock_name", "owner")
    ordering = ("-locked_at",)


@admin.register(DailyFinanceAgg)
class DailyFinanceAggAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "agg_date", "month_bucket", "paid_amount", "rent_paid_amount", "record_count")
    list_filter = ("month_bucket", "agg_date")
    search_fields = ("shop__name",)
    ordering = ("-agg_date",)
