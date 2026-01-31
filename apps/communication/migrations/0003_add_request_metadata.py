from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("communication", "0002_add_processing_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancerequest",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="Optional attachment",
                null=True,
                upload_to="requests/maintenance/",
                verbose_name="Attachment",
            ),
        ),
        migrations.AddField(
            model_name="maintenancerequest",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Request applicant",
                null=True,
                on_delete=models.SET_NULL,
                related_name="maintenance_requests",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Applicant",
            ),
        ),
        migrations.AddField(
            model_name="activityapplication",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="Optional attachment",
                null=True,
                upload_to="requests/activity/",
                verbose_name="Attachment",
            ),
        ),
        migrations.AddField(
            model_name="activityapplication",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Request applicant",
                null=True,
                on_delete=models.SET_NULL,
                related_name="activity_applications",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Applicant",
            ),
        ),
    ]
