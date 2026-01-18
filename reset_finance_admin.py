import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth.models import User
from apps.user_management.models import Role, UserProfile

# 创建或更新财务管理员用户
finance_user, created = User.objects.get_or_create(
    username='finance_admin',
    defaults={
        'is_staff': True,
        'is_active': True,
        'email': 'finance_admin@example.com'
    }
)

# 设置新密码
password = 'finance_admin123'
finance_user.set_password(password)
finance_user.save()

# 确保用户配置文件存在并关联到财务角色
if not hasattr(finance_user, 'profile'):
    # 获取财务角色
    try:
        finance_role = Role.objects.get(role_type=Role.RoleType.FINANCE)
        # 创建用户配置文件
        UserProfile.objects.create(user=finance_user, role=finance_role)
        print(f"✅ 已创建财务管理员用户配置文件")
    except Role.DoesNotExist:
        print("⚠️  未找到财务角色，请先运行 python manage.py init_roles")
else:
    # 更新角色为财务角色
    try:
        finance_role = Role.objects.get(role_type=Role.RoleType.FINANCE)
        finance_user.profile.role = finance_role
        finance_user.profile.save()
        print(f"✅ 已更新财务管理员用户角色")
    except Role.DoesNotExist:
        print("⚠️  未找到财务角色，请先运行 python manage.py init_roles")

# 输出结果
if created:
    print(f"✅ 已创建新的财务管理员用户")
else:
    print(f"✅ 已更新现有财务管理员用户")

print(f"\n财务管理员账号信息：")
print(f"  用户名：finance_admin")
print(f"  密码：{password}")
print(f"  邮箱：{finance_user.email}")
print(f"  是否活跃：{finance_user.is_active}")
print(f"  是否为 staff：{finance_user.is_staff}")
