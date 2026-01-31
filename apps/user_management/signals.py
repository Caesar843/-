from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tenants.models import Tenant
from apps.user_management.models import Role, UserProfile, ShopBindingRequest


def _get_default_tenant():
    try:
        return Tenant.objects.get(code="default")
    except Tenant.DoesNotExist:
        return None


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        if instance.is_superuser:
            role = Role.objects.get(role_type=Role.RoleType.ADMIN)
            tenant = None
        else:
            role = Role.objects.get(role_type=Role.RoleType.SHOP)
            tenant = _get_default_tenant()
        UserProfile.objects.create(user=instance, role=role, tenant=tenant)
    except Role.DoesNotExist:
        if instance.is_superuser:
            role = Role.objects.create(role_type=Role.RoleType.ADMIN, name="Admin")
            tenant = None
        else:
            role = Role.objects.create(role_type=Role.RoleType.SHOP, name="Shop")
            tenant = _get_default_tenant()
        UserProfile.objects.create(user=instance, role=role, tenant=tenant)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        try:
            if instance.is_superuser:
                role = Role.objects.get(role_type=Role.RoleType.ADMIN)
                tenant = None
            else:
                role = Role.objects.get(role_type=Role.RoleType.SHOP)
                tenant = _get_default_tenant()
            UserProfile.objects.create(user=instance, role=role, tenant=tenant)
        except Role.DoesNotExist:
            if instance.is_superuser:
                role = Role.objects.create(role_type=Role.RoleType.ADMIN, name="Admin")
                tenant = None
            else:
                role = Role.objects.create(role_type=Role.RoleType.SHOP, name="Shop")
                tenant = _get_default_tenant()
            UserProfile.objects.create(user=instance, role=role, tenant=tenant)


@receiver(post_save, sender=ShopBindingRequest)
def apply_shop_binding(sender, instance, **kwargs):
    if instance.status != ShopBindingRequest.Status.APPROVED:
        return
    if not instance.approved_shop:
        return
    try:
        profile = instance.user.profile
    except UserProfile.DoesNotExist:
        return
    if profile.shop_id != instance.approved_shop_id:
        profile.shop = instance.approved_shop
        profile.save(update_fields=["shop"])
