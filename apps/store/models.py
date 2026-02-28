from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date
from apps.tenants.managers import TenantManager
from apps.tenants.context import get_current_tenant

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
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.PROTECT,
        related_name='shops',
        verbose_name=_("租户"),
        help_text=_("店铺所属的租户/商场")
    )
    code = models.CharField(
        verbose_name=_("店铺编号"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("外部或业务系统的店铺编号，用于去重匹配")
    )
    mall_name = models.CharField(
        verbose_name=_("商场/园区/区域"),
        max_length=120,
        blank=True,
        null=True,
        help_text=_("所在商场、园区或区域，用于去重匹配与展示")
    )
    address = models.CharField(
        verbose_name=_("店铺地址"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("详细地址或楼层位置")
    )
    org_unit = models.ForeignKey(
        'tenants.OrgUnit',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='shops',
        verbose_name=_("组织单元"),
        help_text=_("店铺所属组织层级")
    )
    name = models.CharField(
        verbose_name=_("店铺名称"),
        max_length=100,
        help_text=_("店铺名称（租户内唯一）")
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

    objects = TenantManager()

    class Meta:
        """元数据"""
        verbose_name = _("店铺")
        verbose_name_plural = _("店铺")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "is_deleted"]),
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["tenant", "code"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "name"], name="shop_unique_name_per_tenant"),
            models.UniqueConstraint(fields=["tenant", "code"], name="shop_unique_code_per_tenant", condition=models.Q(code__isnull=False)),
        ]

    def __str__(self):
        """字符串表示"""
        return self.name

    def clean(self):
        """模型级验证"""
        errors = {}

        if self.org_unit_id and self.tenant_id:
            if self.org_unit.tenant_id != self.tenant_id:
                errors['org_unit'] = _("组织单元必须属于同一租户")
        
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

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            tenant = get_current_tenant()
            if tenant:
                self.tenant = tenant
        super().save(*args, **kwargs)


