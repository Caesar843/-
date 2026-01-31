from django.urls import path

from apps.core import verification_views

urlpatterns = [
    path("verification/send/", verification_views.VerificationSendView.as_view(), name="verification_send"),
    path("verification/verify/", verification_views.VerificationVerifyView.as_view(), name="verification_verify"),
    path("verification/status/", verification_views.VerificationStatusView.as_view(), name="verification_status"),
    path("verification/reset-password/", verification_views.VerificationResetPasswordView.as_view(), name="verification_reset_password"),
]
