from django.db import migrations, models
import django.db.models.deletion


def backfill_tenants(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    Shop = apps.get_model("store", "Shop")
    Contract = apps.get_model("store", "Contract")

    try:
        default_tenant = Tenant.objects.get(code="default")
    except Tenant.DoesNotExist:
        default_tenant = None

    if default_tenant:
        Shop.objects.filter(tenant__isnull=True).update(tenant=default_tenant)

    contracts = Contract.objects.select_related("shop")
    for contract in contracts:
        if contract.tenant_id:
            continue
        if contract.shop_id and contract.shop.tenant_id:
            contract.tenant_id = contract.shop.tenant_id
        elif default_tenant:
            contract.tenant_id = default_tenant.id
        contract.save(update_fields=["tenant"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_create_default_tenant"),
        ("store", "0005_contract_review_comment_contract_reviewed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="shops",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.AddField(
            model_name="shop",
            name="org_unit",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shops",
                to="tenants.orgunit",
                verbose_name="组织单元",
            ),
        ),
        migrations.AlterField(
            model_name="shop",
            name="name",
            field=models.CharField(max_length=100, verbose_name="店铺名称"),
        ),
        migrations.AddField(
            model_name="contract",
            name="tenant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contracts",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.RunPython(backfill_tenants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="shop",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="shops",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.AlterField(
            model_name="contract",
            name="tenant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contracts",
                to="tenants.tenant",
                verbose_name="租户",
            ),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["tenant", "is_deleted"], name="store_shop_tenant__289da5_idx"),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["tenant", "name"], name="store_shop_tenant__e31dd4_idx"),
        ),
        migrations.AddConstraint(
            model_name="shop",
            constraint=models.UniqueConstraint(fields=("tenant", "name"), name="shop_unique_name_per_tenant"),
        ),
        migrations.AddIndex(
            model_name="contract",
            index=models.Index(fields=["tenant", "status"], name="store_contract_tenant__d3a2b1_idx"),
        ),
        migrations.AddIndex(
            model_name="contract",
            index=models.Index(fields=["tenant", "created_at"], name="store_contract_tenant__09f918_idx"),
        ),
    ]
