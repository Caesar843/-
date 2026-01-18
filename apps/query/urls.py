"""
Query App URLs
----------------
"""

from django.urls import path
from apps.query import views

app_name = 'query'

urlpatterns = [
    # 仪表盘
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # 店铺端查询
    path('shop/', views.ShopQueryView.as_view(), name='shop_query'),
    
    # 运营专员端查询
    path('operation/', views.OperationQueryView.as_view(), name='operation_query'),
    
    # 财务管理员端查询
    path('finance/', views.FinanceQueryView.as_view(), name='finance_query'),
    
    # 管理层端查询
    path('admin/', views.AdminQueryView.as_view(), name='admin_query'),
]