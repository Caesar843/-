from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date

"""
Store App Models
----------------
[架构职责]
1. 定义数据结构与约束。
2. 声明业务实体及其关系。
3. 提供数据访问与基本操作。

[设计假设]
- 店铺（Shop）是核心实体，拥有唯一标识与基本属性。
- 合同（Contract）依赖于店铺，描述租赁关系。
- 合同状态流转：DRAFT → ACTIVE → EXPIRED/TERMINATED
- 财务记录（FinanceRecord）由合同派生，不在此模块定义。
"""


class Shop(models.Model):
    """
    店铺模型
    --------
    [业务属性]
    - name: 店铺名称（唯一）
    - area: 面积（平方米）
    - rent: 租金（元/月）
    - description: 描述
    - is_deleted: 是否删除（逻辑删除）
    - created_at: 创建时间
    - updated_at: 更新时间
    """

    # 业态类型枚举
    class BusinessType(models.TextChoices):
        RETAIL = 'RETAIL', _('零售')
        FOOD = 'FOOD', _('餐饮')
        ENTERTAINMENT = 'ENTERTAINMENT', _('娱乐')
        SERVICE = 'SERVICE', _('服务')
        OTHER = 'OTHER', _('其他')

    # 业务字段
    name = models.CharField(
        verbose_name=_("店铺名称"),
        max_length=100,
        unique=True,
        help_text=_("店铺的唯一名称")
    )
    business_type = models.CharField(
        verbose_name=_("业态类型"),
        max_length=20,
        choices=BusinessType.choices,
        default=BusinessType.OTHER,
        help_text=_("店铺的业态类型")
    )
    area = models.DecimalField(
        verbose_name=_("经营面积"),
        max_digits=6,
        decimal_places=2,
        help_text=_("店铺面积，单位：平方米")
    )
    rent = models.DecimalField(
        verbose_name=_("租金"),
        max_digits=8,
        decimal_places=2,
        help_text=_("每月租金，单位：元")
    )
    contact_person = models.CharField(
        verbose_name=_("联系人"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("店铺联系人姓名")
    )
    contact_phone = models.CharField(
        verbose_name=_("联系方式"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("店铺联系人电话")
    )
    entry_date = models.DateField(
        verbose_name=_("入驻日期"),
        blank=True,
        null=True,
        help_text=_("店铺入驻商场的日期")
    )
    description = models.TextField(
        verbose_name=_("描述"),
        blank=True,
        null=True,
        help_text=_("店铺的详细描述")
    )
    is_deleted = models.BooleanField(
        verbose_name=_("是否删除"),
        default=False,
        help_text=_("逻辑删除标记")
    )

    # 审计字段
    created_at = models.DateTimeField(
        verbose_name=_("创建时间"),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name=_("更新时间"),
        auto_now=True
    )

    class Meta:
        """元数据"""
        verbose_name = _("店铺")
        verbose_name_plural = _("店铺")
        ordering = ["name"]

    def __str__(self):
        """字符串表示"""
        return self.name

    def clean(self):
        """模型级验证"""
        errors = {}
        
        # 验证联系方式（电话号码）
        if self.contact_phone:
            import re
            phone_pattern = r'^1[3-9]\d{9}$|^0\d{2,3}-\d{7,8}$'
            if not re.match(phone_pattern, self.contact_phone):
                errors['contact_phone'] = _("联系方式格式不正确，请输入有效的手机号码或固定电话（如：13812345678 或 010-12345678）")
        
        # 验证入驻日期
        if self.entry_date:
            if self.entry_date > date.today():
                errors['entry_date'] = _("入驻日期不能是未来日期")
        
        if errors:
            raise ValidationError(errors)


class Contract(models.Model):
    """
    合同模型
    --------
    [业务属性]
    - shop: 关联店铺（外键）
    - start_date: 开始日期
    - end_date: 结束日期
    - monthly_rent: 月租金
    - deposit: 押金
    - payment_cycle: 缴费周期
    - status: 状态（草稿/生效/过期/终止）
    - created_at: 创建时间
    - updated_at: 更新时间

    [业务规则]
    - 结束日期必须晚于开始日期
    - 月租金与押金必须大于0
    """

    # 状态枚举
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('草稿')
        PENDING_REVIEW = 'PENDING_REVIEW', _('待审核')
        APPROVED = 'APPROVED', _('已批准')
        REJECTED = 'REJECTED', _('已拒绝')
        ACTIVE = 'ACTIVE', _('生效')
        EXPIRED = 'EXPIRED', _('过期')
        TERMINATED = 'TERMINATED', _('终止')

    # 缴费周期枚举
    class PaymentCycle(models.TextChoices):
        MONTHLY = 'MONTHLY', _('月付')
        QUARTERLY = 'QUARTERLY', _('季付')
        SEMIANNUALLY = 'SEMIANNUALLY', _('半年付')
        ANNUALLY = 'ANNUALLY', _('年付')

    # 业务字段
    shop = models.ForeignKey(
        Shop,
        verbose_name=_("店铺"),
        on_delete=models.PROTECT,
        related_name="contracts",
        help_text=_("关联的店铺")
    )
    start_date = models.DateField(
        verbose_name=_("开始日期"),
        help_text=_("合同开始日期")
    )
    end_date = models.DateField(
        verbose_name=_("结束日期"),
        help_text=_("合同结束日期")
    )
    monthly_rent = models.DecimalField(
        verbose_name=_("月租金"),
        max_digits=8,
        decimal_places=2,
        help_text=_("每月租金，单位：元")
    )
    deposit = models.DecimalField(
        verbose_name=_("押金"),
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text=_("押金，单位：元")
    )
    payment_cycle = models.CharField(
        verbose_name=_("缴费周期"),
        max_length=20,
        choices=PaymentCycle.choices,
        default=PaymentCycle.MONTHLY,
        help_text=_("租金缴费周期")
    )
    status = models.CharField(
        verbose_name=_("状态"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text=_("合同状态")
    )

    # 审核相关字段
    reviewed_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_contracts',
        verbose_name=_("审核人"),
        help_text=_("审核该合同的管理员")
    )
    reviewed_at = models.DateTimeField(
        verbose_name=_("审核时间"),
        null=True,
        blank=True,
        help_text=_("合同审核的时间")
    )
    review_comment = models.TextField(
        verbose_name=_("审核意见"),
        blank=True,
        null=True,
        help_text=_("审核人的意见备注")
    )

    # 审计字段
    created_at = models.DateTimeField(
        verbose_name=_("创建时间"),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name=_("更新时间"),
        auto_now=True
    )

    class Meta:
        """元数据"""
        verbose_name = _("合同")
        verbose_name_plural = _("合同")
        ordering = ["-created_at"]
        constraints = [
            # 结束日期必须晚于开始日期
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F('start_date')),
                name='contract_end_date_gt_start_date'
            ),
            # 月租金必须大于0
            models.CheckConstraint(
                condition=models.Q(monthly_rent__gt=0),
                name='contract_monthly_rent_gt_0'
            ),
            # 押金必须大于等于0
            models.CheckConstraint(
                condition=models.Q(deposit__gte=0),
                name='contract_deposit_gte_0'
            ),
        ]

    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.status}"

    def clean(self):
        """模型级验证"""
        # 结束日期必须晚于开始日期
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError(_("结束日期必须晚于开始日期"))

        # 月租金必须大于0
        if self.monthly_rent is not None:
            if self.monthly_rent <= 0:
                raise ValidationError(_("月租金必须大于0"))

        # 押金必须大于等于0
        if self.deposit is not None:
            if self.deposit < 0:
                raise ValidationError(_("押金必须大于等于0"))