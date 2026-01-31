from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_shop_contract_tenant_orgunit"),
        ("user_management", "0004_admin_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShopBindingRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_shop_name", models.CharField(max_length=120, verbose_name="申请店铺名称")),
                ("contact_phone", models.CharField(blank=True, max_length=20, null=True, verbose_name="联系电话")),
                ("note", models.TextField(blank=True, null=True, verbose_name="备注")),
                ("status", models.CharField(choices=[("PENDING", "待审核"), ("APPROVED", "已批准"), ("REJECTED", "已拒绝")], default="PENDING", max_length=20, verbose_name="状态")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="审核时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("approved_shop", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="binding_requests", to="store.shop", verbose_name="审核通过店铺")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_binding_requests", to=settings.AUTH_USER_MODEL, verbose_name="审核人")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="shop_binding_request", to=settings.AUTH_USER_MODEL, verbose_name="用户")),
            ],
            options={
                "verbose_name": "店铺绑定申请",
                "verbose_name_plural": "店铺绑定申请",
                "ordering": ["-created_at"],
            },
        ),
    ]
