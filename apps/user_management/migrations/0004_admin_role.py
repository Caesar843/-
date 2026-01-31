from django.db import migrations


def migrate_admin_role(apps, schema_editor):
    Role = apps.get_model("user_management", "Role")
    Role.objects.filter(role_type="SUPER_ADMIN").update(role_type="ADMIN", name="Admin")
    Role.objects.get_or_create(
        role_type="ADMIN",
        defaults={"name": "Admin", "description": "System administrator with full access."},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("user_management", "0003_userprofile_tenant"),
    ]

    operations = [
        migrations.RunPython(migrate_admin_role, migrations.RunPython.noop),
    ]
