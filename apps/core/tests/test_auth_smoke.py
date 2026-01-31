from django.test import TestCase
from django.contrib.auth.models import User


class AuthSmokeTests(TestCase):
    def test_login_required_redirects_to_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/core/login/", response["Location"])

    def test_register_success_creates_user(self):
        response = self.client.post(
            "/core/register/",
            data={
                "username": "shop_user_1",
                "password1": "S3curePass!234",
                "password2": "S3curePass!234",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="shop_user_1").exists())

    def test_login_success_redirects(self):
        User.objects.create_user(username="login_user", password="S3curePass!234")
        response = self.client.post(
            "/core/login/",
            data={"username": "login_user", "password": "S3curePass!234"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("/dashboard/"))
