from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from django.utils import timezone


class NotificationTemplate(models.Model):
    """
    通知模板
    支持系统消息、短信、邮件等多种类型
    """
    
    class Type(models.TextChoices):
        SYSTEM = 'SYSTEM', _('系统消息')
        SMS = 'SMS', _('短信')
        EMAIL = 'EMAIL', _('邮件')
        PUSH = 'PUSH', _('推送消息')
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_('模板名称'))
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
        verbose_name=_('通知类型')
    )
    title = models.CharField(max_length=200, verbose_name=_('标题'))
    content = models.TextField(verbose_name=_('内容模板'))
    # 用于支持变量替换的字段列表（逗号分隔）
    variables = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('模板变量'),
        help_text=_('示例: shop_name,contract_id,amount')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('是否激活'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))
    
    class Meta:
        verbose_name = _('通知模板')
        verbose_name_plural = _('通知模板')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Notification(models.Model):
    """
    通知消息
    用于跟踪系统生成的所有通知
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('待发送')
        SENT = 'SENT', _('已发送')
        FAILED = 'FAILED', _('发送失败')
        READ = 'READ', _('已读')
    
    class Type(models.TextChoices):
        CONTRACT_SUBMITTED = 'CONTRACT_SUBMITTED', _('合同提交审核')
        CONTRACT_APPROVED = 'CONTRACT_APPROVED', _('合同已批准')
        CONTRACT_REJECTED = 'CONTRACT_REJECTED', _('合同已拒绝')
        PAYMENT_REMINDER = 'PAYMENT_REMINDER', _('支付提醒')
        PAYMENT_OVERDUE = 'PAYMENT_OVERDUE', _('支付逾期')
        RENEWAL_REMINDER = 'RENEWAL_REMINDER', _('续签提醒')
        MAINTENANCE_REQUEST = 'MAINTENANCE_REQUEST', _('维修请求')
        ACTIVITY_REQUEST = 'ACTIVITY_REQUEST', _('活动申请')
        SYSTEM_ALERT = 'SYSTEM_ALERT', _('系统告警')
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('收件人')
    )
    notification_type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.SYSTEM_ALERT,
        verbose_name=_('通知类型')
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('使用的模板')
    )
    title = models.CharField(max_length=200, verbose_name=_('标题'))
    content = models.TextField(verbose_name=_('内容'))
    
    # 业务关联字段
    related_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('关联业务模型'),
        help_text=_('示例: Contract, FinanceRecord')
    )
    related_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('关联业务对象ID')
    )
    
    # 通知状态和渠道
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('状态')
    )
    
    # 通知记录
    is_read = models.BooleanField(default=False, verbose_name=_('是否已读'))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_('已读时间'))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_('发送时间'))
    failed_reason = models.TextField(blank=True, null=True, verbose_name=_('失败原因'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))
    
    class Meta:
        verbose_name = _('通知消息')
        verbose_name_plural = _('通知消息')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"
    
    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class SMSRecord(models.Model):
    """
    短信发送记录
    用于跟踪短信发送状态和第三方服务集成
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('待发送')
        SENT = 'SENT', _('已发送')
        FAILED = 'FAILED', _('发送失败')
        DELIVERED = 'DELIVERED', _('已送达')
    
    phone_number = models.CharField(max_length=20, verbose_name=_('收件手机号'))
    content = models.TextField(verbose_name=_('短信内容'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('状态')
    )
    
    # 第三方服务信息
    provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('短信服务商'),
        help_text=_('示例: ALIYUN, TENCENT, CUSTOM')
    )
    provider_msg_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('服务商消息ID')
    )
    
    # 业务关联
    notification = models.OneToOneField(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_record',
        verbose_name=_('关联通知')
    )
    related_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('关联业务模型')
    )
    related_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('关联业务对象ID')
    )
    
    # 错误信息
    error_message = models.TextField(blank=True, null=True, verbose_name=_('错误信息'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_('发送时间'))
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name=_('送达时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))
    
    class Meta:
        verbose_name = _('短信记录')
        verbose_name_plural = _('短信记录')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['phone_number', '-created_at']),
        ]
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.get_status_display()}"


class NotificationPreference(models.Model):
    """
    用户通知偏好设置
    允许用户自定义通知接收方式和频率
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preference',
        verbose_name=_('用户')
    )
    
    # 通知类型开关
    enable_system_notification = models.BooleanField(default=True, verbose_name=_('启用系统消息'))
    enable_sms_notification = models.BooleanField(default=True, verbose_name=_('启用短信通知'))
    enable_email_notification = models.BooleanField(default=False, verbose_name=_('启用邮件通知'))
    
    # 通知频率控制
    sms_enabled_hours = models.CharField(
        max_length=50,
        default='09:00-21:00',
        verbose_name=_('短信启用时间'),
        help_text=_('示例: 09:00-21:00 表示仅9点到21点发送短信')
    )
    
    # 通知内容偏好
    notify_contract_events = models.BooleanField(default=True, verbose_name=_('合同事件通知'))
    notify_payment_events = models.BooleanField(default=True, verbose_name=_('支付事件通知'))
    notify_maintenance_events = models.BooleanField(default=True, verbose_name=_('维修事件通知'))
    notify_activity_events = models.BooleanField(default=False, verbose_name=_('活动事件通知'))
    
    # 支付提醒相关
    payment_reminder_days = models.PositiveIntegerField(
        default=3,
        verbose_name=_('提前提醒天数'),
        help_text=_('在支付截止前多少天发送提醒，默认3天')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))
    
    class Meta:
        verbose_name = _('通知偏好')
        verbose_name_plural = _('通知偏好')
    
    def __str__(self):
        return f"Notification preference of {self.user.username}"
