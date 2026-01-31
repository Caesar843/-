from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """
    角色模型
    --------
    定义系统中的角色类型
    """
    
    class RoleType(models.TextChoices):
        """Role type choices"""
        SHOP = 'SHOP', _('Shop')
        OPERATION = 'OPERATION', _('Operation')
        FINANCE = 'FINANCE', _('Finance')
        MANAGEMENT = 'MANAGEMENT', _('Management')
        ADMIN = 'ADMIN', _('Admin')

    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        unique=True,
        verbose_name=_('角色类型'),
        help_text=_('系统预定义的角色类型')
    )
    
    name = models.CharField(
        max_length=50,
        verbose_name=_('角色名称'),
        help_text=_('角色的显示名称')
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('角色描述'),
        help_text=_('角色的详细描述')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间')
    )
    
    class Meta:
        verbose_name = _('角色')
        verbose_name_plural = _('角色')
        ordering = ['role_type']
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    用户配置文件模型
    ----------------
    扩展 Django 内置的 User 模型，添加角色和其他属性
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('用户')
    )
    
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        verbose_name=_('角色'),
        help_text=_('用户所属的角色')
    )

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='user_profiles',
        verbose_name=_('所属租户'),
        help_text=_('用户所属的租户/商场')
    )
    
    shop = models.ForeignKey(
        'store.Shop',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='users',
        verbose_name=_('关联店铺'),
        help_text=_('仅入驻店铺角色需要关联具体店铺')
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('联系电话'),
        help_text=_('用户的联系电话')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间')
    )
    
    class Meta:
        verbose_name = _('用户配置文件')
        verbose_name_plural = _('用户配置文件')
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class ObjectPermissionGrant(models.Model):
    """
    Object-level permission grant.
    Allows assigning actions to a specific object for a user or role,
    with optional time-bound validity.
    """

    class ActionChoices(models.TextChoices):
        VIEW = "view", _("View")
        EDIT = "edit", _("Edit")
        APPROVE = "approve", _("Approve")
        DELETE = "delete", _("Delete")

    grantee_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="object_permission_grants",
        verbose_name=_("Grantee User"),
        help_text=_("User who receives the permission grant."),
    )
    grantee_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="object_permission_grants",
        verbose_name=_("Grantee Role"),
        help_text=_("Role that receives the permission grant."),
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
    )
    object_id = models.PositiveBigIntegerField(verbose_name=_("Object ID"))
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(
        max_length=20,
        choices=ActionChoices.choices,
        verbose_name=_("Action"),
        help_text=_("Action allowed on the target object."),
    )
    scope = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name=_("Scope"),
        help_text=_("Optional scope hint (region/shop/contract)."),
    )

    valid_from = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Valid From"),
    )
    valid_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Valid Until"),
    )

    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="granted_object_permissions",
        verbose_name=_("Granted By"),
    )
    reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Reason"),
        help_text=_("Reason or remark for the grant."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        verbose_name = _("Object Permission Grant")
        verbose_name_plural = _("Object Permission Grants")
        indexes = [
            models.Index(fields=["content_type", "object_id", "action"]),
            models.Index(fields=["grantee_user", "action"]),
            models.Index(fields=["grantee_role", "action"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(grantee_user__isnull=False)
                    | models.Q(grantee_role__isnull=False)
                ),
                name="object_permission_grant_has_grantee",
            )
        ]

    def __str__(self):
        subject = self.grantee_user or self.grantee_role
        return f"{subject} -> {self.action} {self.content_type}:{self.object_id}"


class ApprovalRecord(models.Model):
    """
    Approval/audit trail for sensitive actions.
    """

    class ActionChoices(models.TextChoices):
        APPROVE_CONTRACT = "approve_contract", _("Approve Contract")
        TERMINATE_CONTRACT = "terminate_contract", _("Terminate Contract")
        FINANCE_CONFIRM = "finance_confirm", _("Finance Confirm")
        SHOP_STATUS_CHANGE = "shop_status_change", _("Shop Status Change")

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
    )
    object_id = models.PositiveBigIntegerField(verbose_name=_("Object ID"))
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(
        max_length=50,
        choices=ActionChoices.choices,
        verbose_name=_("Action"),
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_records",
        verbose_name=_("Approved By"),
    )
    approved_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Approved At"),
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Comment"),
    )
    signature_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_("Signature Hash"),
    )
    request_snapshot = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Request Snapshot"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        verbose_name = _("Approval Record")
        verbose_name_plural = _("Approval Records")
        indexes = [
            models.Index(fields=["content_type", "object_id", "action"]),
            models.Index(fields=["approved_by", "approved_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.content_type}:{self.object_id}"


class ShopBindingRequest(models.Model):
    """
    店铺绑定申请
    SHOP 用户提交申请，管理员审核后绑定到具体店铺。
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("待审核")
        APPROVED = "APPROVED", _("已批准")
        REJECTED = "REJECTED", _("已拒绝")

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="shop_binding_request",
        verbose_name=_("用户"),
    )
    requested_shop_name = models.CharField(
        max_length=120,
        verbose_name=_("申请店铺名称"),
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("联系电话"),
    )
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("备注"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("状态"),
    )
    approved_shop = models.ForeignKey(
        "store.Shop",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="binding_requests",
        verbose_name=_("审核通过店铺"),
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_binding_requests",
        verbose_name=_("审核人"),
    )
    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("审核时间"),
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
        verbose_name = _("店铺绑定申请")
        verbose_name_plural = _("店铺绑定申请")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"

    def clean(self):
        if self.status == self.Status.APPROVED and not self.approved_shop:
            raise ValidationError(_("批准时必须选择店铺"))
