from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("communication", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancerequest",
            name="handled_by",
            field=models.CharField(
                blank=True,
                help_text="最终处理请求的人员",
                max_length=100,
                null=True,
                verbose_name="处理人员",
            ),
        ),
        migrations.AddField(
            model_name="maintenancerequest",
            name="handled_at",
            field=models.DateTimeField(
                blank=True,
                help_text="处理该请求的时间",
                null=True,
                verbose_name="处理时间",
            ),
        ),
        migrations.AddField(
            model_name="maintenancerequest",
            name="handling_notes",
            field=models.TextField(
                blank=True,
                help_text="处理意见与备注",
                null=True,
                verbose_name="处理意见",
            ),
        ),
        migrations.AddField(
            model_name="activityapplication",
            name="reviewed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="审核处理时间",
                null=True,
                verbose_name="审核时间",
            ),
        ),
    ]
