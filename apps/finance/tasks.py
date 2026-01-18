"""
Finance 应用的 Celery 定时任务
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction

from apps.finance.services import FinanceService
from apps.store.models import Contract
from apps.finance.models import FinanceRecord

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_monthly_accounts_task(self, **kwargs):
    """
    生成当月账单的定时任务
    
    业务流程：
    1. 查询所有活跃的ACTIVE合同
    2. 为每个合同生成当月账单
    3. 记录生成结果
    
    执行计划：每天早上8点执行一次
    """
    try:
        logger.info("Starting generate_monthly_accounts_task")
        
        with transaction.atomic():
            # 查询所有活跃合同
            active_contracts = Contract.objects.filter(
                status=Contract.Status.ACTIVE
            ).select_for_update()
            
            result = {
                'total_contracts': 0,
                'generated_records': 0,
                'failed_contracts': 0,
                'errors': []
            }
            
            for contract in active_contracts:
                result['total_contracts'] += 1
                
                try:
                    # 检查本月是否已生成账单
                    today = date.today()
                    month_start = date(today.year, today.month, 1)
                    
                    # 计算月末
                    if today.month == 12:
                        month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
                    
                    # 检查本月是否已有账单
                    existing = FinanceRecord.objects.filter(
                        contract=contract,
                        fee_type=FinanceRecord.FeeType.RENT,
                        billing_period_start=month_start
                    ).exists()
                    
                    if not existing:
                        # 生成租金账单
                        record = FinanceRecord.objects.create(
                            contract=contract,
                            amount=contract.monthly_rent,
                            fee_type=FinanceRecord.FeeType.RENT,
                            billing_period_start=month_start,
                            billing_period_end=month_end,
                            status=FinanceRecord.Status.UNPAID
                        )
                        result['generated_records'] += 1
                        logger.info(f"Generated finance record for contract {contract.id}")
                    
                except Exception as e:
                    result['failed_contracts'] += 1
                    error_msg = f"Failed to generate account for contract {contract.id}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"generate_monthly_accounts_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_monthly_accounts_task: {str(e)}")
        # Celery 重试机制
        raise self.retry(exc=e, countdown=60 * 5)  # 5分钟后重试


@shared_task(bind=True, max_retries=3)
def send_payment_reminder_task(self, days_ahead: int = 3, **kwargs):
    """
    发送支付提醒的定时任务
    
    业务流程：
    1. 查询距离现在days_ahead天要到期的未支付账单
    2. 通过通知服务发送系统消息和短信
    3. 记录发送结果
    
    参数：
    - days_ahead: 提前多少天发送提醒（默认3天）
    
    执行计划：每天上午10点执行一次（工作日）
    """
    try:
        logger.info(f"Starting send_payment_reminder_task with days_ahead={days_ahead}")
        
        # 调用 FinanceService 发送提醒
        result = FinanceService.send_payment_reminder_notifications(days_ahead=days_ahead)
        
        logger.info(f"send_payment_reminder_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_payment_reminder_task: {str(e)}")
        raise self.retry(exc=e, countdown=60 * 5)


@shared_task(bind=True, max_retries=3)
def send_overdue_payment_alert_task(self, days_overdue: int = 0, **kwargs):
    """
    发送逾期告警的定时任务
    
    业务流程：
    1. 查询逾期days_overdue天以上的未支付账单
    2. 通过通知服务发送管理员告警
    3. 记录发送结果
    
    参数：
    - days_overdue: 查询多少天前开始逾期的账单（0表示任何逾期）
    
    执行计划：每天下午2点执行一次（工作日）
    """
    try:
        logger.info(f"Starting send_overdue_payment_alert_task with days_overdue={days_overdue}")
        
        # 调用 FinanceService 发送告警
        result = FinanceService.send_overdue_payment_alert(days_overdue=days_overdue)
        
        logger.info(f"send_overdue_payment_alert_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_overdue_payment_alert_task: {str(e)}")
        raise self.retry(exc=e, countdown=60 * 5)


@shared_task
def generate_finance_report_task(report_type: str = 'monthly', **kwargs):
    """
    生成财务报表的定时任务
    
    参数：
    - report_type: 报表类型（monthly/quarterly/annual）
    
    生成内容：
    - 当期收入统计
    - 当期支出统计
    - 欠款清单
    - 支付状态汇总
    """
    try:
        logger.info(f"Starting generate_finance_report_task for {report_type} report")
        
        # TODO: 实现财务报表生成逻辑
        # 1. 统计当期收入/支出
        # 2. 计算欠款总额和欠款客户数
        # 3. 分析支付趋势
        # 4. 生成报表并发送给管理员
        
        result = {
            'report_type': report_type,
            'generated_at': timezone.now().isoformat(),
            'status': 'pending_implementation'
        }
        
        logger.info(f"generate_finance_report_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_finance_report_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
