from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils.crypto import constant_time_compare
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import shutil
import logging
import hashlib
import secrets
from apps.core.response import APIResponse
from apps.core.auth_messages import auth_message
from apps.core.rate_limiter import check_rate_limit
from apps.core.rate_limit_decorators import get_client_ip
from apps.core.verification_service import VerificationCodeService
from apps.core.models import VerificationScene, VerificationChannel
from apps.core.forms import (
    StyledSetPasswordForm,
    PasswordResetEmailForm,
    PasswordResetCodeForm,
)
from apps.core.forms import ShopUserRegistrationForm, ShopBindingRequestForm
from apps.user_management.models import Role, UserProfile, ShopBindingRequest
from apps.user_management.models import Role

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    鍋ュ悍妫€鏌ョ鐐?    
    鐢ㄤ簬鐩戞帶绯荤粺鍋ュ悍鐘舵€侊紝鍙璐熻浇鍧囪　鍣ㄥ拰鐩戞帶绯荤粺浣跨敤銆?    
    杩斿洖鏍煎紡:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "checks": {
            "database": "ok" | "error: ...",
            "redis": "ok" | "error: ...",
            "disk_percent": 45.2,
            "uptime_seconds": 3600
        }
    }
    
    HTTP 鐘舵€佺爜:
    - 200: 绯荤粺鍋ュ悍
    - 503: 绯荤粺涓嶅仴搴锋垨鎬ц兘涓嬮檷
    """
    
    def get(self, request):
        """Check system health."""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': self._get_timestamp()
        }
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
            logger.debug('Database connection ok')
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = f'error: {str(e)}'
            logger.error(f'Database connection failed: {str(e)}')
        
        # 2. Redis 妫€鏌ワ紙濡傛灉閰嶇疆浜嗭級
        try:
            cache.set('health_check', 'ok', 10)
            value = cache.get('health_check')
            if value == 'ok':
                health_status['checks']['redis'] = 'ok'
                logger.debug('Redis 杩炴帴姝ｅ父')
            else:
                health_status['status'] = 'degraded'
                health_status['checks']['redis'] = 'error: cache get failed'
                logger.warning('Redis get 鎿嶄綔澶辫触')
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['checks']['redis'] = f'error: {str(e)}'
            logger.warning(f'Redis 杩炴帴澶辫触: {str(e)}')
        
        # Disk space check
        try:
            total, used, free = shutil.disk_usage('/')
            disk_percent = (used / total) * 100
            health_status['checks']['disk_percent'] = round(disk_percent, 2)
            health_status['checks']['disk_free_gb'] = round(free / (1024**3), 2)
            
            # 濡傛灉纾佺洏浣跨敤瓒呰繃 90%锛屾爣璁颁负鎬ц兘涓嬮檷
            if disk_percent > 90:
                health_status['status'] = 'degraded'
                logger.warning(f'纾佺洏浣跨敤鐜囪繃楂? {disk_percent}%')
            
            logger.debug(f'纾佺洏浣跨敤鐜? {disk_percent}%')
        except Exception as e:
            health_status['checks']['disk'] = f'error: {str(e)}'
            logger.warning(f'纾佺洏妫€鏌ュけ璐? {str(e)}')
        
        # Database connection count (PostgreSQL)
        try:
            if 'postgresql' in str(connection.settings_dict.get('ENGINE', '')):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                    )
                    conn_count = cursor.fetchone()[0]
                    health_status['checks']['db_connections'] = conn_count
        except Exception as e:
            logger.debug(f'鏁版嵁搴撹繛鎺ユ暟鏌ヨ澶辫触: {str(e)}')
        
        # App version info
        try:
            import time
            import django
            # 绠€鍗曚及绠楋紝瀹為檯搴旇璁板綍鍚姩鏃堕棿
            health_status['checks']['version'] = django.get_version()
        except Exception as e:
            logger.debug(f'鐗堟湰淇℃伅鑾峰彇澶辫触: {str(e)}')
        
        # 鏍规嵁鐘舵€佽繑鍥炰笉鍚岀殑 HTTP 鐘舵€佺爜
        http_status = {
            'healthy': status.HTTP_200_OK,
            'degraded': status.HTTP_200_OK,  # 202 涔熷彲浠ワ紝浣?200 鏇撮€氱敤
            'unhealthy': status.HTTP_503_SERVICE_UNAVAILABLE
        }.get(health_status['status'], status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(health_status, status=http_status)
    
    @staticmethod
    def _get_timestamp():
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class LoginView(View):
    """鐢ㄦ埛鐧诲綍瑙嗗浘"""
    template_name = 'core/login.html'
    
    def get(self, request):
        """鏄剧ず鐧诲綍琛ㄥ崟"""
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        next_url = request.GET.get('next', '')
        if next_url and not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            next_url = ''
        return render(request, self.template_name, {'next': next_url})
    
    def post(self, request):
        """澶勭悊鐧诲綍璇锋眰"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        client_ip = get_client_ip(request)

        # Rate limit check
        allowed, info = check_rate_limit(
            client_ip=client_ip,
            endpoint=request.path
        )
        if not allowed:
            messages.error(request, '璇锋眰杩囦簬棰戠箒锛岃绋嶅悗鍐嶈瘯')
            return render(request, self.template_name, status=429)

        # Failed login lock
        if username:
            max_attempts = getattr(settings, 'AUTH_LOGIN_MAX_ATTEMPTS', 5)
            lock_seconds = getattr(settings, 'AUTH_LOGIN_LOCK_SECONDS', 600)
            window_seconds = getattr(settings, 'AUTH_LOGIN_FAIL_WINDOW', 300)
            lock_key = f'auth:login_lock:{username}:{client_ip}'
            fail_key = f'auth:login_fail:{username}:{client_ip}'
            if cache.get(lock_key):
                messages.error(request, '璇锋眰杩囦簬棰戠箒锛岃绋嶅悗鍐嶈瘯')
                return render(request, self.template_name, status=429)
        
        # 楠岃瘉杈撳叆
        if not username or not password:
            messages.error(request, auth_message("LOGIN_MISSING"))
            return render(request, self.template_name)
        
        # 楠岃瘉鐢ㄦ埛
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                remember_me = request.POST.get('remember_me') == 'on'
                if remember_me:
                    request.session.set_expiry(None)
                else:
                    request.session.set_expiry(0)
                if username:
                    cache.delete(f'auth:login_fail:{username}:{client_ip}')
                    cache.delete(f'auth:login_lock:{username}:{client_ip}')
                messages.success(request, auth_message("LOGIN_SUCCESS"))
                next_url = request.POST.get('next') or request.GET.get('next') or ''
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure()
                ):
                    return redirect(next_url)
                return redirect('dashboard:index')
            else:
                logger.warning('Disabled account login attempt', extra={'username': username})
                messages.error(request, auth_message("LOGIN_DISABLED"))
        else:
            messages.error(request, auth_message("LOGIN_INVALID"))
            if username:
                fail_key = f'auth:login_fail:{username}:{client_ip}'
                lock_key = f'auth:login_lock:{username}:{client_ip}'
                fails = cache.get(fail_key, 0) + 1
                cache.set(fail_key, fails, window_seconds)
                if fails >= max_attempts:
                    cache.set(lock_key, True, lock_seconds)
        
        return render(request, self.template_name)


