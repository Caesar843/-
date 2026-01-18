"""
全文搜索 API 路由配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.search_views import (
    SearchViewSet,
    SearchIndexViewSet,
    search_view,
    autocomplete_view,
    metrics_view,
)

# 创建路由器
router = DefaultRouter()
router.register(r'search', SearchViewSet, basename='search')
router.register(r'search-index', SearchIndexViewSet, basename='search-index')

app_name = 'search'

urlpatterns = [
    # ViewSet 路由
    path('', include(router.urls)),
    
    # 简单视图
    path('quick-search/', search_view, name='quick-search'),
    path('autocomplete/', autocomplete_view, name='autocomplete'),
    path('metrics/', metrics_view, name='metrics'),
]
