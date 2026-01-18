from django.apps import AppConfig


class BackupConfig(AppConfig):
    """
    备份管理应用配置
    
    职责：
    1. 管理备份和恢复的应用生命周期
    2. 注册应用信号（如数据变化时的备份触发）
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.backup'
    verbose_name = '数据备份与恢复'
