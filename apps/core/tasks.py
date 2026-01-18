"""
Core 应用的通用 Celery 定时任务
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_data_task(days_retention: int = 30, **kwargs):
    """
    清理旧数据的定时任务
    
    清理对象：
    1. 30天前的通知和消息
    2. 30天前的操作日志
    3. 30天前的临时数据
    4. 失败的任务记录
    
    参数：
    - days_retention: 数据保留天数（默认30天）
    
    执行计划：每天凌晨3点执行一次
    """
    try:
        logger.info(f"Starting cleanup_old_data_task with days_retention={days_retention}")
        
        cutoff_date = timezone.now() - timedelta(days=days_retention)
        result = {
            'notifications_deleted': 0,
            'sms_records_deleted': 0,
            'total_deleted': 0,
            'errors': []
        }
        
        # 清理旧通知
        try:
            from apps.notification.models import Notification, SMSRecord
            
            # 删除30天前的已读通知
            deleted_notifications, _ = Notification.objects.filter(
                created_at__lt=cutoff_date,
                is_read=True
            ).delete()
            result['notifications_deleted'] = deleted_notifications
            logger.info(f"Deleted {deleted_notifications} old notifications")
            
            # 删除30天前的短信记录
            deleted_sms, _ = SMSRecord.objects.filter(
                created_at__lt=cutoff_date,
                status__in=['SENT', 'FAILED']  # 只删除已发送或已失败的
            ).delete()
            result['sms_records_deleted'] = deleted_sms
            logger.info(f"Deleted {deleted_sms} old SMS records")
            
            result['total_deleted'] = deleted_notifications + deleted_sms
            
        except Exception as e:
            error_msg = f"Failed to cleanup notifications: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        # TODO: 清理其他旧数据
        # - 操作日志（OperationLog）
        # - 临时文件
        # - 缓存数据
        
        logger.info(f"cleanup_old_data_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def send_system_health_report_task(**kwargs):
    """
    发送系统健康报告的定时任务
    
    报告内容：
    1. 数据库连接状态
    2. 缓存服务状态
    3. 消息队列状态（Celery）
    4. 存储空间使用情况
    5. 系统运行指标（CPU、内存、磁盘）
    
    执行计划：每天早上6点执行一次
    """
    try:
        logger.info("Starting send_system_health_report_task")
        
        from django.db import connection
        from django.contrib.auth.models import User
        
        report = {
            'timestamp': timezone.now().isoformat(),
            'database_status': 'unknown',
            'cache_status': 'unknown',
            'celery_status': 'unknown',
            'issues': []
        }
        
        # 检查数据库连接
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            report['database_status'] = 'ok'
        except Exception as e:
            report['database_status'] = 'error'
            report['issues'].append(f"Database connection failed: {str(e)}")
        
        # 检查用户数量和系统基本信息
        try:
            user_count = User.objects.count()
            admin_count = User.objects.filter(is_staff=True).count()
            report['system_info'] = {
                'total_users': user_count,
                'admin_users': admin_count
            }
        except Exception as e:
            report['issues'].append(f"Failed to get system info: {str(e)}")
        
        # TODO: 添加更多检查项
        # - 缓存系统健康检查
        # - Celery Worker 状态检查
        # - 存储空间检查
        # - 系统资源使用情况
        
        logger.info(f"send_system_health_report_task completed: {report}")
        return report
        
    except Exception as e:
        logger.error(f"Error in send_system_health_report_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def debug_task(**kwargs):
    """
    调试任务 - 用于测试Celery配置
    
    使用: celery -A config call apps.core.tasks.debug_task
    """
    logger.info("Debug task executed successfully!")
    return {
        'status': 'success',
        'timestamp': timezone.now().isoformat(),
        'message': 'Celery is working correctly!'
    }
