"""
限流 API 路由配置

包括:
1. 限流状态、统计、配置端点
2. 白名单/黑名单管理端点
3. 简单视图端点
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .rate_limit_views import (
    RateLimitViewSet,
    WhitelistViewSet,
    BlacklistViewSet,
    rate_limit_status_view,
    rate_limit_stats_view,
)

# 创建路由器
router = DefaultRouter()
router.register(r'rate-limit', RateLimitViewSet, basename='rate-limit')
router.register(r'whitelist', WhitelistViewSet, basename='whitelist')
router.register(r'blacklist', BlacklistViewSet, basename='blacklist')

app_name = 'rate_limit'

urlpatterns = [
    # ViewSet 路由
    path('', include(router.urls)),
    
    # 简单视图
    path('status/', rate_limit_status_view, name='status'),
    path('stats/', rate_limit_stats_view, name='stats'),
]
