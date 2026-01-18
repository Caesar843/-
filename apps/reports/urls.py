from django.urls import path
from apps.reports.views import ReportView

"""
报表应用URL配置
----------------
定义报表应用的路由分发
"""

app_name = 'reports'

urlpatterns = [
    path('', ReportView.as_view(), name='report_list'),
    path('generate/', ReportView.as_view(), name='generate_report'),
    path('export/', ReportView.as_view(), name='export_report'),
]
