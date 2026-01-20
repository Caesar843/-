from django.db import migrations, models
import django.db.models.deletion


def assign_default_tenant(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("user_management", "UserProfile")

    try:
        default_tenant = Tenant.objects.get(code="default")
    except Tenant.DoesNotExist:
        default_tenant = None

    if default_tenant is None:
        return

    profiles = UserProfile.objects.select_related("user")
    for profile in profiles:
        if profile.tenant_id:
            continue
        if profile.user_id and User.objects.filter(id=profile.user_id, is_superuser=True).exists():
            continue
        profile.tenant = default_tenant
        profile.save(update_fields=["tenant"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_create_default_tenant"),
        ("user_management", "0002_object_permissions_and_approvals"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="user_profiles",
                to="tenants.tenant",
                verbose_name="所属租户",
            ),
        ),
        migrations.RunPython(assign_default_tenant, migrations.RunPython.noop),
    ]
