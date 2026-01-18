from django.core.management.base import BaseCommand
from apps.user_management.models import Role


class Command(BaseCommand):
    """
    初始化系统默认角色
    --------------
    创建系统预定义的5个角色：入驻店铺、商场运营专员、财务管理员、商场管理层、超级管理员
    """
    
    help = 'Initialize default roles for the system'
    
    def handle(self, *args, **kwargs):
        # 定义默认角色配置
        default_roles = [
            {
                'role_type': 'SUPER_ADMIN',
                'name': '超级管理员',
                'description': '拥有系统最高权限，可配置系统规则，管理所有数据和用户'
            },
            {
                'role_type': 'MANAGEMENT',
                'name': '商场管理层',
                'description': '负责商场整体运营管理，查看各类报表和汇总数据'
            },
            {
                'role_type': 'OPERATION',
                'name': '商场运营专员',
                'description': '负责店铺入驻审核、活动管理等日常运营工作'
            },
            {
                'role_type': 'FINANCE',
                'name': '财务管理员',
                'description': '负责审核费用数据、管理财务记录等财务相关工作'
            },
            {
                'role_type': 'SHOP',
                'name': '入驻店铺',
                'description': '入驻商场的店铺账号，只能查看和管理自己店铺的数据'
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for role_config in default_roles:
            role, created = Role.objects.get_or_create(
                role_type=role_config['role_type'],
                defaults={
                    'name': role_config['name'],
                    'description': role_config['description']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name}"))
            else:
                existing_count += 1
                self.stdout.write(self.style.NOTICE(f"Role already exists: {role.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nInitialization complete!"))
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count} roles"))
        self.stdout.write(self.style.SUCCESS(f"Existing: {existing_count} roles"))
