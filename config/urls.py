from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.core.views import HealthCheckView

"""
Project Root URL Configuration
------------------------------
[架构职责]
1. 系统流量入口与分发网关。
2. 聚合各业务子应用 (Apps) 的路由配置。
3. 挂载基础设施路由 (Admin, API, Auth)。

[设计假设]
- 业务路由前缀遵循 /app_name/ 模式，避免根路径冲突。
- API 路由（未来）将挂载于 /api/v1/ 下，实现前后端分离架构准备。
"""

urlpatterns = [
    # -------------------------------------------------------------------------
    # Health Check (Root Level)
    # -------------------------------------------------------------------------
    path('health/', HealthCheckView.as_view(), name='health-root'),
    
    # -------------------------------------------------------------------------
    # Infrastructure & Administration
    # -------------------------------------------------------------------------
    path('admin/', admin.site.urls),
    
    # Core app for authentication
    path('core/', include('apps.core.urls')),
    
    # -------------------------------------------------------------------------
    # API Documentation (Swagger & ReDoc)
    # -------------------------------------------------------------------------
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # -------------------------------------------------------------------------
    # API Endpoints
    # -------------------------------------------------------------------------
    
    # Rate Limiting Management API
    path('api/core/', include('apps.core.rate_limit_urls')),

    # Task Management API (Level 4 Task 2)
    path('api/core/', include('apps.core.celery_urls')),
    
    # Search API (Level 4 Task 3)
    path('api/search/', include('apps.core.search_urls')),
    
    # i18n API (Level 4 Task 4)
    path('api/i18n/', include('apps.core.i18n_urls')),

    # -------------------------------------------------------------------------
    # Business Applications (Modular Monolith)
    # -------------------------------------------------------------------------

    # [Store App] 店铺与合同管理核心业务
    # Namespace: 'store' (由 apps.store.urls.app_name 自动提供)
    path('store/', include('apps.store.urls')),

    # [Finance App] 财务核算与账单管理
    path('finance/', include('apps.finance.urls')),

    # [Dashboard App] 数据总览与系统展示
    path('dashboard/', include('apps.dashboard.urls')),
    
    # [Operations App] 运营数据采集与分析
    path('operations/', include('apps.operations.urls')),
    
    # [Communication App] 协同沟通与事务处理
    path('communication/', include('apps.communication.urls')),
    
    # [Query App] 多维度查询系统
    path('query/', include('apps.query.urls')),
    
    # [Reports App] 报表生成与导出
    path('reports/', include('apps.reports.urls')),
    
    # [Backup App] 数据备份与恢复
    path('backup/', include('apps.backup.urls')),
    
    # 系统首页重定向到 Dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

    # -------------------------------------------------------------------------
    # Workflow App (Future Extension)
    # -------------------------------------------------------------------------
    # [TODO] Workflow App: 工单与审批流
    # path('workflow/', include('apps.workflow.urls')),
    # path('api/v1/', include('config.api_urls')),
]

# ============================================
# Django 错误处理程序（自定义错误页面）
# ============================================
# 注：错误处理通过 middleware 处理，不在这里配置处理程序
# from apps.core import views as core_views
# handler400 = core_views.csrf_failure  # Bad Request
# handler403 = core_views.csrf_failure  # Forbidden / CSRF
# handler404 = core_views.page_not_found  # Not Found
# handler500 = core_views.server_error  # Internal Server Error
