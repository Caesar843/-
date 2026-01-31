from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.rate_limit_decorators import get_client_ip
from apps.core.verification_service import VerificationCodeService, VerificationBizCode
from apps.core.models import VerificationScene, VerificationChannel
from apps.user_management.models import UserProfile


def _normalize(value):
    return (value or "").strip()


def _find_user_by_identifier(identifier):
    if not identifier:
        return None, None
    User = get_user_model()
    identifier = identifier.strip()
    user = None
    if "@" in identifier:
        user = User.objects.filter(email__iexact=identifier).first()
    if not user:
        user = User.objects.filter(username__iexact=identifier).first()
    if not user:
        profile = UserProfile.objects.select_related("user").filter(phone=identifier).first()
        if profile:
            user = profile.user
    email = getattr(user, "email", None) if user else None
    email = email.strip().lower() if email else None
    return user, email


class VerificationSendView(APIView):
    def post(self, request):
        scene = _normalize(request.data.get("scene"))
        channel = _normalize(request.data.get("channel"))
        destination = _normalize(request.data.get("destination"))
        identifier = _normalize(request.data.get("identifier"))

        client_context = {
            "ip": get_client_ip(request),
            "ua": request.META.get("HTTP_USER_AGENT", ""),
        }

        service = VerificationCodeService()

        if scene == VerificationScene.RESET_PASSWORD:
            user, email = _find_user_by_identifier(identifier)
            if not user:
                if not service._check_ip_rate_limit(scene, client_context.get("ip")):
                    result = service._result(
                        False,
                        VerificationBizCode.RATE_LIMIT,
                        "请求过于频繁，请稍后再试。",
                        cooldown_seconds=service.cooldown_seconds,
                    )
                else:
                    result = service._result(
                        True,
                        VerificationBizCode.OK,
                        "如果账号存在，我们已发送验证码到绑定邮箱。",
                    )
                return Response(result.__dict__)
            if not email:
                result = service._result(
                    False,
                    VerificationBizCode.NOT_ALLOWED,
                    "该账号未绑定邮箱，无法重置密码。",
                )
                return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)
            result = service.send_code(scene, VerificationChannel.EMAIL, email, client_context)
            if result.success:
                result.message = f"验证码已发送至绑定邮箱 {result.masked_destination}。"
            return Response(result.__dict__)

        if scene == VerificationScene.REGISTER:
            if channel not in [VerificationChannel.EMAIL, VerificationChannel.SMS]:
                result = service._result(
                    False,
                    VerificationBizCode.NOT_ALLOWED,
                    "请选择邮箱或手机号接收验证码。",
                )
                return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)
            result = service.send_code(scene, channel, destination, client_context)
            return Response(result.__dict__)

        result = service._result(False, VerificationBizCode.NOT_ALLOWED, "无效的场景。")
        return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)


class VerificationVerifyView(APIView):
    def post(self, request):
        scene = _normalize(request.data.get("scene"))
        channel = _normalize(request.data.get("channel"))
        destination = _normalize(request.data.get("destination"))
        identifier = _normalize(request.data.get("identifier"))
        code = _normalize(request.data.get("code"))

        client_context = {
            "ip": get_client_ip(request),
            "ua": request.META.get("HTTP_USER_AGENT", ""),
        }

        service = VerificationCodeService()

        if scene == VerificationScene.RESET_PASSWORD:
            user, email = _find_user_by_identifier(identifier)
            if not user:
                result = service._result(
                    True,
                    VerificationBizCode.OK,
                    "如果账号存在，我们已发送验证码到绑定邮箱。",
                )
                return Response(result.__dict__)
            if not email:
                result = service._result(
                    False,
                    VerificationBizCode.NOT_ALLOWED,
                    "该账号未绑定邮箱，无法重置密码。",
                )
                return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)
            result = service.verify_code(
                scene,
                VerificationChannel.EMAIL,
                email,
                code,
                client_context,
            )
            if result.success:
                result.reset_token = service.issue_reset_token_for_user(user)
            return Response(result.__dict__)

        if scene == VerificationScene.REGISTER:
            if channel not in [VerificationChannel.EMAIL, VerificationChannel.SMS]:
                result = service._result(
                    False,
                    VerificationBizCode.NOT_ALLOWED,
                    "请选择邮箱或手机号接收验证码。",
                )
                return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)
            result = service.verify_code(
                scene,
                channel,
                destination,
                code,
                client_context,
                issue_ticket=True,
            )
            return Response(result.__dict__)

        result = service._result(False, VerificationBizCode.NOT_ALLOWED, "无效的场景。")
        return Response(result.__dict__, status=status.HTTP_400_BAD_REQUEST)


