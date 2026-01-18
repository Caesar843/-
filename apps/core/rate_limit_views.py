"""
限流管理 API 视图

提供：
1. 限流状态查询
2. 限流配置管理
3. 白名单/黑名单管理
4. 限流统计查看
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .rate_limiter import rate_limiter, check_rate_limit, reset_rate_limit, get_rate_limit_status
from .rate_limit_config import RateLimitConfig, CostConfig
from .rate_limit_decorators import get_client_ip

logger = logging.getLogger(__name__)


# ============================================================================
# API 视图
# ============================================================================

class RateLimitViewSet(viewsets.ViewSet):
    """
    限流管理视图集
    
    端点:
    - GET /api/core/rate-limit/status/ - 获取限流状态
    - GET /api/core/rate-limit/stats/ - 获取统计信息
    - POST /api/core/rate-limit/reset/ - 重置限流
    - GET /api/core/rate-limit/config/ - 获取配置
    - POST /api/core/rate-limit/configure/ - 更新配置
    """
    
    def get_permissions(self):
        """权限检查"""
        if self.action in ['status', 'stats']:
            return [IsAuthenticated()]
        else:
            return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        获取限流状态
        
        返回用户和 IP 的当前限流状态
        """
        user_id = request.user.id if request.user.is_authenticated else None
        client_ip = get_client_ip(request)
        
        # 获取全局状态
        global_status = rate_limiter.get_status()
        
        # 获取用户级状态
        user_status = {}
        ip_status = {}
        
        if user_id:
            _, user_status = check_rate_limit(
                user_id=str(user_id),
                client_ip=client_ip,
            )
        
        if client_ip:
            _, ip_status = check_rate_limit(
                client_ip=client_ip,
            )
        
        return Response({
            'global': global_status,
            'user': user_status.get('user', {}),
            'ip': ip_status.get('ip', {}),
            'user_id': user_id,
            'client_ip': client_ip,
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        获取限流统计信息
        
        返回总体限流统计
        """
        stats = rate_limiter.get_status()
        
        return Response({
            'total_requests': stats.get('total_requests', 0),
            'allowed': stats.get('allowed', 0),
            'denied': stats.get('denied', 0),
            'denial_rate': stats.get('denial_rate', 0.0),
        })
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """
        重置限流记录
        
        可选参数:
        - key: 重置特定键 (user:123, ip:192.168.1.1 等)
        - type: 重置类型 (global/user/ip/endpoint)
        """
        key = request.data.get('key')
        reset_type = request.data.get('type', 'global')
        
        if key:
            reset_rate_limit(key)
            return Response({
                'message': f'限流记录已重置: {key}',
            })
        else:
            reset_rate_limit()
            return Response({
                'message': '全局限流记录已重置',
            })
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """获取当前限流配置"""
        return Response({
            'limits': RateLimitConfig.DEFAULT_LIMITS,
            'endpoint_limits': RateLimitConfig.ENDPOINT_LIMITS,
            'user_tiers': RateLimitConfig.USER_TIER_MULTIPLIERS,
            'cost_budgets': CostConfig.USER_COST_BUDGET,
        })
    
    @action(detail=False, methods=['post'])
    def configure(self, request):
        """
        更新限流配置
        
        参数:
        - level: 限流层级 (global/user/ip/endpoint)
        - rate: 限流速率
        - period: 时间窗口（秒）
        - strategy: 限流策略 (可选)
        """
        level = request.data.get('level')
        rate = request.data.get('rate')
        period = request.data.get('period')
        strategy = request.data.get('strategy')
        
        if not all([level, rate, period]):
            return Response(
                {'error': 'Missing required parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            RateLimitConfig.configure_limit(level, rate, period)
            rate_limiter.configure(level, rate, period, strategy)
            
            logger.info(f'Rate limit configured: {level} = {rate} req/{period}s')
            
            return Response({
                'message': f'限流配置已更新: {level}',
                'level': level,
                'rate': rate,
                'period': period,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WhitelistViewSet(viewsets.ViewSet):
    """白名单管理视图集"""
    
    permission_classes = [IsAdminUser]
    
    def list(self, request):
        """获取白名单"""
        return Response({
            'users': RateLimitConfig.WHITELIST['users'],
            'ips': RateLimitConfig.WHITELIST['ips'],
            'endpoints': RateLimitConfig.WHITELIST['endpoints'],
        })
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """添加到白名单"""
        key_type = request.data.get('type')  # users/ips/endpoints
        value = request.data.get('value')
        
        if not key_type or not value:
            return Response(
                {'error': 'Missing type or value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        RateLimitConfig.add_whitelist(key_type, value)
        
        return Response({
            'message': f'已添加到白名单: {key_type}={value}',
        })
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """从白名单移除"""
        key_type = request.data.get('type')
        value = request.data.get('value')
        
        if not key_type or not value:
            return Response(
                {'error': 'Missing type or value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        RateLimitConfig.remove_whitelist(key_type, value)
        
        return Response({
            'message': f'已从白名单移除: {key_type}={value}',
        })


class BlacklistViewSet(viewsets.ViewSet):
    """黑名单管理视图集"""
    
    permission_classes = [IsAdminUser]
    
    def list(self, request):
        """获取黑名单"""
        return Response({
            'users': RateLimitConfig.BLACKLIST['users'],
            'ips': RateLimitConfig.BLACKLIST['ips'],
            'endpoints': RateLimitConfig.BLACKLIST['endpoints'],
        })
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """添加到黑名单"""
        key_type = request.data.get('type')
        value = request.data.get('value')
        
        if not key_type or not value:
            return Response(
                {'error': 'Missing type or value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        RateLimitConfig.add_blacklist(key_type, value)
        
        return Response({
            'message': f'已添加到黑名单: {key_type}={value}',
        })
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """从黑名单移除"""
        key_type = request.data.get('type')
        value = request.data.get('value')
        
        if not key_type or not value:
            return Response(
                {'error': 'Missing type or value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        RateLimitConfig.remove_blacklist(key_type, value)
        
        return Response({
            'message': f'已从黑名单移除: {key_type}={value}',
        })


# ============================================================================
# 快捷视图
# ============================================================================

@api_view(['GET'])
def rate_limit_status_view(request):
    """简单的限流状态视图"""
    user_id = request.user.id if request.user.is_authenticated else None
    client_ip = get_client_ip(request)
    
    allowed, info = check_rate_limit(
        user_id=str(user_id) if user_id else None,
        client_ip=client_ip,
    )
    
    return Response({
        'allowed': allowed,
        'user_id': user_id,
        'client_ip': client_ip,
        'limits': info,
    })


@api_view(['GET'])
def rate_limit_stats_view(request):
    """简单的限流统计视图"""
    stats = rate_limiter.get_status()
    
    return Response(stats)
