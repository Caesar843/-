from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Tenant Name")),
                ("code", models.SlugField(max_length=50, unique=True, verbose_name="Tenant Code")),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
            ],
            options={
                "verbose_name": "Tenant",
                "verbose_name_plural": "Tenants",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="OrgUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                ("unit_type", models.CharField(choices=[("mall", "Mall"), ("region", "Region"), ("floor", "Floor"), ("dept", "Department"), ("other", "Other")], default="other", max_length=20, verbose_name="Unit Type")),
                ("path", models.CharField(blank=True, help_text="Optional path for faster tree queries.", max_length=255, null=True, verbose_name="Path")),
                ("level", models.PositiveIntegerField(default=0, verbose_name="Level")),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="tenants.orgunit", verbose_name="Parent Unit")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="org_units", to="tenants.tenant", verbose_name="Tenant")),
            ],
            options={
                "verbose_name": "Org Unit",
                "verbose_name_plural": "Org Units",
                "ordering": ["tenant_id", "level", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="orgunit",
            index=models.Index(fields=["tenant", "parent"], name="tenants_org_tenant__c22241_idx"),
        ),
        migrations.AddIndex(
            model_name="orgunit",
            index=models.Index(fields=["tenant", "unit_type"], name="tenants_org_tenant__b7fe7f_idx"),
        ),
    ]