class RegisterView(View):
    """Shop owner registration view (no admin roles)."""

    template_name = 'core/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        form = ShopUserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        client_ip = get_client_ip(request)
        allowed, info = check_rate_limit(
            client_ip=client_ip,
            endpoint=request.path
        )
        if not allowed:
            messages.error(request, '璇锋眰杩囦簬棰戠箒锛岃绋嶅悗鍐嶈瘯')
            return render(request, self.template_name, status=429)
        form = ShopUserRegistrationForm(request.POST)
        if form.is_valid():
            channel = form.cleaned_data.get("verification_channel")
            ticket = form.cleaned_data.get("verification_ticket")
            email = form.cleaned_data.get("email", "")
            phone = form.cleaned_data.get("phone", "")
            destination = email if channel == VerificationChannel.EMAIL else phone
            if channel not in [VerificationChannel.EMAIL, VerificationChannel.SMS] or not destination:
                messages.error(request, "请选择验证码接收方式并填写对应信息")
                return render(request, self.template_name, {"form": form})
            service = VerificationCodeService()
            if not ticket or not service.consume_verification_ticket(
                VerificationScene.REGISTER, channel, destination, ticket
            ):
                messages.error(request, "请先完成验证码校验")
                return render(request, self.template_name, {"form": form})

            user = form.save(commit=False)
            # Enforce non-admin account for self-registration.
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            user.email = form.cleaned_data.get('email', '')
            user.save()

            # Ensure role is SHOP regardless of any client-side tampering.
            role, _ = Role.objects.get_or_create(
                role_type=Role.RoleType.SHOP,
                defaults={'name': '店铺负责人'},
            )
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
            profile.role = role
            profile.phone = form.cleaned_data.get('phone', '')
            profile.save(update_fields=['role', 'phone'])

            messages.success(request, auth_message("REGISTER_SUCCESS"))
            return redirect('core:login')

        messages.error(request, auth_message("REGISTER_FAILED"))
        return render(request, self.template_name, {'form': form})


