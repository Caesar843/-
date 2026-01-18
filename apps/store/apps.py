from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StoreConfig(AppConfig):
    """
    Store 应用配置
    """
    # 指定默认主键类型，推荐使用 BigAutoField 以适应未来数据增长
    default_auto_field = 'django.db.models.BigAutoField'

    # 【关键】必须包含完整路径，否则 Django 无法正确定位 App
    name = 'apps.store'

    # Admin 后台显示的中文名称
    verbose_name = _('店铺与合同管理')

    def ready(self):
        # 预留信号注册位置，暂不编写代码
        pass