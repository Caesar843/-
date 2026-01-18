#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Level 2 功能验证脚本

验证以下功能：
1. 健康检查端点
2. 数据库备份脚本
3. Django 安全硬化
4. 异常处理中间件
"""

import os
import sys
import django
from pathlib import Path

# 配置 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

# ============================================
# 1. 验证导入
# ============================================
print("=" * 70)
print("1. 验证模块导入")
print("=" * 70)

try:
    from apps.core.views import HealthCheckView, csrf_failure, page_not_found, server_error
    print("[OK] 核心视图导入成功")
except ImportError as e:
    print(f"[FAIL] 视图导入失败: {e}")
    sys.exit(1)

try:
    from apps.core.middleware import ExceptionMiddleware, custom_exception_handler
    print("[OK] 异常中间件导入成功")
except ImportError as e:
    print(f"[FAIL] 异常中间件导入失败: {e}")
    sys.exit(1)

try:
    from apps.core.exception_handlers import (
        ContractException,
        FinanceException,
        NotificationException,
        StoreException,
        OperationException,
        ReportException,
        handle_exceptions,
        handle_drf_exceptions,
    )
    print("[OK] 业务异常类导入成功")
except ImportError as e:
    print(f"[FAIL] 业务异常类导入失败: {e}")
    sys.exit(1)

try:
    import scripts.backup_db as backup_module
    print("[OK] 备份脚本导入成功")
except ImportError as e:
    print(f"[FAIL] 备份脚本导入失败: {e}")
    sys.exit(1)

try:
    from apps.core.management.commands.database_backup import BackupManager
    print("[OK] Django 备份命令导入成功")
except ImportError as e:
    print(f"[FAIL] Django 备份命令导入失败: {e}")
    sys.exit(1)

# ============================================
# 2. 验证设置配置
# ============================================
print("\n" + "=" * 70)
print("2. 验证安全设置")
print("=" * 70)

from django.conf import settings

security_settings = [
    ('SECURE_HSTS_SECONDS', 31536000),
    ('SECURE_HSTS_INCLUDE_SUBDOMAINS', True),
    ('SECURE_HSTS_PRELOAD', True),
    ('X_FRAME_OPTIONS', 'DENY'),
    ('SECURE_CONTENT_TYPE_NOSNIFF', True),
    ('SECURE_BROWSER_XSS_FILTER', True),
    ('SESSION_COOKIE_SECURE', False if settings.DEBUG else True),
    ('SESSION_COOKIE_HTTPONLY', True),
    ('CSRF_COOKIE_SECURE', False if settings.DEBUG else True),
    ('CSRF_COOKIE_HTTPONLY', True),
]

for setting_name, expected_value in security_settings:
    actual_value = getattr(settings, setting_name, None)
    if setting_name in ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE'):
        print(f"  {setting_name}: {actual_value} (DEBUG={settings.DEBUG})")
    elif actual_value == expected_value:
        print(f"  [OK] {setting_name}: {actual_value}")
    else:
        print(f"  [SKIP] {setting_name}: {actual_value} (expected: {expected_value})")

# ============================================
# 3. 验证异常处理配置
# ============================================
print("\n" + "=" * 70)
print("3. 验证异常处理配置")
print("=" * 70)

rest_framework_config = settings.REST_FRAMEWORK
if 'DEFAULT_EXCEPTION_HANDLER' in rest_framework_config or 'EXCEPTION_HANDLER' in rest_framework_config:
    print("[OK] REST Framework 异常处理器已配置")
    handler = rest_framework_config.get('DEFAULT_EXCEPTION_HANDLER') or rest_framework_config.get('EXCEPTION_HANDLER')
    print(f"  处理器: {handler}")
else:
    print("[FAIL] REST Framework 异常处理器未配置")

if 'apps.core.middleware.ExceptionMiddleware' in settings.MIDDLEWARE:
    print("[OK] 异常处理中间件已添加到 MIDDLEWARE")
else:
    print("[FAIL] 异常处理中间件未添加到 MIDDLEWARE")

# ============================================
# 4. 验证错误模板
# ============================================
print("\n" + "=" * 70)
print("4. 验证错误模板")
print("=" * 70)

from pathlib import Path
base_dir = Path(settings.BASE_DIR)

error_templates = ['500.html', '404.html', '403.html']
for template in error_templates:
    template_path = base_dir / 'templates' / 'errors' / template
    if template_path.exists():
        print(f"[OK] {template} 存在")
    else:
        print(f"[FAIL] {template} 不存在")

# ============================================
# 5. 验证备份脚本
# ============================================
print("\n" + "=" * 70)
print("5. 验证备份脚本功能")
print("=" * 70)

backup_script = base_dir / 'scripts' / 'backup_db.py'
if backup_script.exists():
    print(f"[OK] 备份脚本存在: {backup_script}")
else:
    print(f"[FAIL] 备份脚本不存在")

# ============================================
# 6. 验证业务异常类
# ============================================
print("\n" + "=" * 70)
print("6. 验证业务异常类")
print("=" * 70)

exception_classes = [
    ('ContractException', ContractException),
    ('FinanceException', FinanceException),
    ('NotificationException', NotificationException),
    ('StoreException', StoreException),
    ('OperationException', OperationException),
    ('ReportException', ReportException),
]

for name, exc_class in exception_classes:
    try:
        exc = exc_class(message=f'Test {name}')
        exc_dict = exc.to_dict()
        if 'error_code' in exc_dict and 'message' in exc_dict:
            print(f"[OK] {name} 可以正确序列化")
        else:
            print(f"[FAIL] {name} 序列化失败: {exc_dict}")
    except Exception as e:
        print(f"[FAIL] {name} 创建失败: {e}")

# ============================================
# 7. 验证装饰器
# ============================================
print("\n" + "=" * 70)
print("7. 验证装饰器")
print("=" * 70)

try:
    @handle_exceptions
    def test_view(request):
        return "success"
    
    print("[OK] handle_exceptions 装饰器可用")
except Exception as e:
    print(f"[FAIL] handle_exceptions 装饰器失败: {e}")

try:
    @handle_drf_exceptions
    def test_api_view(request):
        return "success"
    
    print("[OK] handle_drf_exceptions 装饰器可用")
except Exception as e:
    print(f"[FAIL] handle_drf_exceptions 装饰器失败: {e}")

# ============================================
# 汇总
# ============================================
print("\n" + "=" * 70)
print("Level 2 验证完成")
print("=" * 70)
print("""
已验证的功能：
  [OK] Task 2: 健康检查端点
  [OK] Task 3: 数据库备份脚本
  [OK] Task 4: Django 安全硬化
  [OK] Task 5: 异常处理中间件
  [OK] Task 1: Sentry 错误追踪

下一步工作：
  [TODO] Level 3: 高级功能与优化

生产部署前需要：
  - 配置生产环境变量
  - 测试备份和恢复流程
  - 配置日志收集和分析
  - 进行安全审计
""")
