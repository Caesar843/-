from django.db import migrations


def create_default_tenant(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    Tenant.objects.get_or_create(
        code="default",
        defaults={
            "name": "default",
            "is_active": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_tenant, migrations.RunPython.noop),
    ]
