
"""
运营数据应用URL配置
-------------
定义运营数据应用的URL路由
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.operations import views


# 设置URL名称空间
app_name = 'operations'

# 创建REST API路由器
router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet, basename='device')
router.register(r'device-data', views.DeviceDataViewSet, basename='device-data')
router.register(r'manual-data', views.ManualOperationDataViewSet, basename='manual-data')
router.register(r'analyses', views.OperationAnalysisViewSet, basename='analysis')


urlpatterns = [
    # API路由
    path('api/', include(router.urls)),
    
    # 设备数据采集API
    path('api/device-collection/', views.DeviceDataCollectionAPI.as_view(), name='device-collection'),
    
    # 设备数据接收API（物联网设备上报）
    path('api/device_data/', views.DeviceDataReceiveAPIView.as_view(), name='device-data-receive'),
    
    # 设备状态更新API
    path('api/device/<str:device_id>/status/', views.DeviceStatusUpdateAPIView.as_view(), name='device-status-update'),
    
    # 手动数据上传
    path('manual-upload/', views.ManualDataUploadView.as_view(), name='manual-upload'),
    
    # 数据可视化
    path('dashboard/', views.OperationDashboardView.as_view(), name='dashboard'),
    
    # 数据分析
    path('analysis/', views.AnalysisView.as_view(), name='analysis'),
    
    # 设备管理
    path('devices/', views.DeviceManagementView.as_view(), name='device-management'),
    
    # 数据报表
    path('reports/', views.ReportsView.as_view(), name='reports'),
]