class VerificationStatusView(APIView):
    def get(self, request):
        scene = _normalize(request.query_params.get("scene"))
        channel = _normalize(request.query_params.get("channel"))
        destination = _normalize(request.query_params.get("destination"))
        identifier = _normalize(request.query_params.get("identifier"))

        service = VerificationCodeService()

        if scene == VerificationScene.RESET_PASSWORD:
            user, email = _find_user_by_identifier(identifier)
            if not user or not email:
                return Response(
                    {
                        "success": True,
                        "cooldown_seconds": 0,
                        "biz_code": VerificationBizCode.OK,
                        "message": "OK",
                    }
                )
            cooldown = service.check_cooldown(scene, VerificationChannel.EMAIL, email)
            return Response(
                {
                    "success": True,
                    "cooldown_seconds": cooldown,
                    "biz_code": VerificationBizCode.OK,
                    "message": "OK",
                }
            )

        if scene == VerificationScene.REGISTER:
            if channel not in [VerificationChannel.EMAIL, VerificationChannel.SMS]:
                return Response(
                    {
                        "success": False,
                        "cooldown_seconds": 0,
                        "biz_code": VerificationBizCode.NOT_ALLOWED,
                        "message": "无效的接收方式。",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cooldown = service.check_cooldown(scene, channel, destination)
            return Response(
                {
                    "success": True,
                    "cooldown_seconds": cooldown,
                    "biz_code": VerificationBizCode.OK,
                    "message": "OK",
                }
            )

        return Response(
            {
                "success": False,
                "cooldown_seconds": 0,
                "biz_code": VerificationBizCode.NOT_ALLOWED,
                "message": "无效的场景。",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerificationResetPasswordView(APIView):
    def post(self, request):
        token = _normalize(request.data.get("reset_token"))
        password1 = _normalize(request.data.get("password1"))
        password2 = _normalize(request.data.get("password2"))

        if not token:
            return Response(
                {
                    "success": False,
                    "biz_code": VerificationBizCode.NOT_ALLOWED,
                    "message": "缺少重置令牌。",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password1 or not password2:
            return Response(
                {
                    "success": False,
                    "biz_code": VerificationBizCode.NOT_ALLOWED,
                    "message": "请填写新密码。",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if password1 != password2:
            return Response(
                {
                    "success": False,
                    "biz_code": VerificationBizCode.NOT_ALLOWED,
                    "message": "两次输入的密码不一致。",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = VerificationCodeService()
        token_record = service.verify_reset_token(token)
        if not token_record:
            return Response(
                {
                    "success": False,
                    "biz_code": VerificationBizCode.INVALID,
                    "message": "重置令牌已失效，请重新申请。",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token_record.user
        try:
            validate_password(password1, user=user)
        except ValidationError as exc:
            return Response(
                {
                    "success": False,
                    "biz_code": VerificationBizCode.NOT_ALLOWED,
                    "message": "密码不符合要求。",
                    "details": exc.messages,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password1)
        user.save(update_fields=["password"])
        service.consume_reset_token(token_record)

        return Response(
            {
                "success": True,
                "biz_code": VerificationBizCode.OK,
                "message": "密码已重置，请重新登录。",
            }
        )
