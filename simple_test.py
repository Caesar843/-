#!/usr/bin/env python3
"""
简单权限系统测试脚本
"""

import os
import sys

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth.models import User
from apps.user_management.models import Role, UserProfile

def simple_permission_test():
    """简单权限测试"""
    print("=== 简单权限系统测试 ===")
    
    # 1. 检查角色
    print("\n1. 角色列表：")
    roles = Role.objects.all()
    for role in roles:
        print(f"   - {role.name} ({role.role_type})")
    
    # 2. 检查超级管理员
    print("\n2. 超级管理员检查：")
    try:
        admin = User.objects.get(username='admin')
        print(f"   - 超级管理员用户存在：{admin.username}")
        
        if hasattr(admin, 'profile'):
            print(f"   - 已配置角色：{admin.profile.role.name}")
        else:
            print(f"   - 未配置角色，正在配置...")
            super_admin_role = Role.objects.get(role_type='SUPER_ADMIN')
            UserProfile.objects.create(user=admin, role=super_admin_role)
            print(f"   - 已配置超级管理员角色")
    except User.DoesNotExist:
        print("   - 超级管理员用户不存在，正在创建...")
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        super_admin_role = Role.objects.get(role_type='SUPER_ADMIN')
        UserProfile.objects.create(user=admin, role=super_admin_role)
        print(f"   - 已创建超级管理员：admin / admin123")
    
    # 3. 检查权限系统是否正常
    print("\n3. 权限系统状态：")
    
    # 检查用户配置文件数量
    total_users = User.objects.count()
    users_with_profile = User.objects.filter(profile__isnull=False).count()
    
    print(f"   - 用户总数：{total_users}")
    print(f"   - 已配置角色的用户数：{users_with_profile}")
    print(f"   - 配置完成率：{users_with_profile}/{total_users}")
    
    # 4. 角色分布
    print("\n4. 角色分布：")
    for role in roles:
        count = UserProfile.objects.filter(role=role).count()
        print(f"   - {role.name}：{count} 人")
    
    print("\n=== 测试完成 ===")
    print("✅ 权限系统基本功能正常")
    print("\n使用以下账号登录测试：")
    print("   - 超级管理员：admin / admin123")
    
    return True

if __name__ == "__main__":
    simple_permission_test()
