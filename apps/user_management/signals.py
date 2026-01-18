from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

from apps.user_management.models import UserProfile, Role


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    当用户创建时自动创建用户配置文件
    """
    if created:
        # 尝试获取默认角色（如果存在）
        try:
            # 新创建的用户默认为店铺角色，除非是超级用户
            if instance.is_superuser:
                role = Role.objects.get(role_type=Role.RoleType.SUPER_ADMIN)
            else:
                role = Role.objects.get(role_type=Role.RoleType.SHOP)
            
            UserProfile.objects.create(user=instance, role=role)
        except Role.DoesNotExist:
            # 如果角色不存在，先创建默认角色，再创建用户配置文件
            if instance.is_superuser:
                role = Role.objects.create(
                    role_type=Role.RoleType.SUPER_ADMIN,
                    name='超级管理员'
                )
            else:
                role = Role.objects.create(
                    role_type=Role.RoleType.SHOP,
                    name='入驻店铺'
                )
            
            UserProfile.objects.create(user=instance, role=role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    当用户保存时自动保存用户配置文件
    """
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # 如果配置文件不存在，创建一个
        try:
            if instance.is_superuser:
                role = Role.objects.get(role_type=Role.RoleType.SUPER_ADMIN)
            else:
                role = Role.objects.get(role_type=Role.RoleType.SHOP)
            
            UserProfile.objects.create(user=instance, role=role)
        except Role.DoesNotExist:
            if instance.is_superuser:
                role = Role.objects.create(
                    role_type=Role.RoleType.SUPER_ADMIN,
                    name='超级管理员'
                )
            else:
                role = Role.objects.create(
                    role_type=Role.RoleType.SHOP,
                    name='入驻店铺'
                )
            
            UserProfile.objects.create(user=instance, role=role)
