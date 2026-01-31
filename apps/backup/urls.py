from django.urls import path
from apps.backup.views import (
    BackupListView,
    BackupDetailView,
    BackupCreateView,
    BackupDownloadView,
    BackupRestoreView,
    BackupDeleteView,
    BackupVerifyView,
    BackupStatsView,
    BackupDirectoryBrowseView,
)

"""
Backup App URL Configuration
-----------------------------
[架构职责]
1. 备份管理应用的路由分发
2. 映射备份相关的视图函数
3. 提供命名空间，避免URL冲突
"""

app_name = 'backup'

urlpatterns = [
    # 备份列表和统计
    path('', BackupListView.as_view(), name='backup_list'),
    path('stats/', BackupStatsView.as_view(), name='backup_stats'),
    
    # 备份创建和管理
    path('create/', BackupCreateView.as_view(), name='backup_create'),
    path('dir-picker/', BackupDirectoryBrowseView.as_view(), name='backup_dir_picker'),
    path('<int:pk>/', BackupDetailView.as_view(), name='backup_detail'),
    path('<int:pk>/download/', BackupDownloadView.as_view(), name='backup_download'),
    path('<int:pk>/restore/', BackupRestoreView.as_view(), name='backup_restore'),
    path('<int:pk>/delete/', BackupDeleteView.as_view(), name='backup_delete'),
    path('<int:pk>/verify/', BackupVerifyView.as_view(), name='backup_verify'),
]
