from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VerificationCodeRecord",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scene", models.CharField(choices=[("REGISTER", "Register"), ("RESET_PASSWORD", "Reset Password")], max_length=30)),
                ("channel", models.CharField(choices=[("EMAIL", "Email"), ("SMS", "SMS")], max_length=10)),
                ("destination", models.CharField(max_length=255)),
                ("code_hash", models.CharField(blank=True, max_length=64, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("cooldown_until", models.DateTimeField(blank=True, null=True)),
                ("send_count_hourly", models.PositiveIntegerField(default=0)),
                ("send_count_daily", models.PositiveIntegerField(default=0)),
                ("hour_window_start", models.DateTimeField(blank=True, null=True)),
                ("day_window_start", models.DateTimeField(blank=True, null=True)),
                ("verify_fail_count", models.PositiveIntegerField(default=0)),
                ("lock_until", models.DateTimeField(blank=True, null=True)),
                ("last_request_id", models.CharField(blank=True, max_length=64, null=True)),
                ("last_sent_at", models.DateTimeField(blank=True, null=True)),
                ("last_verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "unique_together": {("scene", "channel", "destination")},
            },
        ),
        migrations.CreateModel(
            name="VerificationResetToken",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification_reset_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="verificationcoderecord",
            index=models.Index(fields=["scene", "channel", "destination"], name="core_verif_scene_channel_dest_idx"),
        ),
        migrations.AddIndex(
            model_name="verificationcoderecord",
            index=models.Index(fields=["destination"], name="core_verif_destination_idx"),
        ),
        migrations.AddIndex(
            model_name="verificationresettoken",
            index=models.Index(fields=["token_hash"], name="core_verif_token_hash_idx"),
        ),
        migrations.AddIndex(
            model_name="verificationresettoken",
            index=models.Index(fields=["expires_at"], name="core_verif_token_expires_idx"),
        ),
    ]
