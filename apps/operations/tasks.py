"""
Operations 应用的 Celery 定时任务
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta

from apps.operations.services import DeviceDataAggregationService
from apps.store.models import Shop

logger = logging.getLogger(__name__)


@shared_task
def aggregate_hourly_device_data_task(**kwargs):
    """
    按小时聚合设备数据的定时任务
    
    业务流程：
    1. 查询上一个整点小时的所有设备数据
    2. 按店铺进行小时级聚合
    3. 存储聚合结果
    
    执行计划：每小时的第1分钟执行一次
    """
    try:
        logger.info("Starting aggregate_hourly_device_data_task")
        
        # 获取上一个小时
        now = timezone.now()
        last_hour = (now - timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        
        # 获取所有活跃店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        result = {
            'total_shops': shops.count(),
            'aggregated': 0,
            'failed': 0,
            'errors': []
        }
        
        for shop in shops:
            try:
                aggregation_data = DeviceDataAggregationService.aggregate_hourly_data(
                    shop_id=shop.id,
                    hour=last_hour
                )
                result['aggregated'] += 1
                logger.info(f"Hourly aggregation completed for shop {shop.id}")
                
            except Exception as e:
                result['failed'] += 1
                error_msg = f"Failed to aggregate hourly data for shop {shop.id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"aggregate_hourly_device_data_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in aggregate_hourly_device_data_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def aggregate_daily_device_data_task(**kwargs):
    """
    按日聚合设备数据的定时任务
    
    业务流程：
    1. 查询昨日的所有设备数据
    2. 按店铺进行日级聚合
    3. 生成日报统计
    
    执行计划：每天凌晨1点执行一次
    """
    try:
        logger.info("Starting aggregate_daily_device_data_task")
        
        # 获取昨日日期
        yesterday = (timezone.now() - timedelta(days=1)).date()
        
        # 获取所有活跃店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        result = {
            'total_shops': shops.count(),
            'aggregated': 0,
            'failed': 0,
            'errors': []
        }
        
        for shop in shops:
            try:
                aggregation_data = DeviceDataAggregationService.aggregate_daily_data(
                    shop_id=shop.id,
                    date=yesterday
                )
                result['aggregated'] += 1
                logger.info(f"Daily aggregation completed for shop {shop.id}")
                
            except Exception as e:
                result['failed'] += 1
                error_msg = f"Failed to aggregate daily data for shop {shop.id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"aggregate_daily_device_data_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in aggregate_daily_device_data_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def aggregate_monthly_device_data_task(**kwargs):
    """
    按月聚合设备数据的定时任务
    
    业务流程：
    1. 查询上月的所有设备数据
    2. 按店铺进行月级聚合
    3. 生成月度统计报告
    
    执行计划：每月1日凌晨2点执行一次
    """
    try:
        logger.info("Starting aggregate_monthly_device_data_task")
        
        # 获取上月日期
        today = timezone.now().date()
        if today.month == 1:
            last_month_year = today.year - 1
            last_month = 12
        else:
            last_month_year = today.year
            last_month = today.month - 1
        
        # 获取所有活跃店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        result = {
            'total_shops': shops.count(),
            'aggregated': 0,
            'failed': 0,
            'errors': []
        }
        
        for shop in shops:
            try:
                aggregation_data = DeviceDataAggregationService.aggregate_monthly_data(
                    shop_id=shop.id,
                    year=last_month_year,
                    month=last_month
                )
                result['aggregated'] += 1
                logger.info(f"Monthly aggregation completed for shop {shop.id}")
                
            except Exception as e:
                result['failed'] += 1
                error_msg = f"Failed to aggregate monthly data for shop {shop.id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"aggregate_monthly_device_data_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in aggregate_monthly_device_data_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def clean_device_data_task(**kwargs):
    """
    清洗设备数据的定时任务
    
    业务流程：
    1. 检测并移除重复数据
    2. 修复或删除异常数据
    3. 清理超期的临时数据
    4. 生成数据质量报告
    
    执行计划：每周日凌晨4点执行一次（周维护）
    """
    try:
        logger.info("Starting clean_device_data_task")
        
        # 调用数据清洗服务
        clean_result = DeviceDataAggregationService.clean_device_data()
        
        # 如果有错误，记录详细信息
        if clean_result.get('errors'):
            for error in clean_result['errors']:
                logger.error(f"Data cleaning error: {error}")
        
        logger.info(f"clean_device_data_task completed: {clean_result}")
        return clean_result
        
    except Exception as e:
        logger.error(f"Error in clean_device_data_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def check_device_online_status_task(**kwargs):
    """
    检查设备在线状态的定时任务
    
    业务流程：
    1. 查询所有在线的设备
    2. 检查最后活跃时间
    3. 如果超过10分钟未活跃则标记为离线
    4. 发送离线告警通知
    
    执行计划：每5分钟执行一次
    """
    try:
        logger.info("Starting check_device_online_status_task")
        
        from apps.operations.models import Device
        from django.utils import timezone
        from datetime import timedelta
        
        # 定义离线阈值（10分钟）
        offline_threshold = timezone.now() - timedelta(minutes=10)
        
        # 查询应该被标记为离线的设备
        devices_to_offline = Device.objects.filter(
            status=Device.DeviceStatus.ONLINE,
            last_active_at__lt=offline_threshold
        )
        
        result = {
            'total_checked': Device.objects.filter(status=Device.DeviceStatus.ONLINE).count(),
            'marked_offline': 0,
            'errors': []
        }
        
        for device in devices_to_offline:
            try:
                device.status = Device.DeviceStatus.OFFLINE
                device.save(update_fields=['status'])
                result['marked_offline'] += 1
                logger.warning(f"Device {device.device_id} marked as offline (last active: {device.last_active_at})")
                
                # TODO: 发送离线告警通知
                # NotificationService.create_notification(
                #     recipient_id=admin_id,
                #     notification_type='DEVICE_OFFLINE',
                #     title=f'设备离线告警',
                #     content=f'设备 {device.device_name}({device.device_id}) 已离线，最后活跃时间：{device.last_active_at}'
                # )
                
            except Exception as e:
                error_msg = f"Failed to update device {device.device_id} status: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"check_device_online_status_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in check_device_online_status_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
