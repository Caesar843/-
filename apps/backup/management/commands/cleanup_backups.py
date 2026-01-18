from django.core.management.base import BaseCommand, CommandError
from apps.backup.services import BackupService


class Command(BaseCommand):
    """
    Django管理命令：清理过期的备份文件
    
    使用方法:
        python manage.py cleanup_backups --days=30  # 删除30天前的备份
        python manage.py cleanup_backups  # 默认删除30天前的备份
    """
    
    help = '清理过期的备份文件'
    
    def add_arguments(self, parser):
        """定义命令参数"""
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='保留天数，超过此天数的备份将被删除（默认: 30天）'
        )
        
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认删除，不使用此参数则为预览模式'
        )
    
    def handle(self, *args, **options):
        """执行清理命令"""
        days = options['days']
        confirm = options['confirm']
        
        if days <= 0:
            raise CommandError('保留天数必须大于0')
        
        self.stdout.write(self.style.WARNING(
            f'{'确认' if confirm else '预览'}删除{days}天前的备份...\n'
        ))
        
        try:
            service = BackupService()
            deleted_count = service.delete_old_backups(days=days)
            
            if deleted_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 成功删除 {deleted_count} 个过期备份'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'没有过期的备份需要删除'
                ))
            
        except Exception as e:
            raise CommandError(f'清理失败: {str(e)}')
