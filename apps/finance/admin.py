from django.contrib import admin
from apps.finance.models import FinanceRecord, BillingSchedule


@admin.register(FinanceRecord)
class FinanceRecordAdmin(admin.ModelAdmin):
    """
    财务记录管理后台配置
    """
    list_display = (
        'id',
        'contract',
        'amount',
        'billing_period_start',
        'billing_period_end',
        'status',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'status',
        'contract__shop',
        'billing_period_start',
        'billing_period_end'
    )
    search_fields = (
        'contract__shop__name',
        'contract__id'
    )
    date_hierarchy = 'created_at'
    readonly_fields = (
        'created_at',
        'updated_at'
    )


@admin.register(BillingSchedule)
class BillingScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract",
        "contract_item",
        "period_start",
        "period_end",
        "due_date",
        "amount",
        "status",
        "source_version",
    )
    list_filter = ("status", "contract_item__item_type", "contract__shop")
    search_fields = ("contract__contract_no", "contract__shop__name")
    date_hierarchy = "due_date"
    readonly_fields = ("created_at", "updated_at")
