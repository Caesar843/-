from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.store.models import Contract
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    检查合同到期情况的管理命令
    """
    help = '检查即将到期的合同并记录日志'

    def handle(self, *args, **options):
        """
        处理命令执行
        """
        today = timezone.now().date()
        # 检查30天内到期的合同
        thirty_days_later = today + timezone.timedelta(days=30)
        
        # 查找即将到期的活跃合同
        expiring_contracts = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=thirty_days_later
        )
        
        if expiring_contracts.exists():
            self.stdout.write(self.style.WARNING(f'发现 {expiring_contracts.count()} 份即将到期的合同:'))
            
            for contract in expiring_contracts:
                days_until_expiry = (contract.end_date - today).days
                self.stdout.write(
                    self.style.WARNING(
                        f'合同 ID: {contract.id}, 店铺: {contract.shop.name}, '
                        f'到期日期: {contract.end_date}, 剩余天数: {days_until_expiry}'
                    )
                )
                logger.warning(
                    f'Contract expiring soon: ID={contract.id}, Shop={contract.shop.name}, '
                    f'End date={contract.end_date}, Days left={days_until_expiry}'
                )
        else:
            self.stdout.write(self.style.SUCCESS('没有发现即将到期的合同'))
            logger.info('No expiring contracts found')
        
        # 检查已过期但状态仍为ACTIVE的合同
        expired_contracts = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            end_date__lt=today
        )
        
        if expired_contracts.exists():
            self.stdout.write(self.style.ERROR(f'发现 {expired_contracts.count()} 份已过期但状态仍为生效的合同:'))
            
            for contract in expired_contracts:
                days_expired = (today - contract.end_date).days
                self.stdout.write(
                    self.style.ERROR(
                        f'合同 ID: {contract.id}, 店铺: {contract.shop.name}, '
                        f'到期日期: {contract.end_date}, 已过期天数: {days_expired}'
                    )
                )
                # 自动更新状态为EXPIRED
                contract.status = Contract.Status.EXPIRED
                contract.save()
                logger.error(
                    f'Contract expired: ID={contract.id}, Shop={contract.shop.name}, '
                    f'End date={contract.end_date}, Days expired={days_expired}, Status updated to EXPIRED'
                )
        else:
            self.stdout.write(self.style.SUCCESS('没有发现已过期但状态仍为生效的合同'))
            logger.info('No expired contracts with ACTIVE status found')