import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.core.models import (
    VerificationCodeRecord,
    VerificationResetToken,
    VerificationScene,
    VerificationChannel,
)
from apps.notification.services import NotificationService
from apps.notification.models import SMSRecord
from django.core.mail import send_mail, BadHeaderError


class VerificationBizCode:
    OK = "OK"
    RATE_LIMIT = "RATE_LIMIT"
    LOCKED = "LOCKED"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"
    NOT_ALLOWED = "NOT_ALLOWED"
    NOT_FOUND = "NOT_FOUND"
    SEND_FAILED = "SEND_FAILED"


@dataclass
class VerificationResult:
    success: bool
    biz_code: str
    message: str
    cooldown_seconds: int = 0
    expires_in_seconds: int = 0
    request_id: Optional[str] = None
    masked_destination: Optional[str] = None
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None


class VerificationCodeService:
    def __init__(self):
        self.code_ttl = int(getattr(settings, "VERIFICATION_CODE_TTL_SECONDS", 600))
        self.cooldown_seconds = int(getattr(settings, "VERIFICATION_COOLDOWN_SECONDS", 60))
        self.send_limit_hourly = int(getattr(settings, "VERIFICATION_SEND_LIMIT_HOURLY", 5))
        self.send_limit_daily = int(getattr(settings, "VERIFICATION_SEND_LIMIT_DAILY", 20))
        self.verify_fail_limit = int(getattr(settings, "VERIFICATION_VERIFY_FAIL_LIMIT", 5))
        self.lock_seconds = int(getattr(settings, "VERIFICATION_LOCK_SECONDS", 600))
        self.ip_limit_hourly = int(getattr(settings, "VERIFICATION_IP_LIMIT_HOURLY", 20))
        self.register_ticket_ttl = int(getattr(settings, "VERIFICATION_REGISTER_TICKET_TTL_SECONDS", 600))
        self.reset_token_ttl = int(getattr(settings, "VERIFICATION_RESET_TOKEN_TTL_SECONDS", 600))

    def send_code(self, scene, channel, destination, client_context):
        start = time.monotonic()
        request_id = self._request_id()
        now = timezone.now()
        destination = self._normalize_destination(destination)
        masked_destination = self._mask_destination(channel, destination)

        if not destination:
            return self._result(
                False,
                VerificationBizCode.NOT_ALLOWED,
                "请填写有效的接收地址。",
                request_id=request_id,
            )

        if not self._check_ip_rate_limit(scene, client_context.get("ip")):
            return self._result(
                False,
                VerificationBizCode.RATE_LIMIT,
                "请求过于频繁，请稍后再试。",
                cooldown_seconds=self.cooldown_seconds,
                request_id=request_id,
            )

        record, _ = VerificationCodeRecord.objects.get_or_create(
            scene=scene,
            channel=channel,
            destination=destination,
        )
        cooldown_seconds = self._remaining_seconds(record.cooldown_until, now)
        if cooldown_seconds > 0:
            return self._result(
                False,
                VerificationBizCode.RATE_LIMIT,
                "发送过于频繁，请稍后再试。",
                cooldown_seconds=cooldown_seconds,
                request_id=request_id,
                masked_destination=masked_destination,
            )

        if not self._allow_send_by_count(record, now):
            cooldown_seconds = max(self._seconds_to_hour_reset(record, now), 60)
            return self._result(
                False,
                VerificationBizCode.RATE_LIMIT,
                "发送次数过多，请稍后再试。",
                cooldown_seconds=cooldown_seconds,
                request_id=request_id,
                masked_destination=masked_destination,
            )

        code = f"{secrets.randbelow(1000000):06d}"
        record.code_hash = self._hash_code(code)
        record.expires_at = now + timezone.timedelta(seconds=self.code_ttl)
        record.cooldown_until = now + timezone.timedelta(seconds=self.cooldown_seconds)
        record.last_request_id = request_id
        record.last_sent_at = now
        self._increment_send_counters(record, now)

        send_ok, send_error = self._send_via_channel(channel, destination, code, scene)
        if not send_ok:
            record.save(update_fields=[
                "code_hash",
                "expires_at",
                "cooldown_until",
                "last_request_id",
                "last_sent_at",
                "send_count_hourly",
                "send_count_daily",
                "hour_window_start",
                "day_window_start",
            ])
            self._log_action("send_failed", scene, channel, masked_destination, client_context, request_id, start)
            return self._result(
                False,
                VerificationBizCode.SEND_FAILED,
                "验证码发送失败，请稍后再试。",
                request_id=request_id,
                masked_destination=masked_destination,
            )

        record.save(update_fields=[
            "code_hash",
            "expires_at",
            "cooldown_until",
            "last_request_id",
            "last_sent_at",
            "send_count_hourly",
            "send_count_daily",
            "hour_window_start",
            "day_window_start",
        ])
        self._log_action("send_ok", scene, channel, masked_destination, client_context, request_id, start)
        message = "???????"
        if (
            channel == VerificationChannel.SMS
            and getattr(settings, "DEBUG", False)
            and getattr(settings, "VERIFICATION_DEBUG_ECHO_CODE", False)
        ):
            message = f"Verification code sent (dev): {code}"

        return self._result(
            True,
            VerificationBizCode.OK,
            message,
            cooldown_seconds=self.cooldown_seconds,
            expires_in_seconds=self.code_ttl,
            request_id=request_id,
            masked_destination=masked_destination,
        )


    def verify_code(self, scene, channel, destination, code, client_context, issue_ticket=False, issue_reset=False):
        start = time.monotonic()
        request_id = self._request_id()
        now = timezone.now()
        destination = self._normalize_destination(destination)
        masked_destination = self._mask_destination(channel, destination)

        record = VerificationCodeRecord.objects.filter(
            scene=scene,
            channel=channel,
            destination=destination,
        ).first()
        if not record or not record.code_hash:
            self._log_action("verify_missing", scene, channel, masked_destination, client_context, request_id, start)
            return self._result(False, VerificationBizCode.INVALID, "验证码无效。", request_id=request_id)

        locked_seconds = self._remaining_seconds(record.lock_until, now)
        if locked_seconds > 0:
            return self._result(
                False,
                VerificationBizCode.LOCKED,
                "验证失败次数过多，请稍后再试。",
                cooldown_seconds=locked_seconds,
                request_id=request_id,
            )

        if record.expires_at and record.expires_at < now:
            self._log_action("verify_expired", scene, channel, masked_destination, client_context, request_id, start)
            return self._result(False, VerificationBizCode.EXPIRED, "验证码已过期。", request_id=request_id)

        if not self._constant_time_compare(record.code_hash, self._hash_code(code)):
            record.verify_fail_count += 1
            if record.verify_fail_count >= self.verify_fail_limit:
                record.lock_until = now + timezone.timedelta(seconds=self.lock_seconds)
            record.save(update_fields=["verify_fail_count", "lock_until"])
            self._log_action("verify_invalid", scene, channel, masked_destination, client_context, request_id, start)
            if record.lock_until and record.lock_until > now:
                return self._result(
                    False,
                    VerificationBizCode.LOCKED,
                    "验证失败次数过多，请稍后再试。",
                    cooldown_seconds=self.lock_seconds,
                    request_id=request_id,
                )
            return self._result(False, VerificationBizCode.INVALID, "验证码错误。", request_id=request_id)

        record.code_hash = None
        record.expires_at = None
        record.verify_fail_count = 0
        record.lock_until = None
        record.last_verified_at = now
        record.save(update_fields=["code_hash", "expires_at", "verify_fail_count", "lock_until", "last_verified_at"])
        self._log_action("verify_ok", scene, channel, masked_destination, client_context, request_id, start)

        result = self._result(True, VerificationBizCode.OK, "验证码验证通过。", request_id=request_id)
        if issue_ticket:
            result.verification_token = self._issue_verification_ticket(scene, channel, destination)
        if issue_reset:
            result.reset_token = self._issue_reset_token(destination)
        return result

    def consume_verification_ticket(self, scene, channel, destination, token):
        destination = self._normalize_destination(destination)
        if not token or not destination:
            return False
        key = self._ticket_key(scene, channel, destination)
        token_hash = cache.get(key)
        if not token_hash:
            return False
        if not self._constant_time_compare(token_hash, self._hash_token(token)):
            return False
        cache.delete(key)
        return True

    def check_cooldown(self, scene, channel, destination):
        destination = self._normalize_destination(destination)
        now = timezone.now()
        record = VerificationCodeRecord.objects.filter(
            scene=scene,
            channel=channel,
            destination=destination,
        ).first()
        if not record:
            return 0
        return self._remaining_seconds(record.cooldown_until, now)

    def issue_reset_token_for_user(self, user):
        token = self._random_token()
        token_hash = self._hash_token(token)
        now = timezone.now()
        VerificationResetToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=now + timezone.timedelta(seconds=self.reset_token_ttl),
        )
        return token

    def verify_reset_token(self, token):
        if not token:
            return None
        token_hash = self._hash_token(token)
        now = timezone.now()
        record = VerificationResetToken.objects.filter(
            token_hash=token_hash,
            used_at__isnull=True,
            expires_at__gt=now,
        ).select_related("user").first()
        return record

    def consume_reset_token(self, token_record):
        token_record.used_at = timezone.now()
        token_record.save(update_fields=["used_at"])

    def _send_via_channel(self, channel, destination, code, scene):
        try:
            if channel == VerificationChannel.EMAIL:
                if settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"):
                    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                        return False, "EMAIL_NOT_CONFIGURED"
                subject = "验证码"
                message = f"您的验证码是：{code}，有效期 {int(self.code_ttl / 60)} 分钟。"
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [destination],
                    fail_silently=False,
                )
                return True, None
            if channel == VerificationChannel.SMS:
                content = f"您的验证码是：{code}，有效期 {int(self.code_ttl / 60)} 分钟。"
                sms_record = NotificationService.send_sms(destination, content)
                if sms_record.status != SMSRecord.Status.SENT:
                    return False, sms_record.error_message or "SMS_FAILED"
                return True, None
        except (BadHeaderError, Exception) as exc:
            return False, str(exc)
        return False, "unsupported channel"

    def _issue_verification_ticket(self, scene, channel, destination):
        token = self._random_token()
        cache.set(
            self._ticket_key(scene, channel, destination),
            self._hash_token(token),
            timeout=self.register_ticket_ttl,
        )
        return token

    def _issue_reset_token(self, destination):
        return None

    def _check_ip_rate_limit(self, scene, ip):
        if not ip:
            return True
        key = f"verification:ip:{scene}:{ip}"
        current = cache.get(key)
        if current is None:
            cache.set(key, 1, timeout=3600)
            return True
        if current >= self.ip_limit_hourly:
            return False
        cache.incr(key)
        return True

    def _allow_send_by_count(self, record, now):
        if not record.hour_window_start or (now - record.hour_window_start).total_seconds() >= 3600:
            record.hour_window_start = now
            record.send_count_hourly = 0
        if not record.day_window_start or (now - record.day_window_start).total_seconds() >= 86400:
            record.day_window_start = now
            record.send_count_daily = 0
        if record.send_count_hourly >= self.send_limit_hourly:
            return False
        if record.send_count_daily >= self.send_limit_daily:
            return False
        return True

    def _increment_send_counters(self, record, now):
        if not record.hour_window_start or (now - record.hour_window_start).total_seconds() >= 3600:
            record.hour_window_start = now
            record.send_count_hourly = 0
        if not record.day_window_start or (now - record.day_window_start).total_seconds() >= 86400:
            record.day_window_start = now
            record.send_count_daily = 0
        record.send_count_hourly += 1
        record.send_count_daily += 1

    @staticmethod
    def _seconds_to_hour_reset(record, now):
        if not record.hour_window_start:
            return 0
        elapsed = (now - record.hour_window_start).total_seconds()
        return max(0, int(3600 - elapsed))

    @staticmethod
    def _remaining_seconds(dt, now):
        if not dt:
            return 0
        remaining = (dt - now).total_seconds()
        return max(0, int(remaining))

    @staticmethod
    def _normalize_destination(destination):
        if not destination:
            return ""
        return str(destination).strip().lower()

    @staticmethod
    def _hash_code(code):
        return hashlib.sha256(f"{code}{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_token(token):
        return hashlib.sha256(f"{token}{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

    @staticmethod
    def _random_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def _ticket_key(scene, channel, destination):
        return f"verification:ticket:{scene}:{channel}:{destination}"

    @staticmethod
    def _request_id():
        return uuid.uuid4().hex

    @staticmethod
    def _constant_time_compare(a, b):
        if a is None or b is None:
            return False
        return secrets.compare_digest(a, b)

    @staticmethod
    def _mask_destination(channel, destination):
        if not destination:
            return ""
        if channel == VerificationChannel.EMAIL and "@" in destination:
            name, domain = destination.split("@", 1)
            if len(name) <= 1:
                masked = "*"
            else:
                masked = name[0] + "***"
            return f"{masked}@{domain}"
        if channel == VerificationChannel.SMS:
            if len(destination) <= 4:
                return destination[0] + "***"
            return f"{destination[:3]}****{destination[-2:]}"
        return destination

    def _log_action(self, action, scene, channel, masked_destination, client_context, request_id, start):
        elapsed = int((time.monotonic() - start) * 1000)
        logger = self._logger()
        logger.info(
            "verification_event",
            extra={
                "action": action,
                "scene": scene,
                "channel": channel,
                "destination": masked_destination,
                "ip": client_context.get("ip"),
                "ua": client_context.get("ua"),
                "request_id": request_id,
                "elapsed_ms": elapsed,
            },
        )

    @staticmethod
    def _logger():
        import logging
        return logging.getLogger(__name__)

    @staticmethod
    def _result(success, biz_code, message, cooldown_seconds=0, expires_in_seconds=0, request_id=None, masked_destination=None):
        return VerificationResult(
            success=success,
            biz_code=biz_code,
            message=message,
            cooldown_seconds=cooldown_seconds,
            expires_in_seconds=expires_in_seconds,
            request_id=request_id,
            masked_destination=masked_destination,
        )
