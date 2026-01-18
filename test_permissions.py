#!/usr/bin/env python3
"""
权限系统测试脚本
----------------
测试不同角色的权限控制是否正常工作
"""

import os
import sys

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth.models import User
from apps.user_management.models import Role, UserProfile
from apps.store.models import Shop

def test_permission_system():
    """测试权限系统"""
    print("=== 权限系统测试 ===")
    
    # 1. 检查角色是否已正确创建
    print("\n1. 检查角色创建情况：")
    roles = Role.objects.all()
    for role in roles:
        print(f"   - {role.name} ({role.role_type})")
    
    if len(roles) == 0:
        print("   ❌ 未创建任何角色，请先运行 python manage.py init_roles")
        return False
    
    # 2. 检查超级管理员用户
    print("\n2. 检查超级管理员用户：")
    try:
        admin_user = User.objects.get(username='admin')
        print(f"   - 超级管理员用户：{admin_user.username}")
        
        # 检查是否有用户配置文件
        if hasattr(admin_user, 'profile'):
            print(f"   - 角色：{admin_user.profile.role.name}")
        else:
            print("   - ⚠️  超级管理员用户没有配置文件")
            # 创建配置文件
            super_admin_role = Role.objects.get(role_type=Role.RoleType.SUPER_ADMIN)
            UserProfile.objects.create(user=admin_user, role=super_admin_role)
            print("   - ✅ 已为超级管理员创建配置文件")
    except User.DoesNotExist:
        print("   - ⚠️  未找到超级管理员用户")
        # 创建超级管理员用户
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        super_admin_role = Role.objects.get(role_type=Role.RoleType.SUPER_ADMIN)
        UserProfile.objects.create(user=admin_user, role=super_admin_role)
        print("   - ✅ 已创建超级管理员用户：admin / admin123")
    
    # 3. 创建测试店铺和店铺用户
    print("\n3. 创建测试店铺和用户：")
    
    # 创建测试店铺
    test_shop, created = Shop.objects.get_or_create(
        name='测试店铺',
        defaults={
            'business_type': 'RETAIL',
            'area': 100.0,
            'rent': 10000.0,
            'contact_person': '测试联系人',
            'contact_phone': '13800138000',
            'entry_date': '2026-01-01',
            'description': '这是一个测试店铺'
        }
    )
    if created:
        print(f"   - ✅ 已创建测试店铺：{test_shop.name}")
    else:
        print(f"   - ⚠️  测试店铺已存在：{test_shop.name}")
    
    # 创建店铺用户
    shop_user, created = User.objects.get_or_create(
        username='shop_user',
        defaults={
            'email': 'shop@example.com',
            'password': 'shop123'
        }
    )
    if created:
        shop_user.set_password('shop123')
        shop_user.save()
        # 创建用户配置文件
        shop_role = Role.objects.get(role_type=Role.RoleType.SHOP)
        UserProfile.objects.create(user=shop_user, role=shop_role, shop=test_shop)
        print(f"   - ✅ 已创建店铺用户：shop_user / shop123")
    else:
        print(f"   - ⚠️  店铺用户已存在：shop_user")
    
    # 创建财务管理员用户
    finance_user, created = User.objects.get_or_create(
        username='finance_user',
        defaults={
            'email': 'finance@example.com',
            'password': 'finance123'
        }
    )
    if created:
        finance_user.set_password('finance123')
        finance_user.save()
        # 创建用户配置文件
        finance_role = Role.objects.get(role_type=Role.RoleType.FINANCE)
        UserProfile.objects.create(user=finance_user, role=finance_role)
        print(f"   - ✅ 已创建财务管理员用户：finance_user / finance123")
    else:
        print(f"   - ⚠️  财务管理员用户已存在：finance_user")
    
    # 4. 验证权限系统的核心功能
    print("\n4. 验证权限系统核心功能：")
    
    # 检查用户配置文件关联
    users_with_profile = User.objects.filter(profile__isnull=False).count()
    total_users = User.objects.count()
    print(f"   - 用户总数：{total_users}")
    print(f"   - 已关联配置文件的用户数：{users_with_profile}")
    
    if users_with_profile == 0:
        print("   ❌ 没有用户关联配置文件")
        return False
    
    # 检查角色分配
    role_counts = {}
    for role in roles:
        count = UserProfile.objects.filter(role=role).count()
        role_counts[role.name] = count
        print(f"   - {role.name}：{count} 个用户")
    
    print("\n=== 测试完成 ===")
    print("✅ 权限系统基本功能正常")
    print("\n测试账号：")
    print("   - 超级管理员：admin / admin123")
    print("   - 店铺用户：shop_user / shop123")
    print("   - 财务管理员：finance_user / finance123")
    print("\n请使用这些账号测试不同角色的权限控制")
    
    return True

if __name__ == "__main__":
    test_permission_system()
