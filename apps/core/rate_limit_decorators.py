"""
API 限流装饰器和中间件

提供方便的装饰器和中间件实现，用于保护 API 端点
"""

import functools
import logging
from typing import Callable, Optional, Any, Dict
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.decorators import decorator_from_middleware_with_args
from rest_framework import status
from rest_framework.decorators import api_view
from .rate_limiter import check_rate_limit, rate_limiter
from .rate_limit_config import RateLimitConfig, CostConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 装饰器
# ============================================================================

def rate_limit(
    requests: int = 100,
    period: int = 60,
    key_func: Optional[Callable] = None
):
    """
    限流装饰器 - 限制单个端点的请求速率
    
    Args:
        requests: 允许的最大请求数
        period: 时间窗口（秒）
        key_func: 自定义限流键生成函数
    
    示例:
        @rate_limit(requests=10, period=60)
        def my_view(request):
            return Response({'status': 'ok'})
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 获取限流键
            if key_func:
                limit_key = key_func(request)
            else:
                # 默认使用用户ID或IP
                user_id = getattr(request.user, 'id', None)
                client_ip = get_client_ip(request)
                limit_key = f'user:{user_id}' if user_id else f'ip:{client_ip}'
            
            # 检查限流
            allowed, info = check_rate_limit(
                user_id=user_id if not key_func else None,
                client_ip=get_client_ip(request),
                endpoint=request.path,
            )
            
            if not allowed:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'message': f'限制: {requests} 请求/{period} 秒',
                        'retry_after': info['endpoint']['reset_after'],
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def throttle(
    strategy: str = 'token_bucket',
    rate: int = 100,
    period: int = 60
):
    """
    节流装饰器 - 使用特定策略限制请求
    
    Args:
        strategy: 限流策略 (token_bucket/leaky_bucket/sliding_window/fixed_window)
        rate: 限流速率
        period: 时间窗口（秒）
    
    示例:
        @throttle(strategy='token_bucket', rate=100, period=60)
        def my_view(request):
            return Response({'status': 'ok'})
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_id = getattr(request.user, 'id', None)
            
            allowed, info = check_rate_limit(
                user_id=f'user:{user_id}' if user_id else None,
                client_ip=f'ip:{get_client_ip(request)}',
            )
            
            if not allowed:
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'retry_after': info['user']['reset_after'] if user_id else info['ip']['reset_after'],
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def cost_limit(
    max_cost: int = 1000,
    operation: Optional[str] = None
):
    """
    基于成本的限流装饰器
    
    Args:
        max_cost: 最大成本（通常是每小时预算）
        operation: 操作类型（用于查询成本）
    
    示例:
        @cost_limit(max_cost=1000, operation='export')
        def export_data(request):
            return Response({...})
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 获取操作成本
            cost = CostConfig.get_operation_cost(operation or 'default')
            
            # 检查用户成本预算
            user_id = getattr(request.user, 'id', None)
            if user_id:
                cache_key = f'cost_budget:{user_id}'
                from django.core.cache import cache
                used_cost = cache.get(cache_key, 0)
                
                if used_cost + cost > max_cost:
                    return JsonResponse(
                        {
                            'error': 'Cost limit exceeded',
                            'message': f'成本预算已用尽 (已使用: {used_cost}/{max_cost})',
                            'used_cost': used_cost,
                            'max_cost': max_cost,
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                
                # 更新使用成本
                cache.set(cache_key, used_cost + cost, 3600)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# 2. 中间件
# ============================================================================

class RateLimitMiddleware:
    """
    限流中间件 - 在视图处理之前检查限流
    
    在 settings.py 中注册:
        MIDDLEWARE = [
            ...
            'apps.core.rate_limit_decorators.RateLimitMiddleware',
            ...
        ]
    """
    
    # 不需要限流的路径
    EXEMPT_PATHS = [
        '/health/',
        '/admin/',
        '/api/docs/',
        '/api/redoc/',
        '/api/schema/',
        '/static/',
        '/media/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 检查是否在豁免路径中
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return self.get_response(request)
        
        # 检查是否在白名单中
        client_ip = get_client_ip(request)
        user_id = getattr(request.user, 'id', None) if request.user.is_authenticated else None
        
        if RateLimitConfig.is_whitelisted('ips', client_ip):
            return self.get_response(request)
        
        if user_id and RateLimitConfig.is_whitelisted('users', str(user_id)):
            return self.get_response(request)
        
        # 检查是否在黑名单中
        if RateLimitConfig.is_blacklisted('ips', client_ip):
            logger.warning(f'Blacklisted IP attempted access: {client_ip}')
            return JsonResponse(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_id and RateLimitConfig.is_blacklisted('users', str(user_id)):
            logger.warning(f'Blacklisted user attempted access: {user_id}')
            return JsonResponse(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 检查限流
        allowed, info = check_rate_limit(
            user_id=str(user_id) if user_id else None,
            client_ip=client_ip,
            endpoint=request.path,
        )
        
        if not allowed:
            logger.warning(
                f'Rate limit exceeded',
                extra={
                    'user_id': user_id,
                    'client_ip': client_ip,
                    'path': request.path,
                }
            )
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'retry_after': max(
                        info['user'].get('reset_after', 60),
                        info['ip'].get('reset_after', 60),
                        info['endpoint'].get('reset_after', 60),
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        response = self.get_response(request)
        
        # 添加限流信息到响应头
        response['X-RateLimit-Limit'] = str(RateLimitConfig.DEFAULT_LIMITS['user']['rate'])
        response['X-RateLimit-Remaining'] = str(info['user'].get('remaining', 0))
        response['X-RateLimit-Reset'] = str(info['user'].get('reset_after', 60))
        
        return response


# ============================================================================
# 3. 辅助函数
# ============================================================================

def get_client_ip(request: HttpRequest) -> str:
    """
    获取客户端 IP 地址
    
    处理代理情况下的真实 IP
    """
    # 检查是否通过代理
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip or '0.0.0.0'


def get_rate_limit_info(request: HttpRequest) -> Dict[str, Any]:
    """获取请求的限流信息"""
    user_id = getattr(request.user, 'id', None) if request.user.is_authenticated else None
    client_ip = get_client_ip(request)
    
    _, info = check_rate_limit(
        user_id=str(user_id) if user_id else None,
        client_ip=client_ip,
        endpoint=request.path,
    )
    
    return {
        'user_id': user_id,
        'client_ip': client_ip,
        'endpoint': request.path,
        'info': info,
    }


# ============================================================================
# 4. DRF 限流器
# ============================================================================

from rest_framework.throttling import BaseThrottle

class CustomUserThrottle(BaseThrottle):
    """
    Django REST Framework 用户限流器
    
    在 settings.py 中配置:
        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_CLASSES': [
                'apps.core.rate_limit_decorators.CustomUserThrottle',
            ],
            'DEFAULT_THROTTLE_RATES': {
                'user': '100/hour',
            }
        }
    """
    
    def allow_request(self, request, view):
        user_id = request.user.id if request.user and request.user.is_authenticated else None
        client_ip = get_client_ip(request)
        
        allowed, info = check_rate_limit(
            user_id=str(user_id) if user_id else None,
            client_ip=client_ip,
            endpoint=request.path,
        )
        
        return allowed
    
    def throttle_success(self):
        return True
    
    def throttle_failure(self):
        return False


class CustomIPThrottle(BaseThrottle):
    """
    Django REST Framework IP 限流器
    """
    
    def allow_request(self, request, view):
        client_ip = get_client_ip(request)
        
        allowed, info = check_rate_limit(
            client_ip=client_ip,
            endpoint=request.path,
        )
        
        return allowed
    
    def throttle_success(self):
        return True
    
    def throttle_failure(self):
        return False
