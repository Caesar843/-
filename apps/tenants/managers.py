from django.db import models
from apps.tenants.context import get_current_tenant


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if tenant is None:
            return self
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = get_current_tenant()
        if tenant is None:
            return queryset
        return queryset.filter(tenant=tenant)

    def for_tenant(self, tenant):
        queryset = super().get_queryset()
        if tenant is None:
            return queryset
        return queryset.filter(tenant=tenant)
