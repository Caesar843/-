from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import VerificationCodeRecord, VerificationScene, VerificationChannel
from apps.core.verification_service import VerificationCodeService, VerificationBizCode


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class VerificationServiceTests(TestCase):
    def setUp(self):
        self.service = VerificationCodeService()

    def test_verify_success_consumes_code(self):
        record = VerificationCodeRecord.objects.create(
            scene=VerificationScene.REGISTER,
            channel=VerificationChannel.EMAIL,
            destination="test@example.com",
            code_hash=self.service._hash_code("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        result = self.service.verify_code(
            VerificationScene.REGISTER,
            VerificationChannel.EMAIL,
            "test@example.com",
            "123456",
            {"ip": "127.0.0.1", "ua": "test"},
            issue_ticket=True,
        )
        record.refresh_from_db()
        self.assertTrue(result.success)
        self.assertIsNone(record.code_hash)
        self.assertIsNotNone(result.verification_token)

    def test_verify_invalid_locks_after_limit(self):
        record = VerificationCodeRecord.objects.create(
            scene=VerificationScene.REGISTER,
            channel=VerificationChannel.EMAIL,
            destination="lock@example.com",
            code_hash=self.service._hash_code("654321"),
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        last = None
        for _ in range(self.service.verify_fail_limit):
            last = self.service.verify_code(
                VerificationScene.REGISTER,
                VerificationChannel.EMAIL,
                "lock@example.com",
                "000000",
                {"ip": "127.0.0.1", "ua": "test"},
            )
        record.refresh_from_db()
        self.assertEqual(last.biz_code, VerificationBizCode.LOCKED)
        self.assertIsNotNone(record.lock_until)

    def test_consume_verification_ticket(self):
        token = self.service._issue_verification_ticket(
            VerificationScene.REGISTER,
            VerificationChannel.EMAIL,
            "ticket@example.com",
        )
        ok = self.service.consume_verification_ticket(
            VerificationScene.REGISTER,
            VerificationChannel.EMAIL,
            "ticket@example.com",
            token,
        )
        self.assertTrue(ok)

    def test_reset_token_flow(self):
        user = get_user_model().objects.create_user(username="u1", password="pass1234", email="u1@example.com")
        token = self.service.issue_reset_token_for_user(user)
        record = self.service.verify_reset_token(token)
        self.assertIsNotNone(record)
        self.service.consume_reset_token(record)
        record.refresh_from_db()
        self.assertIsNotNone(record.used_at)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class VerificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_send_register_email(self):
        resp = self.client.post(
            "/api/core/verification/send/",
            {
                "scene": VerificationScene.REGISTER,
                "channel": VerificationChannel.EMAIL,
                "destination": "api@example.com",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("success", resp.data)

    def test_reset_send_unknown_identifier(self):
        resp = self.client.post(
            "/api/core/verification/send/",
            {"scene": VerificationScene.RESET_PASSWORD, "identifier": "missing@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])

    def test_reset_verify_unknown_identifier(self):
        resp = self.client.post(
            "/api/core/verification/verify/",
            {"scene": VerificationScene.RESET_PASSWORD, "identifier": "missing@example.com", "code": "123456"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])

    def test_reset_password_requires_token(self):
        resp = self.client.post(
            "/api/core/verification/reset-password/",
            {"password1": "NewPass123!", "password2": "NewPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["biz_code"], VerificationBizCode.NOT_ALLOWED)

    def test_status_register(self):
        resp = self.client.get(
            "/api/core/verification/status/",
            {"scene": VerificationScene.REGISTER, "channel": VerificationChannel.EMAIL, "destination": "status@example.com"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("cooldown_seconds", resp.data)
