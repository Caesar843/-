
"""
运营数据应用配置
-------------
配置运营数据应用的基本信息
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OperationsConfig(AppConfig):
    """
    运营数据应用配置类
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations'
    verbose_name = _('运营数据管理')
    
    def ready(self):
        """
        应用初始化时执行的方法
        """
        # 导入信号处理模块
        try:
            import apps.operations.signals
        except ImportError:
            pass
