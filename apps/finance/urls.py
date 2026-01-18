from django.urls import path
from apps.finance.views import (
    FinanceListView, 
    FinancePayView,
    FinanceCreateView,
    FinanceDetailView,
    FinanceStatementView,
    FinanceReminderView,
    FinanceHistoryView
)

"""
Finance App URL Configuration
-----------------------------
[架构职责]
1. 财务应用的路由分发。
2. 映射视图函数与 URL 路径。
3. 提供命名空间，避免 URL 冲突。
"""

app_name = 'finance'

urlpatterns = [
    # 财务记录列表
    path('records/', FinanceListView.as_view(), name='finance_list'),
    
    # 财务记录创建
    path('records/create/', FinanceCreateView.as_view(), name='finance_create'),
    
    # 财务记录支付
    path('records/<int:pk>/pay/', FinancePayView.as_view(), name='finance_pay'),
    
    # 财务记录详情
    path('records/<int:pk>/detail/', FinanceDetailView.as_view(), name='finance_detail'),
    
    # 费用明细单
    path('statement/<int:contract_id>/', FinanceStatementView.as_view(), name='finance_statement'),
    
    # 缴费提醒
    path('reminders/', FinanceReminderView.as_view(), name='finance_reminders'),
    
    # 缴费历史
    path('history/', FinanceHistoryView.as_view(), name='finance_history'),
]