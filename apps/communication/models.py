from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.store.models import Shop


class MaintenanceRequest(models.Model):
    """
    维修请求模型
    ----------
    [业务属性]
    - shop: 关联店铺
    - title: 标题
    - description: 描述
    - request_type: 请求类型
    - priority: 优先级
    - status: 状态
    - assigned_to: 指派人员
    - estimated_cost: 预估费用
    - actual_cost: 实际费用
    - completion_date: 完成日期
    - created_at: 创建时间
    - updated_at: 更新时间
    """

    # 请求类型枚举
    class RequestType(models.TextChoices):
        WATER = 'WATER', _('水电故障')
        EQUIPMENT = 'EQUIPMENT', _('设备维修')
        FACILITY = 'FACILITY', _('设施维护')
        OTHER = 'OTHER', _('其他')

    # 优先级枚举
    class Priority(models.TextChoices):
        LOW = 'LOW', _('低')
        MEDIUM = 'MEDIUM', _('中')
        HIGH = 'HIGH', _('高')
        URGENT = 'URGENT', _('紧急')

    # 状态枚举
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('待处理')
        ASSIGNED = 'ASSIGNED', _('已指派')
        IN_PROGRESS = 'IN_PROGRESS', _('处理中')
        COMPLETED = 'COMPLETED', _('已完成')
        CANCELLED = 'CANCELLED', _('已取消')

    # 业务字段
    shop = models.ForeignKey(
        Shop,
        verbose_name=_("店铺"),
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
        help_text=_("提交请求的店铺")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Applicant"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="maintenance_requests",
        help_text=_("Request applicant")
    )
    title = models.CharField(
        verbose_name=_("标题"),
        max_length=200,
        help_text=_("维修请求标题")
    )
    description = models.TextField(
        verbose_name=_("描述"),
        help_text=_("维修请求详细描述")
    )
    attachment = models.FileField(
        verbose_name=_("Attachment"),
        upload_to="requests/maintenance/",
        blank=True,
        null=True,
        help_text=_("Optional attachment")
    )
    request_type = models.CharField(
        verbose_name=_("请求类型"),
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.OTHER,
        help_text=_("维修请求类型")
    )
    priority = models.CharField(
        verbose_name=_("优先级"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_("维修请求优先级")
    )
    status = models.CharField(
        verbose_name=_("状态"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("维修请求状态")
    )
    assigned_to = models.CharField(
        verbose_name=_("指派人员"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("处理该请求的人员")
    )
    handled_by = models.CharField(
        verbose_name=_("处理人员"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("最终处理请求的人员")
    )
    handled_at = models.DateTimeField(
        verbose_name=_("处理时间"),
        blank=True,
        null=True,
        help_text=_("处理该请求的时间")
    )
    handling_notes = models.TextField(
        verbose_name=_("处理意见"),
        blank=True,
        null=True,
        help_text=_("处理意见与备注")
    )
    estimated_cost = models.DecimalField(
        verbose_name=_("预估费用"),
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("预估维修费用")
    )
    actual_cost = models.DecimalField(
        verbose_name=_("实际费用"),
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("实际维修费用")
    )
    completion_date = models.DateField(
        verbose_name=_("完成日期"),
        blank=True,
        null=True,
        help_text=_("维修完成日期")
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
        verbose_name = _("维修请求")
        verbose_name_plural = _("维修请求")
        ordering = ["-created_at"]

    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.title} ({self.status})"

    def clean(self):
        """模型级验证"""
        # 实际费用必须大于等于0
        if self.actual_cost is not None:
            if self.actual_cost < 0:
                raise ValidationError(_("实际费用必须大于等于0"))

        # 预估费用必须大于等于0
        if self.estimated_cost is not None:
            if self.estimated_cost < 0:
                raise ValidationError(_("预估费用必须大于等于0"))


class ActivityApplication(models.Model):
    """
    活动申请模型
    ----------
    [业务属性]
    - shop: 关联店铺
    - title: 标题
    - description: 描述
    - activity_type: 活动类型
    - start_date: 开始日期
    - end_date: 结束日期
    - location: 场地位置
    - participants: 预计参与人数
    - status: 状态
    - reviewer: 审核人员
    - review_comments: 审核意见
    - created_at: 创建时间
    - updated_at: 更新时间
    """

    # 活动类型枚举
    class ActivityType(models.TextChoices):
        PROMOTION = 'PROMOTION', _('促销活动')
        ADVERTISING = 'ADVERTISING', _('广告投放')
        EVENT = 'EVENT', _('专题活动')
        OTHER = 'OTHER', _('其他')

    # 状态枚举
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('待审核')
        APPROVED = 'APPROVED', _('已批准')
        REJECTED = 'REJECTED', _('已拒绝')
        CANCELLED = 'CANCELLED', _('已取消')

    # 业务字段
    shop = models.ForeignKey(
        Shop,
        verbose_name=_("店铺"),
        on_delete=models.CASCADE,
        related_name="activity_applications",
        help_text=_("提交申请的店铺")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Applicant"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="activity_applications",
        help_text=_("Request applicant")
    )
    title = models.CharField(
        verbose_name=_("标题"),
        max_length=200,
        help_text=_("活动申请标题")
    )
    description = models.TextField(
        verbose_name=_("描述"),
        help_text=_("活动申请详细描述")
    )
    attachment = models.FileField(
        verbose_name=_("Attachment"),
        upload_to="requests/activity/",
        blank=True,
        null=True,
        help_text=_("Optional attachment")
    )
    activity_type = models.CharField(
        verbose_name=_("活动类型"),
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.OTHER,
        help_text=_("活动类型")
    )
    start_date = models.DateTimeField(
        verbose_name=_("开始日期"),
        help_text=_("活动开始日期和时间")
    )
    end_date = models.DateTimeField(
        verbose_name=_("结束日期"),
        help_text=_("活动结束日期和时间")
    )
    location = models.CharField(
        verbose_name=_("场地位置"),
        max_length=200,
        help_text=_("活动场地位置")
    )
    participants = models.IntegerField(
        verbose_name=_("预计参与人数"),
        help_text=_("预计参与活动的人数")
    )
    status = models.CharField(
        verbose_name=_("状态"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_("活动申请状态")
    )
    reviewer = models.CharField(
        verbose_name=_("审核人员"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("审核该申请的人员")
    )
    review_comments = models.TextField(
        verbose_name=_("审核意见"),
        blank=True,
        null=True,
        help_text=_("审核意见和备注")
    )
    reviewed_at = models.DateTimeField(
        verbose_name=_("审核时间"),
        blank=True,
        null=True,
        help_text=_("审核处理时间")
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
        verbose_name = _("活动申请")
        verbose_name_plural = _("活动申请")
        ordering = ["-created_at"]

    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.title} ({self.status})"

    def clean(self):
        """模型级验证"""
        # 结束日期必须晚于开始日期
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError(_("结束日期必须晚于开始日期"))

        # 参与人数必须大于0
        if self.participants is not None:
            if self.participants <= 0:
                raise ValidationError(_("参与人数必须大于0"))


class ProcessLog(models.Model):
    """
    流程日志模型
    ----------
    [业务属性]
    - content_type: 关联模型类型
    - object_id: 关联对象ID
    - action: 操作类型
    - description: 描述
    - operator: 操作人
    - created_at: 创建时间
    """

    # 操作类型枚举
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('创建')
        UPDATE = 'UPDATE', _('更新')
        ASSIGN = 'ASSIGN', _('指派')
        APPROVE = 'APPROVE', _('批准')
        REJECT = 'REJECT', _('拒绝')
        COMPLETE = 'COMPLETE', _('完成')
        CANCEL = 'CANCEL', _('取消')
        COMMENT = 'COMMENT', _('评论')

    # 业务字段
    content_type = models.CharField(
        verbose_name=_("模型类型"),
        max_length=100,
        help_text=_("关联的模型类型")
    )
    object_id = models.IntegerField(
        verbose_name=_("对象ID"),
        help_text=_("关联的对象ID")
    )
    action = models.CharField(
        verbose_name=_("操作类型"),
        max_length=20,
        choices=ActionType.choices,
        help_text=_("操作类型")
    )
    description = models.TextField(
        verbose_name=_("描述"),
        help_text=_("操作描述和详情")
    )
    operator = models.CharField(
        verbose_name=_("操作人"),
        max_length=100,
        help_text=_("执行操作的人员")
    )

    # 审计字段
    created_at = models.DateTimeField(
        verbose_name=_("创建时间"),
        auto_now_add=True
    )

    class Meta:
        """元数据"""
        verbose_name = _("流程日志")
        verbose_name_plural = _("流程日志")
        ordering = ["-created_at"]

    def __str__(self):
        """字符串表示"""
        return f"{self.content_type} #{self.object_id} - {self.action} - {self.created_at}"