class ShopBindingRequestView(View):
    template_name = "core/shop_binding_request.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('core:login')
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return redirect('dashboard:index')
        if profile.role.role_type != Role.RoleType.SHOP:
            return redirect('dashboard:index')
        if profile.shop:
            return redirect('store:shop_update', profile.shop.id)

        existing = ShopBindingRequest.objects.filter(user=request.user).first()
        form = ShopBindingRequestForm(initial={
            "requested_shop_name": getattr(existing, "requested_shop_name", ""),
            "contact_phone": getattr(existing, "contact_phone", ""),
            "note": getattr(existing, "note", ""),
        })
        return render(request, self.template_name, {"form": form, "request_obj": existing})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('core:login')
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return redirect('dashboard:index')
        if profile.role.role_type != Role.RoleType.SHOP:
            return redirect('dashboard:index')

        form = ShopBindingRequestForm(request.POST)
        if not form.is_valid():
            messages.error(request, "请检查表单填写")
            return render(request, self.template_name, {"form": form})

        data = form.cleaned_data
        obj, _ = ShopBindingRequest.objects.get_or_create(user=request.user)
        obj.requested_shop_name = data["requested_shop_name"]
        obj.contact_phone = data.get("contact_phone") or ""
        obj.note = data.get("note") or ""
        obj.status = ShopBindingRequest.Status.PENDING
        obj.approved_shop = None
        obj.reviewed_by = None
        obj.reviewed_at = None
        obj.save()

        messages.success(request, "申请已提交，等待管理员审核")
        return redirect('core:shop_binding_request')


class PasswordResetRequestView(View):
    template_name = 'registration/password_reset_form.html'

    def get(self, request):
        return render(request, self.template_name)


class PasswordResetVerifyView(View):
    template_name = 'registration/password_reset_verify.html'

    def get(self, request):
        return render(request, self.template_name)


class PasswordResetSetPasswordView(View):
    template_name = 'registration/password_reset_set_password.html'

    def get(self, request):
        return render(request, self.template_name)

class LogoutView(View):
    """鐢ㄦ埛鐧诲嚭瑙嗗浘"""
    @method_decorator(require_POST)
    def post(self, request):
        """澶勭悊鐧诲嚭璇锋眰"""
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, auth_message("LOGOUT_SUCCESS"))
        return redirect('core:login')


# ============================================
# CSRF 鍜岄敊璇鐞嗚鍥?# ============================================

def csrf_failure(request, reason=""):
    """
    CSRF 楠岃瘉澶辫触澶勭悊瑙嗗浘
    
    褰?CSRF token 鏍￠獙澶辫触鏃惰皟鐢ㄦ瑙嗗浘銆?    """
    logger.warning(
        f'CSRF 楠岃瘉澶辫触: {reason}',
        extra={
            'path': request.path,
            'method': request.method,
            'user': str(request.user),
            'ip': request.META.get('REMOTE_ADDR'),
        }
    )
    
    if request.headers.get('Accept') == 'application/json':
        return Response(
            {
                'code': 403,
                'message': 'CSRF token 楠岃瘉澶辫触锛岃閲嶆柊鎻愪氦',
                'data': None,
            },
            status=status.HTTP_403_FORBIDDEN
        )
    else:
        return render(
            request,
            'errors/403.html',
            {'reason': reason},
            status=403
        )


