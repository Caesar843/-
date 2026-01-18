"""
国际化 URL 配置
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from .i18n_views import I18nViewSet, translate_view, convert_currency_view, format_date_view

# 创建路由器
router = DefaultRouter()
# 不需要前缀，因为这已经被 /api/i18n/ 包含了
router.register(r'', I18nViewSet, basename='i18n')

# URL 模式
urlpatterns = router.urls

# 添加简单视图
simple_patterns = [
    path('translate/', translate_view, name='translate'),
    path('convert-currency/', convert_currency_view, name='convert_currency'),
    path('format-date/', format_date_view, name='format_date'),
]

urlpatterns.extend(simple_patterns)

app_name = 'i18n'
