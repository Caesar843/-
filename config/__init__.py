"""


Celery 应用初始化
在Django启动时自动导入Celery配置
"""
import logging

logger = logging.getLogger(__name__)

try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError as exc:
    # Celery 未安装时，使用虚拟 app 以避免启动错误
    logger.warning("Celery import failed; using dummy app. error=%s", exc)
    class DummyCeleryApp:
        def autodiscover_tasks(self, *args, **kwargs):
            return None
        
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    
    celery_app = DummyCeleryApp()
    __all__ = ('celery_app',)