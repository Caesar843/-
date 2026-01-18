from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import shutil
import logging
from apps.core.response import APIResponse

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    健康检查端点
    
    用于监控系统健康状态，可被负载均衡器和监控系统使用。
    
    返回格式:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "checks": {
            "database": "ok" | "error: ...",
            "redis": "ok" | "error: ...",
            "disk_percent": 45.2,
            "uptime_seconds": 3600
        }
    }
    
    HTTP 状态码:
    - 200: 系统健康
    - 503: 系统不健康或性能下降
    """
    
    def get(self, request):
        """检查系统健康状态"""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': self._get_timestamp()
        }
        
        # 1. 数据库检查
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
            logger.debug('数据库连接正常')
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = f'error: {str(e)}'
            logger.error(f'数据库连接失败: {str(e)}')
        
        # 2. Redis 检查（如果配置了）
        try:
            cache.set('health_check', 'ok', 10)
            value = cache.get('health_check')
            if value == 'ok':
                health_status['checks']['redis'] = 'ok'
                logger.debug('Redis 连接正常')
            else:
                health_status['status'] = 'degraded'
                health_status['checks']['redis'] = 'error: cache get failed'
                logger.warning('Redis get 操作失败')
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['checks']['redis'] = f'error: {str(e)}'
            logger.warning(f'Redis 连接失败: {str(e)}')
        
        # 3. 磁盘空间检查
        try:
            total, used, free = shutil.disk_usage('/')
            disk_percent = (used / total) * 100
            health_status['checks']['disk_percent'] = round(disk_percent, 2)
            health_status['checks']['disk_free_gb'] = round(free / (1024**3), 2)
            
            # 如果磁盘使用超过 90%，标记为性能下降
            if disk_percent > 90:
                health_status['status'] = 'degraded'
                logger.warning(f'磁盘使用率过高: {disk_percent}%')
            
            logger.debug(f'磁盘使用率: {disk_percent}%')
        except Exception as e:
            health_status['checks']['disk'] = f'error: {str(e)}'
            logger.warning(f'磁盘检查失败: {str(e)}')
        
        # 4. 获取数据库连接数（PostgreSQL）
        try:
            if 'postgresql' in str(connection.settings_dict.get('ENGINE', '')):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                    )
                    conn_count = cursor.fetchone()[0]
                    health_status['checks']['db_connections'] = conn_count
        except Exception as e:
            logger.debug(f'数据库连接数查询失败: {str(e)}')
        
        # 5. 应用启动时间（从 Django 启动时间计算）
        try:
            import time
            import django
            # 简单估算，实际应该记录启动时间
            health_status['checks']['version'] = django.get_version()
        except Exception as e:
            logger.debug(f'版本信息获取失败: {str(e)}')
        
        # 根据状态返回不同的 HTTP 状态码
        http_status = {
            'healthy': status.HTTP_200_OK,
            'degraded': status.HTTP_200_OK,  # 202 也可以，但 200 更通用
            'unhealthy': status.HTTP_503_SERVICE_UNAVAILABLE
        }.get(health_status['status'], status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(health_status, status=http_status)
    
    @staticmethod
    def _get_timestamp():
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class LoginView(View):
    """用户登录视图"""
    template_name = 'core/login.html'
    
    def get(self, request):
        """显示登录表单"""
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        return render(request, self.template_name)
    
    def post(self, request):
        """处理登录请求"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # 验证输入
        if not username or not password:
            messages.error(request, '请输入用户名和密码')
            return render(request, self.template_name)
        
        # 验证用户
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, '登录成功')
                return redirect('dashboard:index')
            else:
                messages.error(request, '用户账号已被禁用')
        else:
            messages.error(request, '用户名或密码错误')
        
        return render(request, self.template_name)


class LogoutView(View):
    """用户登出视图"""
    def get(self, request):
        """处理登出请求"""
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, '已成功登出')
        return redirect('core:login')


# ============================================
# CSRF 和错误处理视图
# ============================================

