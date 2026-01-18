from django.urls import path
from apps.dashboard.views import DashboardView

"""
Dashboard App URL Configuration
-------------------------------
[架构职责]
1. 数据总览应用的路由分发。
2. 映射视图函数与 URL 路径。
3. 提供命名空间，避免 URL 冲突。
"""

app_name = 'dashboard'

urlpatterns = [
    # 数据总览首页
    path('', DashboardView.as_view(), name='index'),
]
