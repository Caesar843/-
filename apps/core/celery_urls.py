"""
Celery 任务管理 API 路由配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.celery_views import (
    TaskViewSet,
    WorkerViewSet,
    task_status_view,
    send_task_view,
    celery_stats_view,
)

# 创建路由器
router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='celery-task')
router.register(r'workers', WorkerViewSet, basename='celery-worker')

app_name = 'celery'

urlpatterns = [
    # ViewSet 路由
    path('', include(router.urls)),
    
    # 简单视图
    path('task/<str:task_id>/', task_status_view, name='task-status'),
    path('task/send/', send_task_view, name='task-send'),
    path('stats/', celery_stats_view, name='celery-stats'),
]