class ContractNumberSequence(models.Model):
    """
    Per-tenant, per-year contract number sequence.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="contract_number_sequences",
        verbose_name=_("租户"),
    )
    year = models.PositiveIntegerField(
        verbose_name=_("年份"),
    )
    last_seq = models.PositiveIntegerField(
        default=0,
        verbose_name=_("最新序号"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("创建时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    class Meta:
        verbose_name = _("合同编号序列")
        verbose_name_plural = _("合同编号序列")
        indexes = [
            models.Index(fields=["tenant", "year"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "year"],
                name="contract_no_seq_unique_tenant_year",
            )
        ]

    def __str__(self):
        return f"{self.tenant_id}-{self.year}-{self.last_seq}"


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
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_("租户"),
        help_text=_("合同所属的租户/商场")
    )
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
    contract_no = models.CharField(
        verbose_name=_("合同编号"),
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("合同业务编号（同租户内唯一）")
    )
    is_archived = models.BooleanField(
        verbose_name=_("是否归档"),
        default=False,
        db_index=True,
        help_text=_("合同是否归档，归档后默认不在列表展示")
    )
    archived_at = models.DateTimeField(
        verbose_name=_("归档时间"),
        blank=True,
        null=True,
        help_text=_("合同归档时间")
    )
    archived_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="archived_contracts",
        verbose_name=_("归档人"),
        help_text=_("执行归档操作的用户")
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

    objects = TenantManager()

    class Meta:
        """元数据"""
        verbose_name = _("合同")
        verbose_name_plural = _("合同")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
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
            models.UniqueConstraint(
                fields=["tenant", "contract_no"],
                name="contract_unique_no_per_tenant",
                condition=models.Q(contract_no__isnull=False),
            ),
        ]

    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.status}"

    def clean(self):
        """模型级验证"""
        if self.tenant_id and self.shop_id and self.shop.tenant_id != self.tenant_id:
            raise ValidationError(_("合同租户与店铺租户不一致"))
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

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.shop_id:
            self.tenant = self.shop.tenant
        super().save(*args, **kwargs)


class ContractItem(models.Model):
    """
    合同费用项（租金/物业费/押金等）
    """

    class ItemType(models.TextChoices):
        RENT = "RENT", _("租金")
        PROPERTY_FEE = "PROPERTY_FEE", _("物业费")
        DEPOSIT = "DEPOSIT", _("押金")
        REVENUE_SHARE = "REVENUE_SHARE", _("分成")
        OTHER = "OTHER", _("其他")

    class CalcType(models.TextChoices):
        FIXED = "FIXED", _("固定值")
        STEP = "STEP", _("阶梯")
        ESCALATION = "ESCALATION", _("递增")
        PERCENTAGE = "PERCENTAGE", _("比例")

    class PaymentCycle(models.TextChoices):
        MONTHLY = "MONTHLY", _("月付")
        QUARTERLY = "QUARTERLY", _("季付")
        SEMIANNUALLY = "SEMIANNUALLY", _("半年付")
        ANNUALLY = "ANNUALLY", _("年付")
        ONE_TIME = "ONE_TIME", _("一次性")

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("启用")
        INACTIVE = "INACTIVE", _("停用")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="contract_items",
        verbose_name=_("租户"),
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="contract_items",
        verbose_name=_("合同"),
    )
    item_type = models.CharField(
        max_length=32,
        choices=ItemType.choices,
        default=ItemType.RENT,
        db_index=True,
        verbose_name=_("费用项类型"),
    )
    calc_type = models.CharField(
        max_length=16,
        choices=CalcType.choices,
        default=CalcType.FIXED,
        verbose_name=_("计费方式"),
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("基础金额"),
    )
    rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name=_("比例/递增率"),
    )
    tax_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name=_("税率"),
    )
    currency = models.CharField(
        max_length=8,
        default="CNY",
        verbose_name=_("币种"),
    )
    period_start = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("费用项起始日期"),
    )
    period_end = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("费用项结束日期"),
    )
    payment_cycle = models.CharField(
        max_length=20,
        choices=PaymentCycle.choices,
        default=PaymentCycle.MONTHLY,
        verbose_name=_("缴费周期"),
    )
    free_rent_from = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("免租开始"),
    )
    free_rent_to = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("免租结束"),
    )
    sequence = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("显示顺序"),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name=_("状态"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("创建时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    objects = TenantManager()

    class Meta:
        verbose_name = _("合同费用项")
        verbose_name_plural = _("合同费用项")
        ordering = ["contract_id", "sequence", "id"]
        indexes = [
            models.Index(fields=["tenant", "contract", "status"]),
            models.Index(fields=["tenant", "item_type"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="contract_item_amount_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__isnull=True)
                | models.Q(period_start__isnull=True)
                | models.Q(period_end__gte=models.F("period_start")),
                name="contract_item_period_valid",
            ),
            models.UniqueConstraint(
                fields=["contract", "sequence"],
                name="contract_item_unique_sequence_per_contract",
            ),
        ]

    def __str__(self):
        return f"{self.contract_id}-{self.item_type}-{self.amount}"

    def clean(self):
        if self.contract_id and self.tenant_id and self.contract.tenant_id != self.tenant_id:
            raise ValidationError(_("费用项租户与合同租户不一致"))

        if self.free_rent_from and self.free_rent_to and self.free_rent_to < self.free_rent_from:
            raise ValidationError(_("免租结束日期不能早于免租开始日期"))

        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError(_("费用项结束日期不能早于开始日期"))

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        self.full_clean()
        super().save(*args, **kwargs)


class ContractAttachment(models.Model):
    """
    合同附件（主合同/补充协议/附件/资质）
    """

    class AttachmentType(models.TextChoices):
        MAIN = "MAIN", _("主合同")
        SUPPLEMENT = "SUPPLEMENT", _("补充协议")
        ANNEX = "ANNEX", _("附件")
        QUALIFICATION = "QUALIFICATION", _("资质文件")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="contract_attachments",
        verbose_name=_("租户"),
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="attachments",
        verbose_name=_("合同"),
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.MAIN,
        db_index=True,
        verbose_name=_("附件类型"),
    )
    file = models.FileField(
        upload_to="contract_attachments/%Y/%m/",
        verbose_name=_("文件"),
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name=_("原始文件名"),
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("文件类型"),
    )
    file_size = models.PositiveIntegerField(
        default=0,
        verbose_name=_("文件大小"),
    )
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name=_("文件哈希"),
    )
    version_no = models.PositiveIntegerField(
        default=1,
        verbose_name=_("版本号"),
    )
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("是否当前版本"),
    )
    remark = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("备注"),
    )
    uploaded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="uploaded_contract_attachments",
        verbose_name=_("上传人"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("上传时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    objects = TenantManager()

    class Meta:
        verbose_name = _("合同附件")
        verbose_name_plural = _("合同附件")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["tenant", "contract", "attachment_type"]),
            models.Index(fields=["tenant", "file_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "attachment_type", "version_no"],
                name="contract_attachment_unique_version",
            ),
        ]

    def __str__(self):
        return f"{self.contract_id}-{self.attachment_type}-v{self.version_no}"

    def clean(self):
        if self.contract_id and self.tenant_id and self.contract.tenant_id != self.tenant_id:
            raise ValidationError(_("合同附件租户与合同租户不一致"))

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        self.full_clean()
        super().save(*args, **kwargs)


class ContractSignature(models.Model):
    """
    合同签署记录
    """

    class PartyType(models.TextChoices):
        LANDLORD = "LANDLORD", _("甲方")
        TENANT = "TENANT", _("乙方")
        WITNESS = "WITNESS", _("见证方")
        OTHER = "OTHER", _("其他")

    class SignMethod(models.TextChoices):
        ONLINE = "ONLINE", _("电子签")
        OFFLINE = "OFFLINE", _("线下签")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="contract_signatures",
        verbose_name=_("租户"),
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="signatures",
        verbose_name=_("合同"),
    )
    party_type = models.CharField(
        max_length=20,
        choices=PartyType.choices,
        default=PartyType.TENANT,
        db_index=True,
        verbose_name=_("签署方"),
    )
    signer_name = models.CharField(
        max_length=100,
        verbose_name=_("签署人"),
    )
    signer_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("职务"),
    )
    sign_method = models.CharField(
        max_length=20,
        choices=SignMethod.choices,
        default=SignMethod.OFFLINE,
        verbose_name=_("签署方式"),
    )
    signed_at = models.DateTimeField(
        db_index=True,
        verbose_name=_("签署时间"),
    )
    attachment = models.ForeignKey(
        ContractAttachment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="signature_records",
        verbose_name=_("关联签署文件"),
    )
    evidence_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_("签署证据哈希"),
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("备注"),
    )
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_contract_signatures",
        verbose_name=_("登记人"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("登记时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    objects = TenantManager()

    class Meta:
        verbose_name = _("合同签署")
        verbose_name_plural = _("合同签署")
        ordering = ["-signed_at", "-id"]
        indexes = [
            models.Index(fields=["tenant", "contract", "signed_at"]),
            models.Index(fields=["tenant", "party_type"]),
        ]

    def __str__(self):
        return f"{self.contract_id}-{self.party_type}-{self.signer_name}"

    def clean(self):
        if self.contract_id and self.tenant_id and self.contract.tenant_id != self.tenant_id:
            raise ValidationError(_("合同签署租户与合同租户不一致"))
        if self.attachment_id and self.attachment.contract_id != self.contract_id:
            raise ValidationError(_("签署附件必须属于同一合同"))

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        self.full_clean()
        super().save(*args, **kwargs)


class ApprovalFlowConfig(models.Model):
    """
    审批流配置（MVP：先支持合同）。
    """

    class TargetType(models.TextChoices):
        CONTRACT = "CONTRACT", _("合同")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="approval_flow_configs",
        verbose_name=_("租户"),
    )
    target_type = models.CharField(
        max_length=32,
        choices=TargetType.choices,
        default=TargetType.CONTRACT,
        db_index=True,
        verbose_name=_("目标类型"),
    )
    node_name = models.CharField(
        max_length=64,
        verbose_name=_("节点名称"),
    )
    order_no = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("节点顺序"),
    )
    approver_role = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name=_("审批角色"),
        help_text=_("可选：ADMIN / MANAGEMENT / OPERATION 等"),
    )
    approver = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approval_flow_config_nodes",
        verbose_name=_("指定审批人"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("是否启用"),
    )
    sla_hours = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("处理时限(小时)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("创建时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    objects = TenantManager()

    class Meta:
        verbose_name = _("审批流配置")
        verbose_name_plural = _("审批流配置")
        ordering = ["target_type", "order_no", "id"]
        indexes = [
            models.Index(fields=["tenant", "target_type", "is_active"]),
            models.Index(fields=["tenant", "approver_role"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "target_type", "order_no"],
                name="approval_flow_unique_order_per_target",
            ),
        ]

    def __str__(self):
        return f"{self.tenant_id}-{self.target_type}-{self.order_no}-{self.node_name}"

    def clean(self):
        if not self.approver and not self.approver_role:
            raise ValidationError(_("必须配置审批角色或指定审批人"))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ApprovalTask(models.Model):
    """
    审批任务实例（由审批流配置生成）。
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("待处理")
        APPROVED = "APPROVED", _("已通过")
        REJECTED = "REJECTED", _("已驳回")
        SKIPPED = "SKIPPED", _("已跳过")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="approval_tasks",
        verbose_name=_("租户"),
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="approval_tasks",
        verbose_name=_("合同"),
    )
    flow_config = models.ForeignKey(
        ApprovalFlowConfig,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approval_tasks",
        verbose_name=_("来源审批配置"),
    )
    round_no = models.PositiveIntegerField(
        default=1,
        verbose_name=_("审批轮次"),
    )
    order_no = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("节点顺序"),
    )
    node_name = models.CharField(
        max_length=64,
        verbose_name=_("节点名称"),
    )
    approver_role = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name=_("审批角色"),
    )
    assigned_to = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_approval_tasks",
        verbose_name=_("分配审批人"),
    )
    acted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="handled_approval_tasks",
        verbose_name=_("实际处理人"),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("任务状态"),
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("审批意见"),
    )
    sla_due_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("节点时限"),
    )
    acted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("处理时间"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("创建时间"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    objects = TenantManager()

    class Meta:
        verbose_name = _("审批任务")
        verbose_name_plural = _("审批任务")
        ordering = ["contract_id", "-round_no", "order_no", "id"]
        indexes = [
            models.Index(fields=["tenant", "contract", "status"]),
            models.Index(fields=["tenant", "assigned_to", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "round_no", "order_no"],
                name="approval_task_unique_contract_round_order",
            ),
        ]

    def __str__(self):
        return f"{self.contract_id}-R{self.round_no}-N{self.order_no}-{self.status}"

    def clean(self):
        if self.contract_id and self.tenant_id and self.contract.tenant_id != self.tenant_id:
            raise ValidationError(_("审批任务租户与合同租户不一致"))
        if self.flow_config_id:
            if self.contract_id and self.flow_config.target_type != ApprovalFlowConfig.TargetType.CONTRACT:
                raise ValidationError(_("审批配置目标类型与合同任务不匹配"))
            if self.tenant_id and self.flow_config.tenant_id != self.tenant_id:
                raise ValidationError(_("审批配置租户与审批任务租户不一致"))

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.contract_id:
            self.tenant = self.contract.tenant
        self.full_clean()
        super().save(*args, **kwargs)
