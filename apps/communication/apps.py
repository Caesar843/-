from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommunicationConfig(AppConfig):
    """
    通信模块应用配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.communication'
    verbose_name = _('通信管理')