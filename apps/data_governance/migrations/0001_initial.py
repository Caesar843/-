from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("store", "0005_contract_review_comment_contract_reviewed_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataQualityIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(choices=[("finance", "Finance"), ("contract", "Contract"), ("ops", "Ops")], db_index=True, max_length=20)),
                ("rule_code", models.CharField(max_length=100)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], max_length=20)),
                ("object_type", models.CharField(blank=True, max_length=100, null=True)),
                ("object_id", models.CharField(blank=True, max_length=64, null=True)),
                ("details", models.JSONField(blank=True, null=True)),
                ("detected_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("ignored", "Ignored"), ("resolved", "Resolved")], db_index=True, default="open", max_length=20)),
            ],
            options={
                "verbose_name": "Data Quality Issue",
                "verbose_name_plural": "Data Quality Issue",
            },
        ),
        migrations.CreateModel(
            name="DailyFinanceAgg",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("agg_date", models.DateField(db_index=True)),
                ("month_bucket", models.CharField(db_index=True, max_length=7)),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("rent_paid_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("record_count", models.IntegerField(default=0)),
                ("paid_count", models.IntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="daily_finance_aggs", to="store.shop")),
            ],
            options={
                "verbose_name": "Daily Finance Aggregate",
                "verbose_name_plural": "Daily Finance Aggregate",
            },
        ),
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("scope", models.CharField(db_index=True, max_length=50)),
                ("request_hash", models.CharField(blank=True, max_length=64, null=True)),
                ("object_type", models.CharField(blank=True, max_length=100, null=True)),
                ("object_id", models.CharField(blank=True, max_length=64, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Idempotency Key",
                "verbose_name_plural": "Idempotency Key",
            },
        ),
        migrations.CreateModel(
            name="JobLock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lock_name", models.CharField(max_length=100, unique=True)),
                ("locked_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField()),
                ("owner", models.CharField(blank=True, max_length=100, null=True)),
                ("payload_hash", models.CharField(blank=True, max_length=64, null=True)),
            ],
            options={
                "verbose_name": "Job Lock",
                "verbose_name_plural": "Job Lock",
            },
        ),
        migrations.AddIndex(
            model_name="dataqualityissue",
            index=models.Index(fields=["domain", "severity", "detected_at"], name="data_gover_domain_e99f8c_idx"),
        ),
        migrations.AddConstraint(
            model_name="dataqualityissue",
            constraint=models.UniqueConstraint(fields=("domain", "rule_code", "object_type", "object_id", "status"), name="dq_issue_unique_open"),
        ),
        migrations.AddIndex(
            model_name="dailyfinanceagg",
            index=models.Index(fields=["shop", "agg_date"], name="data_gover_shop_id_93f8a5_idx"),
        ),
        migrations.AddIndex(
            model_name="dailyfinanceagg",
            index=models.Index(fields=["month_bucket", "shop"], name="data_gover_month_b_f27d10_idx"),
        ),
        migrations.AddConstraint(
            model_name="dailyfinanceagg",
            constraint=models.UniqueConstraint(fields=("shop", "agg_date"), name="daily_finance_agg_unique"),
        ),
    ]
