from django.db import migrations, models
import django.db.models.deletion


def backfill_tenant(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    FinanceRecord = apps.get_model("finance", "FinanceRecord")

    try:
        default_tenant = Tenant.objects.get(code="default")
    except Tenant.DoesNotExist:
        default_tenant = None

    records = FinanceRecord.objects.select_related("contract")
    for record in records:
        if record.tenant_id:
            continue
        if record.contract_id and getattr(record.contract, "tenant_id", None):
            record.tenant_id = record.contract.tenant_id
        elif default_tenant:
            record.tenant_id = default_tenant.id
        record.save(update_fields=["tenant"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_create_default_tenant"),
        ("finance", "0003_financerecord_reminder_sent"),
    ]

    operations = [
        migrations.AddField(
            model_name="financerecord",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="finance_records",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.RunPython(backfill_tenant, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="financerecord",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="finance_records",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.AddIndex(
            model_name="financerecord",
            index=models.Index(fields=["tenant", "status"], name="finance_fin_tenant__de50f2_idx"),
        ),
        migrations.AddIndex(
            model_name="financerecord",
            index=models.Index(fields=["tenant", "billing_period_end"], name="finance_fin_tenant__5f4c1b_idx"),
        ),
    ]
