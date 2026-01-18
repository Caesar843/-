from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.store.models import Contract


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

    @property
    def due_date(self):
        """Compatibility alias for legacy code that expects a due_date field."""
        return self.billing_period_end

    class Meta:
        verbose_name = _("财务记录")
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
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
