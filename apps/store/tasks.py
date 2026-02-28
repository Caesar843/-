"""
Store 应用的 Celery 定时任务
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction

from apps.store.models import Contract
from apps.notification.services import NotificationService
from django.contrib.auth.models import User
from apps.audit.services import log_audit_action
from apps.audit.utils import serialize_instance

logger = logging.getLogger(__name__)

CONTRACT_AUDIT_FIELDS = [
    "id",
    "shop_id",
    "start_date",
    "end_date",
    "monthly_rent",
    "deposit",
    "payment_cycle",
    "status",
    "reviewed_by_id",
    "reviewed_at",
    "review_comment",
]


@shared_task(bind=True, max_retries=3)
def send_renewal_reminder_task(self, days_until_expiry: int = 30, **kwargs):
    """
    发送合同续签提醒的定时任务
    
    业务流程：
    1. 查询将在days_until_expiry天内到期的ACTIVE合同
    2. 为相关店铺联系人发送续签提醒
    3. 记录提醒结果
    
    参数：
    - days_until_expiry: 合同将在多少天后到期时发送提醒（默认30天）
    
    执行计划：每月1日发送30天内到期的续签提醒
    """
    try:
        logger.info(f"Starting send_renewal_reminder_task with days_until_expiry={days_until_expiry}")
        
        with transaction.atomic():
            tenant_id = kwargs.get("tenant_id")
            today = date.today()
            expiry_date = today + timedelta(days=days_until_expiry)
            
            # 查询将在指定日期范围内到期的活跃合同
            expiring_contracts = Contract.objects.filter(
                status=Contract.Status.ACTIVE,
                end_date__lte=expiry_date,
                end_date__gt=today
            ).select_related('shop')
            if tenant_id is not None:
                expiring_contracts = expiring_contracts.filter(tenant_id=tenant_id)
            
            result = {
                'total_contracts': 0,
                'reminders_sent': 0,
                'failed': 0,
                'errors': []
            }
            
            for contract in expiring_contracts:
                result['total_contracts'] += 1
                
                try:
                    # 获取店铺联系人对应的用户或管理员
                    admins = User.objects.filter(is_staff=True)
                    if tenant_id is not None:
                        admins = admins.filter(profile__tenant_id=tenant_id)
                    
                    if not admins.exists():
                        # 如果没有管理员，尝试获取超级用户
                        admins = User.objects.filter(is_superuser=True)
                        if tenant_id is not None:
                            admins = admins.filter(profile__tenant_id=tenant_id)
                    
                    for admin in admins:
                        try:
                            days_remaining = (contract.end_date - today).days
                            
                            # 发送续签提醒通知
                            notification = NotificationService.create_notification(
                                recipient_id=admin.id,
                                notification_type=NotificationService.Notification.Type.RENEWAL_REMINDER,
                                title=f'合同续签提醒',
                                content=f'店铺"{contract.shop.name}"的合同将在{days_remaining}天后（{contract.end_date}）到期，'
                                       f'请及时与店主联系进行续签协议。月租金：¥{contract.monthly_rent}。',
                                related_model='Contract',
                                related_id=contract.id
                            )
                            result['reminders_sent'] += 1
                            logger.info(f"Renewal reminder sent for contract {contract.id}")
                            
                        except Exception as e:
                            result['failed'] += 1
                            error_msg = f"Failed to send renewal reminder: {str(e)}"
                            result['errors'].append(error_msg)
                            logger.error(error_msg)
                            
                except Exception as e:
                    result['failed'] += 1
                    error_msg = f"Error processing contract {contract.id}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"send_renewal_reminder_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_renewal_reminder_task: {str(e)}")
        raise self.retry(exc=e, countdown=60 * 5)


@shared_task
def auto_expire_contracts_task(**kwargs):
    """
    自动标记已过期合同的定时任务
    
    业务流程：
    1. 查询end_date已过期的ACTIVE合同
    2. 自动转移至EXPIRED状态
    3. 记录处理结果
    
    执行计划：每天凌晨1点执行一次
    """
    try:
        logger.info("Starting auto_expire_contracts_task")
        
        today = date.today()
        tenant_id = kwargs.get("tenant_id")
        
        with transaction.atomic():
            # 查询已过期的活跃合同
            expired_contracts = Contract.objects.filter(
                status=Contract.Status.ACTIVE,
                end_date__lt=today
            ).select_for_update()
            if tenant_id is not None:
                expired_contracts = expired_contracts.filter(tenant_id=tenant_id)
            
            result = {
                'total_expired': 0,
                'marked_as_expired': 0,
                'errors': []
            }
            
            for contract in expired_contracts:
                result['total_expired'] += 1
                
                try:
                    # 标记为过期
                    before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
                    contract.status = Contract.Status.EXPIRED
                    contract.save(update_fields=['status', 'updated_at'])
                    after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
                    log_audit_action(
                        action="expire_contract",
                        module="contract",
                        instance=contract,
                        before_data=before_data,
                        after_data=after_data,
                    )
                    result['marked_as_expired'] += 1
                    logger.info(f"Contract {contract.id} automatically marked as expired")
                    
                except Exception as e:
                    error_msg = f"Failed to mark contract {contract.id} as expired: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"auto_expire_contracts_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_expire_contracts_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def generate_contract_statistics_task(**kwargs):
    """
    生成合同统计数据的定时任务
    
    统计内容：
    - 当月新增合同数
    - 当月到期合同数
    - 当月续签合同数
    - 合同分布统计（按业态、金额段等）
    
    执行计划：每天早上9点执行一次
    """
    try:
        logger.info("Starting generate_contract_statistics_task")
        
        today = date.today()
        month_start = date(today.year, today.month, 1)
        tenant_id = kwargs.get("tenant_id")
        contract_qs = Contract.objects.all()
        if tenant_id is not None:
            contract_qs = contract_qs.filter(tenant_id=tenant_id)
        
        # TODO: 实现合同统计逻辑
        result = {
            'period': f"{today.year}-{today.month:02d}",
            'new_contracts': 0,
            'expiring_contracts': 0,
            'renewed_contracts': 0,
            'total_active_contracts': contract_qs.filter(status=Contract.Status.ACTIVE).count(),
            'status': 'pending_implementation'
        }
        
        logger.info(f"generate_contract_statistics_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_contract_statistics_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
