from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """
    角色模型
    --------
    定义系统中的角色类型
    """
    
    class RoleType(models.TextChoices):
        """角色类型枚举"""
        SHOP = 'SHOP', _('入驻店铺')
        OPERATION = 'OPERATION', _('商场运营专员')
        FINANCE = 'FINANCE', _('财务管理员')
        MANAGEMENT = 'MANAGEMENT', _('商场管理层')
        SUPER_ADMIN = 'SUPER_ADMIN', _('超级管理员')
    
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
