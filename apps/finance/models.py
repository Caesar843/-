from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.store.models import Contract, ContractItem
from apps.tenants.managers import TenantManager


class FinanceRecord(models.Model):
    """
    财务记录实体
    管理合同的账单数据，支持按合同生成和状态流转
    """

    class Status(models.TextChoices):
        """
        账单状态机定义
        注意：状态流转逻辑必须由 Service 层控制，Model 仅存储结果。
        """
        UNPAID = 'UNPAID', _('未支付')
        PAID = 'PAID', _('已支付')
        VOID = 'VOID', _('已作废')

    class FeeType(models.TextChoices):
        """
        费用类型
        """
        RENT = 'RENT', _('租金')
        PROPERTY_FEE = 'PROPERTY_FEE', _('物业费')
        UTILITY_FEE = 'UTILITY_FEE', _('水电费')
        OTHER = 'OTHER', _('其他费用')

    class PaymentMethod(models.TextChoices):
        """
        缴费方式
        """
        WECHAT = 'WECHAT', _('微信支付')
        ALIPAY = 'ALIPAY', _('支付宝')
        BANK_TRANSFER = 'BANK_TRANSFER', _('银行转账')
        CASH = 'CASH', _('现金')

    # 外键关联：使用 PROTECT 防止误删包含账单的合同
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.PROTECT,
        related_name='finance_records',
        verbose_name=_("租户")
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name='finance_records',
        verbose_name=_("关联合同")
    )

    # 金额字段：保留2位小数，最大支持 999,999.99
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("金额")
    )

    # 账单周期
    billing_period_start = models.DateField(
        verbose_name=_("账单周期开始日期"),
        db_index=True
    )
    billing_period_end = models.DateField(
        verbose_name=_("账单周期结束日期"),
        db_index=True
    )

    # 状态
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
        verbose_name=_("账单状态"),
        db_index=True
    )

    # 费用类型
    fee_type = models.CharField(
        max_length=20,
        choices=FeeType.choices,
        default=FeeType.RENT,
        verbose_name=_("费用类型"),
        db_index=True
    )

    # 缴费方式
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
        verbose_name=_("缴费方式")
    )

    # 缴费时间
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("缴费时间")
    )

    # 交易单号
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("交易单号")
    )

    # 提醒标记
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name=_("是否已发送提醒"),
        help_text=_("用于追踪是否已发送支付提醒，避免重复提醒")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    objects = TenantManager()

    @property
    def due_date(self):
        """Compatibility alias for legacy code that expects a due_date field."""
        return self.billing_period_end

    class Meta:
        verbose_name = _("财务记录")
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "billing_period_end"]),
        ]
        constraints = [
            # 数据库级数据完整性约束：账单周期结束日期必须晚于开始日期
            models.CheckConstraint(
                condition=models.Q(billing_period_end__gt=models.F('billing_period_start')),
                name='finance_record_period_end_gt_start'
            ),
            # 业务约束：同一合同在同一时间只能有一个未支付或已支付的账单
            # 注：这里简化处理，实际业务可能需要更复杂的约束
        ]

    def __str__(self):
        return f"{self.contract} - {self.get_fee_type_display()} - {self.get_status_display()} - ¥{self.amount}"

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        super().save(*args, **kwargs)


class BillingSchedule(models.Model):
    """
    账单计划：由合同费用项按周期生成，可追溯来源版本
    """

    class Status(models.TextChoices):
        PLANNED = "PLANNED", _("待出账")
        ISSUED = "ISSUED", _("已出账")
        PARTIAL = "PARTIAL", _("部分支付")
        PAID = "PAID", _("已支付")
        VOID = "VOID", _("作废")
        OVERDUE = "OVERDUE", _("逾期")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="billing_schedules",
        verbose_name=_("租户"),
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="billing_schedules",
        verbose_name=_("合同"),
    )
    contract_item = models.ForeignKey(
        ContractItem,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="billing_schedules",
        verbose_name=_("合同费用项"),
    )
    period_start = models.DateField(
        db_index=True,
        verbose_name=_("账期开始"),
    )
    period_end = models.DateField(
        db_index=True,
        verbose_name=_("账期结束"),
    )
    due_date = models.DateField(
        db_index=True,
        verbose_name=_("应收日期"),
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("计划金额"),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
        verbose_name=_("计划状态"),
    )
    source_version = models.PositiveIntegerField(
        default=1,
        verbose_name=_("来源合同版本"),
    )
    finance_record = models.OneToOneField(
        "FinanceRecord",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="billing_schedule",
        verbose_name=_("生成财务记录"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    objects = TenantManager()

    class Meta:
        verbose_name = _("账单计划")
        verbose_name_plural = verbose_name
        ordering = ["contract_id", "period_start", "id"]
        indexes = [
            models.Index(fields=["tenant", "contract", "status"]),
            models.Index(fields=["tenant", "due_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="billing_schedule_period_end_gte_start",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="billing_schedule_amount_gte_0",
            ),
            models.UniqueConstraint(
                fields=["contract", "contract_item", "period_start", "period_end", "source_version"],
                name="billing_schedule_unique_period_per_item_version",
            ),
        ]

    def __str__(self):
        return f"{self.contract_id}-{self.period_start}-{self.amount}"

    def clean(self):
        if self.contract_id and self.tenant_id and self.contract.tenant_id != self.tenant_id:
            raise ValidationError(_("账单计划租户与合同租户不一致"))
        if self.contract_item_id and self.contract_item.contract_id != self.contract_id:
            raise ValidationError(_("账单计划费用项不属于该合同"))

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        self.full_clean()
        super().save(*args, **kwargs)