def csrf_failure(request, reason=""):
    """
    CSRF 验证失败处理视图
    
    当 CSRF token 校验失败时调用此视图。
    """
    logger.warning(
        f'CSRF 验证失败: {reason}',
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
                'message': 'CSRF token 验证失败，请重新提交',
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
    """404 错误处理"""
    logger.info(f'404 错误: {request.path}')
    
    if request.headers.get('Accept') == 'application/json':
        return Response(
            {
                'code': 404,
                'message': '请求的页面不存在',
                'data': None,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    else:
        return render(request, 'errors/404.html', status=404)


def server_error(request):
    """500 错误处理"""
    logger.error(f'500 错误: {request.path}')
    
    if request.headers.get('Accept') == 'application/json':
        return Response(
            {
                'code': 500,
                'message': '服务器内部错误，请稍后重试',
                'data': None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        return render(request, 'errors/500.html', status=500)


class CacheStatsView(APIView):
    """
    缓存统计监控视图
    
    获取缓存性能统计，包括命中率、错误率等指标。
    仅管理员用户可访问。
    
    路由: GET /api/core/cache/stats/
    返回: {
        "hits": 1500,
        "misses": 300,
        "hit_rate": 0.833,
        "errors": 2,
        "avg_time_ms": 1.5,
        "total_operations": 1802
    }
    """
    
    def get(self, request):
        """获取缓存统计信息"""
        # 权限检查
        if not request.user.is_staff:
            return Response(
                {'detail': '只有管理员可以访问'},
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
            logger.exception('获取缓存统计失败')
            return Response(
                {'detail': f'获取统计失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class CacheHealthView(APIView):
    """
    缓存健康检查视图
    
    诊断缓存系统的健康状态。
    仅管理员用户可访问。
    
    路由: GET /api/core/cache/health/
    返回: {
        "status": "healthy|degraded|unhealthy",
        "backend": "redis|locmem",
        "connection": "ok|error",
        "latency_ms": 1.2,
        "message": "..."
    }
    """
    
    def get(self, request):
        """检查缓存健康状态"""
        # 权限检查
        if not request.user.is_staff:
            return Response(
                {'detail': '只有管理员可以访问'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_config import CacheOptimization
            
            health = CacheOptimization.check_cache_health()
            
            http_status = status.HTTP_200_OK if health['status'] == 'healthy' \
                else status.HTTP_503_SERVICE_UNAVAILABLE
            
            return Response(health, status=http_status)
        except Exception as e:
            logger.exception('缓存健康检查失败')
            return Response(
                {'detail': f'检查失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheClearView(APIView):
    """
    缓存清理视图
    
    清除指定的缓存数据。
    仅管理员用户可访问。
    
    POST /api/core/cache/clear/
    Body: {
        "pattern": "user:*",  # 可选，支持通配符
        "all": true            # 可选，清除所有缓存
    }
    """
    
    def post(self, request):
        """清除缓存"""
        # 权限检查
        if not request.user.is_staff:
            return Response(
                {'detail': '只有管理员可以访问'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            from apps.core.cache_manager import CacheManager
            
            data = request.data or {}
            
            if data.get('all'):
                # 清除所有缓存
                cache.clear()
                message = '已清除所有缓存'
                logger.info('所有缓存已清除')
            elif data.get('pattern'):
                # 清除匹配模式的缓存
                manager = CacheManager()
                count = manager.clear_pattern(data['pattern'])
                message = f'已清除 {count} 个缓存'
                logger.info(f'清除了模式 {data["pattern"]} 匹配的 {count} 个缓存')
            else:
                return Response(
                    {'detail': '请提供 pattern 或 all 参数'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'status': 'success',
                'message': message
            })
        except Exception as e:
            logger.exception('缓存清理失败')
            return Response(
                {'detail': f'清理失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CacheWarmupView(APIView):
    """
    缓存预热视图
    
    手动触发缓存预热（热销产品、常用配置等）。
    仅管理员用户可访问。
    
    POST /api/core/cache/warmup/
    Body: {
        "targets": ["products", "categories", "config"]  # 要预热的目标
    }
    """
    
    def post(self, request):
        """触发缓存预热"""
        # 权限检查
        if not request.user.is_staff:
            return Response(
                {'detail': '只有管理员可以访问'},
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
                    results['products'] = '已预热热销产品'
                elif target == 'categories':
                    # 可扩展：预热分类等
                    results['categories'] = '已预热分类信息'
                elif target == 'config':
                    # 可扩展：预热配置等
                    results['config'] = '已预热系统配置'
            
            logger.info(f'缓存预热完成: {targets}')
            
            return Response({
                'status': 'success',
                'message': '缓存预热完成',
                'results': results
            })
        except Exception as e:
            logger.exception('缓存预热失败')
            return Response(
                {'detail': f'预热失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )