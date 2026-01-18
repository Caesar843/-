from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('health/', views.HealthCheckView.as_view(), name='health'),
    
    # 缓存监控 API 路由
    path('cache/stats/', views.CacheStatsView.as_view(), name='cache_stats'),
    path('cache/health/', views.CacheHealthView.as_view(), name='cache_health'),
    path('cache/clear/', views.CacheClearView.as_view(), name='cache_clear'),
    path('cache/warmup/', views.CacheWarmupView.as_view(), name='cache_warmup'),
    
    # 错误处理路由（用于测试）
    path('error/403/', views.csrf_failure, name='csrf_error'),
    path('error/404/', views.page_not_found, name='page_not_found'),
    path('error/500/', views.server_error, name='server_error'),
]