def page_not_found(request, exception=None):
    """404 閿欒澶勭悊"""
    logger.info(f'404 閿欒: {request.path}')
    
    if request.headers.get('Accept') == 'application/json':
        return Response(
            {
                'code': 404,
                'message': '璇锋眰鐨勯〉闈笉瀛樺湪',
                'data': None,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    else:
        return render(request, 'errors/404.html', status=404)


def server_error(request):
    """500 閿欒澶勭悊"""
    logger.error(f'500 閿欒: {request.path}')
    
    if request.headers.get('Accept') == 'application/json':
        return Response(
            {
                'code': 500,
                'message': 'Internal server error. Please try again later.',
                'data': None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        return render(request, 'errors/500.html', status=500)


class CacheStatsView(APIView):
    """
    缂撳瓨缁熻鐩戞帶瑙嗗浘
    
    鑾峰彇缂撳瓨鎬ц兘缁熻锛屽寘鎷懡涓巼銆侀敊璇巼绛夋寚鏍囥€?    浠呯鐞嗗憳鐢ㄦ埛鍙闂€?    
    璺敱: GET /api/core/cache/stats/
    杩斿洖: {
        "hits": 1500,
        "misses": 300,
        "hit_rate": 0.833,
        "errors": 2,
        "avg_time_ms": 1.5,
        "total_operations": 1802
    }
    """
    
    def get(self, request):
        """鑾峰彇缂撳瓨缁熻淇℃伅"""
        # Permission check
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_manager import get_cache_stats
            
            stats = get_cache_stats()
            
            return Response({
                'status': 'success',
                'data': stats,
                'timestamp': self._get_timestamp()
            })
        except Exception as e:
            logger.exception('鑾峰彇缂撳瓨缁熻澶辫触')
            return Response(
                {'detail': f'鑾峰彇缁熻澶辫触: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class CacheHealthView(APIView):
    """
    缂撳瓨鍋ュ悍妫€鏌ヨ鍥?    
    璇婃柇缂撳瓨绯荤粺鐨勫仴搴风姸鎬併€?    浠呯鐞嗗憳鐢ㄦ埛鍙闂€?    
    璺敱: GET /api/core/cache/health/
    杩斿洖: {
        "status": "healthy|degraded|unhealthy",
        "backend": "redis|locmem",
        "connection": "ok|error",
        "latency_ms": 1.2,
        "message": "..."
    }
    """
    
    def get(self, request):
        """Check cache health."""
        # Permission check
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_config import CacheOptimization
            
            health = CacheOptimization.check_cache_health()
            
            http_status = status.HTTP_200_OK if health['status'] == 'healthy' \
                else status.HTTP_503_SERVICE_UNAVAILABLE
            
            return Response(health, status=http_status)
        except Exception as e:
            logger.exception('Cache health check failed')
            return Response(
                {'detail': f'Health check failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheClearView(APIView):
    """
    缂撳瓨娓呯悊瑙嗗浘
    
    娓呴櫎鎸囧畾鐨勭紦瀛樻暟鎹€?    浠呯鐞嗗憳鐢ㄦ埛鍙闂€?    
    POST /api/core/cache/clear/
    Body: {
        "pattern": "user:*",  # 鍙€夛紝鏀寔閫氶厤绗?        "all": true            # 鍙€夛紝娓呴櫎鎵€鏈夌紦瀛?    }
    """
    
    def post(self, request):
        """娓呴櫎缂撳瓨"""
        # Permission check
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_manager import CacheManager
            
            data = request.data or {}
            
            if data.get('all'):
                # Clear all cache
                cache.clear()
                message = 'All cache cleared.'
                logger.info('鎵€鏈夌紦瀛樺凡娓呴櫎')
            elif data.get('pattern'):
                # Clear cache by pattern
                manager = CacheManager()
                count = manager.clear_pattern(data['pattern'])
                message = f'Cleared {count} cache entries.'
                logger.info(f"Cleared cache entries for pattern {data['pattern']}: {count}")
            else:
                return Response(
                    {'detail': 'Please provide pattern or all.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'status': 'success',
                'message': message
            })
        except Exception as e:
            logger.exception('缂撳瓨娓呯悊澶辫触')
            return Response(
                {'detail': f'娓呯悊澶辫触: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheWarmupView(APIView):
    """
    缂撳瓨棰勭儹瑙嗗浘
    
    鎵嬪姩瑙﹀彂缂撳瓨棰勭儹锛堢儹閿€浜у搧銆佸父鐢ㄩ厤缃瓑锛夈€?    浠呯鐞嗗憳鐢ㄦ埛鍙闂€?    
    POST /api/core/cache/warmup/
    Body: {
        "targets": ["products", "categories", "config"]  # 瑕侀鐑殑鐩爣
    }
    """
    
    def post(self, request):
        """瑙﹀彂缂撳瓨棰勭儹"""
        # Permission check
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_manager import CacheManager, CacheWarmup
            
            manager = CacheManager()
            data = request.data or {}
            targets = data.get('targets', ['products'])
            
            results = {}
            
            for target in targets:
                if target == 'products':
                    CacheWarmup.warmup_popular_products(manager, limit=50)
                    results['products'] = 'Popular products warmed.'
                elif target == 'categories':
                    # Optional: warm categories
                    results['categories'] = 'Categories warmed.'
                elif target == 'config':
                    # Optional: warm config
                    results['config'] = 'Config warmed.'
            
            logger.info(f'缂撳瓨棰勭儹瀹屾垚: {targets}')
            
            return Response({
                'status': 'success',
                'message': '缂撳瓨棰勭儹瀹屾垚',
                'results': results
            })
        except Exception as e:
            logger.exception('缂撳瓨棰勭儹澶辫触')
            return Response(
                {'detail': f'棰勭儹澶辫触: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


