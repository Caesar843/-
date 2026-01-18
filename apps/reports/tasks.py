"""
Reports 应用的 Celery 定时任务
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_report_task(**kwargs):
    """
    生成日报表的定时任务
    
    报表内容：
    1. 当日门店营业统计
    2. 当日新增店铺数
    3. 当日新增合同数
    4. 当日财务收入统计
    5. 当日客流量统计（从Device数据聚合）
    
    执行计划：每个工作日早上7点执行一次
    """
    try:
        logger.info("Starting generate_daily_report_task")
        
        from apps.store.models import Shop, Contract
        from apps.finance.models import FinanceRecord
        from apps.operations.models import ManualOperationData
        
        today = date.today()
        
        result = {
            'report_date': today.isoformat(),
            'generated_at': timezone.now().isoformat(),
            'statistics': {
                'active_shops': Shop.objects.filter(is_deleted=False).count(),
                'today_new_contracts': Contract.objects.filter(
                    created_at__date=today
                ).count(),
                'today_paid_amount': 0,
                'today_operation_data_records': 0
            }
        }
        
        # 统计当日财务收入
        try:
            from django.db.models import Sum
            paid_records = FinanceRecord.objects.filter(
                paid_at__date=today
            ).aggregate(total=Sum('amount'))
            result['statistics']['today_paid_amount'] = str(paid_records['total'] or 0)
        except Exception as e:
            logger.error(f"Failed to calculate daily paid amount: {str(e)}")
        
        # 统计当日运营数据记录数
        try:
            operation_data_count = ManualOperationData.objects.filter(
                created_at__date=today
            ).count()
            result['statistics']['today_operation_data_records'] = operation_data_count
        except Exception as e:
            logger.error(f"Failed to get operation data count: {str(e)}")
        
        # TODO: 发送报表给相关管理员
        # 可以通过邮件或系统通知发送
        
        logger.info(f"generate_daily_report_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_daily_report_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def generate_weekly_report_task(**kwargs):
    """
    生成周报表的定时任务
    
    报表内容：
    1. 本周营收汇总
    2. 本周新增店铺数
    3. 本周合同签署数
    4. 本周客流量趋势
    5. 本周逾期账单数
    
    执行计划：每周一早上8点执行一次
    """
    try:
        logger.info("Starting generate_weekly_report_task")
        
        from apps.store.models import Shop, Contract
        from apps.finance.models import FinanceRecord
        from django.db.models import Sum, Count, Q
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        result = {
            'report_period': f"{week_start.isoformat()} to {week_end.isoformat()}",
            'generated_at': timezone.now().isoformat(),
            'statistics': {
                'new_shops': 0,
                'new_contracts': 0,
                'weekly_revenue': 0,
                'overdue_records': 0
            }
        }
        
        # 统计周内新增店铺
        result['statistics']['new_shops'] = Shop.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_end,
            is_deleted=False
        ).count()
        
        # 统计周内新增合同
        result['statistics']['new_contracts'] = Contract.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_end
        ).count()
        
        # 统计周收入
        revenue = FinanceRecord.objects.filter(
            paid_at__date__gte=week_start,
            paid_at__date__lte=week_end,
            status=FinanceRecord.Status.PAID
        ).aggregate(total=Sum('amount'))
        result['statistics']['weekly_revenue'] = str(revenue['total'] or 0)
        
        # 统计逾期账单
        overdue = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            billing_period_end__lt=week_start
        ).count()
        result['statistics']['overdue_records'] = overdue
        
        # TODO: 生成可视化图表并发送给管理员
        
        logger.info(f"generate_weekly_report_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_weekly_report_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def generate_monthly_report_task(**kwargs):
    """
    生成月报表的定时任务
    
    报表内容：
    1. 月度营收汇总
    2. 月度新增店铺统计
    3. 月度合同续签率
    4. 月度客流量分析
    5. 月度财务对账
    6. 月度风险预警（逾期、即将到期等）
    
    执行计划：每个月1日早上9点执行
    """
    try:
        logger.info("Starting generate_monthly_report_task")
        
        from apps.store.models import Shop, Contract
        from apps.finance.models import FinanceRecord
        from django.db.models import Sum, Count, Q
        
        today = date.today()
        if today.month == 1:
            last_month_start = date(today.year - 1, 12, 1)
            last_month_end = date(today.year - 1, 12, 31)
        else:
            last_month_start = date(today.year, today.month - 1, 1)
            if today.month - 1 == 2:
                last_month_end = date(today.year, today.month - 1, 29) if today.year % 4 == 0 else date(today.year, today.month - 1, 28)
            else:
                last_month_end = date(today.year, today.month, 1) - timedelta(days=1)
        
        result = {
            'report_period': f"{last_month_start.year}-{last_month_start.month:02d}",
            'generated_at': timezone.now().isoformat(),
            'statistics': {
                'monthly_revenue': 0,
                'new_shops': 0,
                'new_contracts': 0,
                'total_active_shops': 0,
                'total_active_contracts': 0,
                'overdue_records': 0,
                'renewal_rate': 0
            }
        }
        
        # 统计月度收入
        revenue = FinanceRecord.objects.filter(
            paid_at__date__gte=last_month_start,
            paid_at__date__lte=last_month_end,
            status=FinanceRecord.Status.PAID
        ).aggregate(total=Sum('amount'))
        result['statistics']['monthly_revenue'] = str(revenue['total'] or 0)
        
        # 统计月内新增店铺
        result['statistics']['new_shops'] = Shop.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end,
            is_deleted=False
        ).count()
        
        # 统计月内新增合同
        result['statistics']['new_contracts'] = Contract.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # 当前活跃店铺和合同数
        result['statistics']['total_active_shops'] = Shop.objects.filter(is_deleted=False).count()
        result['statistics']['total_active_contracts'] = Contract.objects.filter(
            status=Contract.Status.ACTIVE
        ).count()
        
        # 逾期账单
        result['statistics']['overdue_records'] = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            billing_period_end__lt=last_month_start
        ).count()
        
        # TODO: 计算续签率（续签合同数/到期合同数）
        
        logger.info(f"generate_monthly_report_task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_monthly_report_task: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
