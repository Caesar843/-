from django.apps import AppConfig


class QueryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.query'
    verbose_name = '多维度查询系统'