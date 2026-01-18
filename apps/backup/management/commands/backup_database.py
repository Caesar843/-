from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from apps.backup.services import BackupService


class Command(BaseCommand):
    """
    Django管理命令：执行数据备份
    
    使用方法:
        python manage.py backup_database --type=FULL --data-types=SHOP,CONTRACT,FINANCE
        python manage.py backup_database  # 默认全量备份，备份所有数据
    """
    
    help = '执行数据库备份操作'
    
    def add_arguments(self, parser):
        """定义命令参数"""
        parser.add_argument(
            '--type',
            type=str,
            default='FULL',
            help='备份类型: FULL 或 INCREMENTAL (默认: FULL)'
        )
        
        parser.add_argument(
            '--data-types',
            type=str,
            default='SHOP,CONTRACT,OPERATION,FINANCE,LOG',
            help='要备份的数据类型，用逗号分隔 (默认: SHOP,CONTRACT,OPERATION,FINANCE,LOG)'
        )
        
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='备份说明或备注'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            default=None,
            help='执行备份的用户用户名（默认: 系统自动备份）'
        )
    
    def handle(self, *args, **options):
        """执行备份命令"""
        # 验证参数
        backup_type = options['type'].upper()
        if backup_type not in ['FULL', 'INCREMENTAL']:
            raise CommandError('备份类型必须是 FULL 或 INCREMENTAL')
        
        # 解析数据类型
        data_types = [dt.strip().upper() for dt in options['data_types'].split(',')]
        valid_types = ['SHOP', 'CONTRACT', 'OPERATION', 'FINANCE', 'LOG']
        for dt in data_types:
            if dt not in valid_types:
                raise CommandError(f'无效的数据类型: {dt}。有效类型: {", ".join(valid_types)}')
        
        # 获取执行用户
        user = None
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                raise CommandError(f'用户不存在: {options["user"]}')
        
        # 执行备份
        try:
            self.stdout.write(self.style.WARNING(f'开始执行{backup_type}备份...'))
            
            service = BackupService()
            backup_record = service.create_backup(
                data_types=data_types,
                backup_type=backup_type,
                user=user,
                description=options['description']
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ 备份成功!\n'
                f'  备份名称: {backup_record.backup_name}\n'
                f'  备份类型: {backup_record.get_backup_type_display()}\n'
                f'  文件大小: {self._format_size(backup_record.file_size)}\n'
                f'  数据类型: {", ".join(backup_record.data_types)}\n'
                f'  创建时间: {backup_record.created_at.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'  文件路径: {backup_record.file_path}'
            ))
            
        except Exception as e:
            raise CommandError(f'备份失败: {str(e)}')
    
    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{size:.2f} TB'
