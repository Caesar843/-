from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.finance.models import FinanceRecord
from apps.finance.services import FinanceService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    生成缴费提醒的管理命令
    """
    help = '生成并发送缴费提醒'

    def add_arguments(self, parser):
        """
        添加命令行参数
        """
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='提前提醒的天数'
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            default=False,
            help='是否发送邮件提醒'
        )

    def handle(self, *args, **options):
        """
        处理命令执行
        """
        days_ahead = options['days_ahead']
        send_email = options['send_email']
        
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS(f'开始生成缴费提醒（提前 {days_ahead} 天）'))
        
        # 生成缴费提醒
        reminders = FinanceService.generate_payment_reminders(days_ahead)
        
        if reminders:
            self.stdout.write(self.style.WARNING(f'发现 {len(reminders)} 条待缴费记录需要提醒:'))
            
            for record in reminders:
                days_until_due = (record.billing_period_end - today).days
                self.stdout.write(
                    self.style.WARNING(
                        f'记录 ID: {record.id}, 合同: {record.contract}, '
                        f'费用类型: {record.get_fee_type_display()}, 金额: ¥{record.amount}, '
                        f'到期日期: {record.billing_period_end}, 剩余天数: {days_until_due}'
                    )
                )
                logger.warning(
                    f'Payment reminder: ID={record.id}, Contract={record.contract}, '
                    f'Fee type={record.get_fee_type_display()}, Amount=¥{record.amount}, '
                    f'Due date={record.billing_period_end}, Days left={days_until_due}'
                )
            
            if send_email:
                # 这里可以添加邮件发送逻辑
                self.stdout.write(self.style.INFO('邮件提醒功能已启用（模拟）'))
                for record in reminders:
                    self.stdout.write(
                        self.style.INFO(
                            f'[模拟] 向店铺 {record.contract.shop.name} 发送缴费提醒邮件'
                        )
                    )
        else:
            self.stdout.write(self.style.SUCCESS('没有发现需要提醒的待缴费记录'))
            logger.info('No payment reminders needed')
        
        self.stdout.write(self.style.SUCCESS('缴费提醒生成完成'))