from django.conf import settings
from django.db import models
from django.utils import timezone


class VerificationScene(models.TextChoices):
    REGISTER = "REGISTER", "Register"
    RESET_PASSWORD = "RESET_PASSWORD", "Reset Password"


class VerificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class VerificationCodeRecord(models.Model):
    scene = models.CharField(max_length=30, choices=VerificationScene.choices)
    channel = models.CharField(max_length=10, choices=VerificationChannel.choices)
    destination = models.CharField(max_length=255)

    code_hash = models.CharField(max_length=64, blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    cooldown_until = models.DateTimeField(blank=True, null=True)

    send_count_hourly = models.PositiveIntegerField(default=0)
    send_count_daily = models.PositiveIntegerField(default=0)
    hour_window_start = models.DateTimeField(blank=True, null=True)
    day_window_start = models.DateTimeField(blank=True, null=True)

    verify_fail_count = models.PositiveIntegerField(default=0)
    lock_until = models.DateTimeField(blank=True, null=True)

    last_request_id = models.CharField(max_length=64, blank=True, null=True)
    last_sent_at = models.DateTimeField(blank=True, null=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("scene", "channel", "destination")
        indexes = [
            models.Index(fields=["scene", "channel", "destination"]),
            models.Index(fields=["destination"]),
        ]

    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())


class VerificationResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_reset_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["expires_at"]),
        ]
