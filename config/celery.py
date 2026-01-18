"""
Celery 配置文件（支持 Celery 可选依赖）

使用方式：
1. 启动 Celery Worker: celery -A config worker -l info
2. 启动 Celery Beat: celery -A config beat -l info

注：使用 Celery 需要先安装: pip install celery redis
"""
import os

CELERY_AVAILABLE = False

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    # Celery 未安装，定义虚拟类以避免错误
    class crontab:
        def __init__(self, *args, **kwargs):
            pass
    
    print("Warning: Celery is not installed. Run 'pip install celery redis' to enable async tasks.")


if CELERY_AVAILABLE:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    app = Celery('store_management')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    app.conf.update(
        timezone='Asia/Shanghai',
        enable_utc=True,
        CELERY_ENABLE_UTC=True,
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],
        CELERY_RESULT_SERIALIZER='json',
        CELERY_DEFAULT_QUEUE='default',
        CELERY_DEFAULT_EXCHANGE='tasks',
        CELERY_DEFAULT_ROUTING_KEY='task.default',
        CELERY_TASK_TIME_LIMIT=30 * 60,
        CELERY_TASK_SOFT_TIME_LIMIT=25 * 60,
    )

    app.conf.beat_schedule = {
        'generate-monthly-accounts': {
            'task': 'apps.finance.tasks.generate_monthly_accounts_task',
            'schedule': crontab(hour=8, minute=0),
            'kwargs': {'description': '生成当月所有活跃合同的账单'}
        },
        'send-payment-reminders': {
            'task': 'apps.finance.tasks.send_payment_reminder_task',
            'schedule': crontab(hour=10, minute=0, day_of_week='1-5'),
            'kwargs': {'days_ahead': 3, 'description': '发送3天内到期的账单支付提醒'}
        },
        'send-overdue-alerts': {
            'task': 'apps.finance.tasks.send_overdue_payment_alert_task',
            'schedule': crontab(hour=14, minute=0, day_of_week='1-5'),
            'kwargs': {'days_overdue': 0, 'description': '检查并告警所有逾期账单'}
        },
        'send-renewal-reminders': {
            'task': 'apps.store.tasks.send_renewal_reminder_task',
            'schedule': crontab(hour=9, minute=0, day_of_month=1),
            'kwargs': {'days_until_expiry': 30, 'description': '发送合同续签提醒'}
        },
        'backup-database': {
            'task': 'apps.backup.tasks.backup_database_task',
            'schedule': crontab(hour=20, minute=0, day_of_week='4'),
            'kwargs': {'backup_type': 'FULL', 'description': '执行完整数据库备份'}
        },
        'cleanup-old-data': {
            'task': 'apps.core.tasks.cleanup_old_data_task',
            'schedule': crontab(hour=3, minute=0),
            'kwargs': {'days_retention': 30, 'description': '清理旧的日志和临时数据'}
        },
        'generate-daily-reports': {
            'task': 'apps.reports.tasks.generate_daily_report_task',
            'schedule': crontab(hour=7, minute=0, day_of_week='1-5'),
            'kwargs': {'description': '生成日流量报表和财务统计'}
        },
        'aggregate-hourly-data': {
            'task': 'apps.operations.tasks.aggregate_hourly_device_data_task',
            'schedule': crontab(minute=1),
            'kwargs': {'description': '按小时聚合所有店铺的设备数据'}
        },
        'aggregate-daily-data': {
            'task': 'apps.operations.tasks.aggregate_daily_device_data_task',
            'schedule': crontab(hour=1, minute=0),
            'kwargs': {'description': '按日聚合所有店铺的设备数据'}
        },
        'aggregate-monthly-data': {
            'task': 'apps.operations.tasks.aggregate_monthly_device_data_task',
            'schedule': crontab(hour=2, minute=0, day_of_month=1),
            'kwargs': {'description': '按月聚合所有店铺的设备数据'}
        },
        'clean-device-data': {
            'task': 'apps.operations.tasks.clean_device_data_task',
            'schedule': crontab(hour=4, minute=0, day_of_week='6'),
            'kwargs': {'description': '清洗和整理设备数据'}
        },
        'check-device-status': {
            'task': 'apps.operations.tasks.check_device_online_status_task',
            'schedule': crontab(minute='*/5'),
            'kwargs': {'description': '检查设备在线状态并标记离线设备'}
        },
    }

    @app.task(bind=True)
    def debug_task(self):
        """调试任务 - 用于测试Celery配置是否正常"""
        print(f'Request: {self.request!r}')
        return 'Celery is working!'

else:
    # Celery 未安装时，创建虚拟 app 对象
    class DummyCeleryApp:
        def autodiscover_tasks(self, *args, **kwargs):
            pass
        
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        
        class Conf:
            beat_schedule = {}
            def update(self, *args, **kwargs):
                pass
            def config_from_object(self, *args, **kwargs):
                pass
        
        conf = Conf()
    
    app = DummyCeleryApp()
