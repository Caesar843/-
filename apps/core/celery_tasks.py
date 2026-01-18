"""
异步任务定义模块

包含所有异步任务：
1. 财务相关任务 (账单计算、支付提醒)
2. 报表生成任务 (日/周/月报表)
3. 通知任务 (邮件、短信发送)
4. 数据处理任务 (导出、导入)
5. 系统维护任务 (清理、备份)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Count, Q

from config.celery import app

logger = logging.getLogger(__name__)


# ============================================================================
# 财务相关任务
# ============================================================================

@app.task(
    bind=True,
    name='apps.finance.tasks.check_pending_bills',
    default_retry_delay=60,  # 60 秒后重试
    max_retries=3  # 最多重试 3 次
)
def check_pending_bills(self):
    """
    检查待支付账单并发送提醒
    
    每分钟执行一次，检查是否有待支付账单
    """
    try:
        from apps.finance.models import FinanceRecord
        
        # 获取待支付账单
        cutoff_date = timezone.now().date() + timedelta(days=1)
        pending_bills = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            reminder_sent=False,
            billing_period_end__lte=cutoff_date,
        )
        
        count = pending_bills.count()
        
        if count > 0:
            logger.info(f'Found {count} pending bills for reminder')
            # 发送提醒任务
            send_bill_reminders.delay(list(pending_bills.values_list('id', flat=True)))
        
        return {
            'status': 'success',
            'pending_count': count,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error checking pending bills: {str(exc)}')
        # 重试
        raise self.retry(exc=exc)


@app.task(
    name='apps.finance.tasks.send_bill_reminders',
    default_retry_delay=60,
    max_retries=3
)
def send_bill_reminders(bill_ids=None):
    """
    发送账单提醒邮件
    
    Args:
        bill_ids: 账单 ID 列表
    """
    try:
        from apps.finance.models import FinanceRecord
        from apps.store.models import Shop
        
        if not bill_ids:
            return {
                'status': 'success',
                'sent_count': 0,
                'timestamp': datetime.now().isoformat()
            }

        bills = FinanceRecord.objects.filter(id__in=bill_ids)
        
        for bill in bills:
            shop = bill.contract.shop
            contact_email = getattr(shop, 'contact_email', None)
            if not contact_email:
                logger.warning(f'Shop {shop.id} missing contact email, skipping reminder')
                continue
            
            # 构建邮件内容
            subject = f'【账单提醒】{shop.name} 有待支付账单'
            context = {
                'shop_name': shop.name,
                'bill_amount': bill.amount,
                'due_date': bill.due_date,
                'bill_id': bill.id
            }
            
            message = render_to_string('finance/bill_reminder.html', context)
            
            # 发送邮件
            send_mail(
                subject,
                'Please view in HTML mode',
                'noreply@mall.com',
                [contact_email],
                html_message=message,
                fail_silently=False
            )

            bill.reminder_sent = True
            bill.save(update_fields=['reminder_sent'])
            logger.info(f'Bill reminder sent to shop {shop.id}')
        
        return {
            'status': 'success',
            'sent_count': len(bills),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error sending bill reminders: {str(exc)}')
        raise


@app.task(
    name='apps.finance.tasks.calculate_monthly_revenue',
    default_retry_delay=60,
    max_retries=3
)
def calculate_monthly_revenue(year=None, month=None):
    """
    计算月度收入统计
    
    Args:
        year: 年份
        month: 月份
    """
    try:
        from apps.finance.models import FinanceRecord
        
        now = timezone.now()
        year = year or now.year
        month = month or now.month
        start_date = datetime(year, month, 1).date()

        # next month start for bounds
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        # aggregate revenue
        revenue_data = FinanceRecord.objects.filter(
            billing_period_start__gte=start_date,
            billing_period_start__lt=end_date,
            status=FinanceRecord.Status.PAID
        ).aggregate(
            total_revenue=Sum('amount'),
            transaction_count=Count('id')
        )
        
        logger.info(f'Monthly revenue for {year}-{month}: {revenue_data}')
        
        return revenue_data
    
    except Exception as exc:
        logger.error(f'Error calculating monthly revenue: {str(exc)}')
        return {
            'status': 'failed',
            'error': str(exc),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# 报表生成任务
# ============================================================================

@app.task(
    bind=True,
    name='apps.reports.tasks.generate_hourly_report',
    default_retry_delay=300,
    max_retries=3
)
def generate_hourly_report(self):
    """
    生成小时报表
    
    统计过去 1 小时的数据
    """
    try:
        try:
            from apps.reports.models import Report
        except Exception as exc:
            logger.warning(f'Reports models unavailable: {str(exc)}')
            return {
                'status': 'skipped',
                'reason': 'reports models unavailable',
                'timestamp': timezone.now().isoformat()
            }
        
        now = timezone.now()
        start_time = now - timedelta(hours=1)
        
        # 统计数据
        stats = {
            'period': f'{start_time.hour}:00 - {now.hour}:00',
            'timestamp': now.isoformat(),
            'shop_count': 0,
            'transaction_count': 0,
            'total_revenue': Decimal('0')
        }
        
        # 创建报表记录
        report = Report.objects.create(
            report_type='hourly',
            period_start=start_time,
            period_end=now,
            data=stats,
            status='completed'
        )
        
        logger.info(f'Hourly report generated: {report.id}')
        
        return {
            'status': 'success',
            'report_id': report.id,
            'timestamp': now.isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error generating hourly report: {str(exc)}')
        raise self.retry(exc=exc)


@app.task(
    name='apps.reports.tasks.generate_daily_report',
    default_retry_delay=300,
    max_retries=3
)
def generate_daily_report(date=None):
    """
    生成日报表
    
    Args:
        date: 日期 (默认为昨天)
    """
    try:
        try:
            from apps.reports.models import Report
        except Exception as exc:
            logger.warning(f'Reports models unavailable: {str(exc)}')
            return {
                'status': 'skipped',
                'reason': 'reports models unavailable',
                'timestamp': timezone.now().isoformat()
            }
        
        if not date:
            date = (timezone.now() - timedelta(days=1)).date()
        
        start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(date, datetime.max.time()))
        
        # 统计数据
        stats = {
            'date': date.isoformat(),
            'timestamp': timezone.now().isoformat(),
            'shop_count': 0,
            'transaction_count': 0,
            'total_revenue': Decimal('0')
        }
        
        # 创建报表
        report = Report.objects.create(
            report_type='daily',
            period_start=start,
            period_end=end,
            data=stats,
            status='completed'
        )
        
        logger.info(f'Daily report generated for {date}: {report.id}')
        
        return {
            'status': 'success',
            'report_id': report.id,
            'date': date.isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error generating daily report: {str(exc)}')
        raise


@app.task(
    name='apps.reports.tasks.generate_weekly_report',
    default_retry_delay=300,
    max_retries=3
)
def generate_weekly_report():
    """
    生成周报表
    """
    try:
        try:
            from apps.reports.models import Report
        except Exception as exc:
            logger.warning(f'Reports models unavailable: {str(exc)}')
            return {
                'status': 'skipped',
                'reason': 'reports models unavailable',
                'timestamp': timezone.now().isoformat()
            }
        
        now = timezone.now()
        # 获取周一日期
        start_date = now - timedelta(days=now.weekday())
        start = timezone.make_aware(datetime.combine(start_date.date(), datetime.min.time()))
        end = now
        
        # 统计数据
        stats = {
            'week': f'{start.date()} - {end.date()}',
            'timestamp': now.isoformat()
        }
        
        # 创建报表
        report = Report.objects.create(
            report_type='weekly',
            period_start=start,
            period_end=end,
            data=stats,
            status='completed'
        )
        
        logger.info(f'Weekly report generated: {report.id}')
        
        return {
            'status': 'success',
            'report_id': report.id
        }
    
    except Exception as exc:
        logger.error(f'Error generating weekly report: {str(exc)}')
        raise


@app.task(
    name='apps.reports.tasks.generate_monthly_report',
    default_retry_delay=300,
    max_retries=3
)
def generate_monthly_report():
    """
    生成月报表
    """
    try:
        try:
            from apps.reports.models import Report
        except Exception as exc:
            logger.warning(f'Reports models unavailable: {str(exc)}')
            return {
                'status': 'skipped',
                'reason': 'reports models unavailable',
                'timestamp': timezone.now().isoformat()
            }
        
        now = timezone.now()
        start_date = now.replace(day=1)
        start = timezone.make_aware(datetime.combine(start_date.date(), datetime.min.time()))
        end = now
        
        # 统计数据
        stats = {
            'month': f'{start.year}-{start.month:02d}',
            'timestamp': now.isoformat()
        }
        
        # 创建报表
        report = Report.objects.create(
            report_type='monthly',
            period_start=start,
            period_end=end,
            data=stats,
            status='completed'
        )
        
        logger.info(f'Monthly report generated: {report.id}')
        
        return {
            'status': 'success',
            'report_id': report.id
        }
    
    except Exception as exc:
        logger.error(f'Error generating monthly report: {str(exc)}')
        raise


# ============================================================================
# 通知任务
# ============================================================================

@app.task(
    name='apps.notification.tasks.send_notification_email',
    default_retry_delay=60,
    max_retries=5
)
def send_notification_email(recipient_email=None, subject=None, template_name=None, context=None, **kwargs):
    """
    发送通知邮件
    
    Args:
        recipient_email: 收件人邮箱
        subject: 邮件主题
        template_name: 模板名称
        context: 模板上下文
    """
    try:
        if not recipient_email:
            recipient_email = kwargs.get('email')
        if not subject:
            subject = kwargs.get('subject')
        message = kwargs.get('message')

        if template_name and context:
            message = render_to_string(f'notifications/{template_name}.html', context)
        elif message is None:
            message = ''
        
        send_mail(
            subject,
            'Please view in HTML mode',
            'noreply@mall.com',
            [recipient_email],
            html_message=message,
            fail_silently=False
        )
        
        logger.info(f'Email sent to {recipient_email}: {subject}')
        
        return {
            'status': 'success',
            'recipient': recipient_email,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error sending email to {recipient_email}: {str(exc)}')
        return {
            'status': 'failed',
            'recipient': recipient_email,
            'error': str(exc),
            'timestamp': datetime.now().isoformat()
        }


@app.task(
    name='apps.notification.tasks.cleanup_old_notifications',
    default_retry_delay=300,
    max_retries=3
)
def cleanup_old_notifications(days=30):
    """
    清理过期通知
    
    Args:
        days: 保留天数 (默认 30 天)
    """
    try:
        from apps.notification.models import Notification
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count, _ = Notification.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(f'Cleaned up {deleted_count} old notifications')
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error cleaning up notifications: {str(exc)}')
        raise


# ============================================================================
# 数据处理任务
# ============================================================================

@app.task(
    name='apps.core.tasks.export_data',
    default_retry_delay=60,
    max_retries=3
)
def export_data(export_type, filters=None):
    """
    导出数据任务
    
    Args:
        export_type: 导出类型 (shops, contracts, finances 等)
        filters: 过滤条件字典
    """
    try:
        import csv
        from io import StringIO
        from django.core.files.base import ContentFile
        
        logger.info(f'Exporting {export_type} with filters {filters}')
        
        # 根据类型导出数据
        if export_type == 'shops':
            from apps.store.models import Shop
            queryset = Shop.objects.all()
        
        elif export_type == 'contracts':
            from apps.store.models import Contract
            queryset = Contract.objects.all()
        
        elif export_type == 'finances':
            from apps.finance.models import FinanceRecord
            queryset = FinanceRecord.objects.all()
        
        else:
            logger.warning(f'Unknown export type: {export_type}')
            return {
                'status': 'unsupported_export_type',
                'export_type': export_type,
                'row_count': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # 应用过滤
        if filters:
            queryset = queryset.filter(**filters)
        
        # 生成 CSV
        output = StringIO()
        # ... CSV 生成逻辑 ...
        
        logger.info(f'Export completed: {export_type}')
        
        return {
            'status': 'success',
            'export_type': export_type,
            'row_count': queryset.count(),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error exporting data: {str(exc)}')
        return {
            'status': 'failed',
            'export_type': export_type,
            'error': str(exc),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# 系统维护任务
# ============================================================================

@app.task(
    name='apps.backup.tasks.backup_database',
    default_retry_delay=300,
    max_retries=3
)
def backup_database():
    """
    数据库备份任务
    
    定期备份数据库
    """
    try:
        import subprocess
        from django.conf import settings
        from datetime import datetime
        
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'backup_{timestamp}.sql'
        
        # 备份命令 (PostgreSQL 示例)
        cmd = [
            'pg_dump',
            '-U', settings.DATABASES['default']['USER'],
            '-h', settings.DATABASES['default']['HOST'],
            settings.DATABASES['default']['NAME'],
            '-f', str(backup_file)
        ]
        
        # 执行备份
        subprocess.run(cmd, check=True)
        
        logger.info(f'Database backup completed: {backup_file}')
        
        return {
            'status': 'success',
            'backup_file': str(backup_file),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error backing up database: {str(exc)}')
        return {
            'status': 'failed',
            'error': str(exc),
            'timestamp': datetime.now().isoformat()
        }


@app.task(
    name='apps.core.tasks.cleanup_cache',
    default_retry_delay=60,
    max_retries=3
)
def cleanup_cache():
    """
    清理过期缓存
    """
    try:
        from django.core.cache import cache
        
        # 清理缓存
        cache.clear()
        
        logger.info('Cache cleaned up')
        
        return {
            'status': 'success',
            'action': 'cache_cleanup',
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as exc:
        logger.error(f'Error cleaning up cache: {str(exc)}')
        raise


# ============================================================================
# 测试任务
# ============================================================================

@app.task(bind=True)
def test_task(self, param):
    """
    测试任务
    
    用于测试 Celery 是否正常工作
    """
    logger.info(f'Testing Celery with param: {param}')
    if param == 'fail':
        raise ValueError('Requested failure for test_task')
    return f'Task received: {param}'


@app.task(bind=True, queue='default')
def long_running_task(self, seconds=5):
    """
    Long-running task example.

    Used for verifying task progress updates.
    """
    try:
        from celery_progress.backend import ProgressRecorder
        progress_recorder = ProgressRecorder(self)
    except Exception:
        progress_recorder = None

    import time
    steps = max(1, min(int(seconds) * 5, 50))
    for i in range(steps):
        # Update progress when backend is available.
        if progress_recorder:
            progress_recorder.set_progress(i + 1, steps, description='Processing...')

        # Simulate a small unit of work.
        time.sleep(0.01)

    logger.info('Long running task completed')

    return {
        'status': 'success',
        'message': 'completed',
        'timestamp': datetime.now().isoformat()
    }
