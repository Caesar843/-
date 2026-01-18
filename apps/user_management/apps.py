from django.apps import AppConfig


class UserManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user_management'
    verbose_name = '用户管理'
    
    def ready(self):
        # 导入信号处理器，确保信号被注册
        import apps.user_management.signals
