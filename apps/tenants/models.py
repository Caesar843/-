from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.tenants.managers import TenantManager


class Tenant(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Tenant Name"))
    code = models.SlugField(max_length=50, unique=True, verbose_name=_("Tenant Code"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrgUnit(models.Model):
    class UnitType(models.TextChoices):
        MALL = "mall", _("Mall")
        REGION = "region", _("Region")
        FLOOR = "floor", _("Floor")
        DEPT = "dept", _("Department")
        OTHER = "other", _("Other")

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="org_units",
        verbose_name=_("Tenant"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    unit_type = models.CharField(
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.OTHER,
        verbose_name=_("Unit Type"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Unit"),
    )
    path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Path"),
        help_text=_("Optional path for faster tree queries."),
    )
    level = models.PositiveIntegerField(default=0, verbose_name=_("Level"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    objects = TenantManager()

    class Meta:
        verbose_name = _("Org Unit")
        verbose_name_plural = _("Org Units")
        indexes = [
            models.Index(fields=["tenant", "parent"]),
            models.Index(fields=["tenant", "unit_type"]),
        ]
        ordering = ["tenant_id", "level", "name"]

    def __str__(self):
        return f"{self.name} ({self.tenant})"
