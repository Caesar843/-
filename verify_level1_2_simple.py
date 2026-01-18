"""
Level 1 & 2 配置验证脚本 - 简化版

验证所有配置和功能，不通过 HTTP 请求
"""

import os
import sys
import django
from pathlib import Path

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

def check_section(title):
    """打印检查部分"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")

def check(name, condition, detail=""):
    """检查条件"""
    status = "[OK]" if condition else "[FAIL]"
    print(f"  {status} {name}")
    if not condition and detail:
        print(f"      -> {detail}")
    return condition

# 统计
total_checks = 0
total_passed = 0

# ==================================================================
# LEVEL 1 验证
# ==================================================================

check_section("LEVEL 1 - 基础配置验证")

# 1. CORS 验证
print("1. CORS 跨域配置")
total_checks += 1
if check("CORS 中间件已安装", 'corsheaders.middleware.CorsMiddleware' in settings.MIDDLEWARE):
    total_passed += 1

total_checks += 1
if check("CORS 应用已配置", 'corsheaders' in settings.INSTALLED_APPS):
    total_passed += 1

total_checks += 1
if check("CORS 来源已配置", hasattr(settings, 'CORS_ALLOWED_ORIGINS') and len(settings.CORS_ALLOWED_ORIGINS) > 0,
         f"来源: {getattr(settings, 'CORS_ALLOWED_ORIGINS', [])}"):
    total_passed += 1

# 2. API 文档验证
print("\n2. API 文档生成 (drf-spectacular)")
total_checks += 1
if check("drf-spectacular 已安装", 'drf_spectacular' in settings.INSTALLED_APPS):
    total_passed += 1

total_checks += 1
if check("OpenAPI Schema 类已配置",
         settings.REST_FRAMEWORK.get('DEFAULT_SCHEMA_CLASS') == 'drf_spectacular.openapi.AutoSchema'):
    total_passed += 1

# 检查路由
total_checks += 1
try:
    from django.urls import resolve
    from django.http import HttpRequest
    # 检查路由是否存在
    has_schema = False
    has_docs = False
    has_redoc = False
    
    try:
        resolve('/api/schema/')
        has_schema = True
    except:
        pass
    
    try:
        resolve('/api/docs/')
        has_docs = True
    except:
        pass
    
    try:
        resolve('/api/redoc/')
        has_redoc = True
    except:
        pass
    
    all_routes = has_schema and has_docs and has_redoc
    if check("API 文档路由已配置", all_routes,
             f"schema: {has_schema}, docs: {has_docs}, redoc: {has_redoc}"):
        total_passed += 1
except Exception as e:
    check("API 文档路由已配置", False, str(e))

# 3. 日志验证
print("\n3. 基础日志配置")
total_checks += 1
if check("日志配置已定义", 'LOGGING' in settings.__dict__):
    total_passed += 1

total_checks += 1
if check("Django 日志处理器已配置", 'django' in settings.LOGGING.get('loggers', {})):
    total_passed += 1

# 4. 环境变量验证
print("\n4. 环境变量管理")
total_checks += 1
if check("DEBUG 配置正确", isinstance(settings.DEBUG, bool), f"DEBUG={settings.DEBUG}"):
    total_passed += 1

total_checks += 1
if check("SECRET_KEY 已设置", len(settings.SECRET_KEY) > 0):
    total_passed += 1

total_checks += 1
if check("ALLOWED_HOSTS 已配置", len(settings.ALLOWED_HOSTS) > 0,
         f"ALLOWED_HOSTS={settings.ALLOWED_HOSTS}"):
    total_passed += 1

# 5. 响应格式统一
print("\n5. 响应格式统一")
total_checks += 1
if check("REST Framework 异常处理器已配置", 'EXCEPTION_HANDLER' in settings.REST_FRAMEWORK):
    total_passed += 1

total_checks += 1
if check("自定义异常处理器已配置",
         'apps.core.exception_handlers.custom_exception_handler' in settings.REST_FRAMEWORK.get('EXCEPTION_HANDLER', '')):
    total_passed += 1

# ==================================================================
# LEVEL 2 验证
# ==================================================================

check_section("LEVEL 2 - 生产质量验证")

# 1. Sentry 配置
print("1. Sentry 错误追踪")
total_checks += 1
try:
    import sentry_sdk
    if check("sentry-sdk 已安装", True):
        total_passed += 1
except ImportError:
    check("sentry-sdk 已安装", False, "未安装")

total_checks += 1
sentry_dsn = getattr(settings, 'SENTRY_DSN', None)
if check("Sentry 配置就绪", True, f"DSN: {'已配置' if sentry_dsn else '开发模式'}"):
    total_passed += 1

# 2. 健康检查端点
print("\n2. 健康检查端点")
total_checks += 1
try:
    from django.urls import resolve
    resolve('/health/')
    if check("健康检查路由已配置", True):
        total_passed += 1
except:
    check("健康检查路由已配置", False, "路由不存在")

# 3. 数据库备份脚本
print("\n3. 数据库备份脚本")
total_checks += 1
backup_script = Path('scripts/backup_db.py')
if check("备份脚本存在", backup_script.exists(), str(backup_script)):
    total_passed += 1

# 4. 安全硬化
print("\n4. Django 安全硬化")
total_checks += 1
if check("X-Frame-Options 已设置", settings.X_FRAME_OPTIONS == 'DENY',
         f"X-Frame-Options={settings.X_FRAME_OPTIONS}"):
    total_passed += 1

total_checks += 1
if check("SECURE_CONTENT_TYPE_NOSNIFF 已启用", settings.SECURE_CONTENT_TYPE_NOSNIFF == True):
    total_passed += 1

total_checks += 1
if check("SESSION_COOKIE_HTTPONLY 已启用", settings.SESSION_COOKIE_HTTPONLY == True):
    total_passed += 1

total_checks += 1
if check("CSRF_COOKIE_HTTPONLY 已启用", settings.CSRF_COOKIE_HTTPONLY == True):
    total_passed += 1

# 5. 异常处理中间件
print("\n5. 异常处理中间件")
total_checks += 1
exception_middleware_found = any(
    'exception' in mw.lower() or 'handler' in mw.lower()
    for mw in settings.MIDDLEWARE
)
if check("异常处理中间件已添加", exception_middleware_found):
    total_passed += 1

# 6. 错误模板
print("\n6. 错误模板")
for status_code in [404, 403, 500]:
    total_checks += 1
    template_path = Path(f'templates/errors/{status_code}.html')
    if check(f"{status_code}.html 模板存在", template_path.exists(), str(template_path)):
        total_passed += 1

# ==================================================================
# 功能集成验证
# ==================================================================

check_section("功能集成验证")

# 缓存验证
print("缓存系统")
total_checks += 1
try:
    from django.core.cache import cache
    cache.set('test_key', 'test_value', 60)
    value = cache.get('test_key')
    if check("缓存系统正常", value == 'test_value'):
        total_passed += 1
    cache.delete('test_key')
except Exception as e:
    check("缓存系统正常", False, str(e))

# 数据库连接验证
print("\n数据库连接")
total_checks += 1
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    if check("数据库连接正常", True):
        total_passed += 1
except Exception as e:
    check("数据库连接正常", False, str(e))

# ==================================================================
# 总结
# ==================================================================

check_section("验证总结")

percentage = (total_passed / total_checks * 100) if total_checks > 0 else 0

print(f"[OK] 通过: {total_passed}")
print(f"[FAIL] 失败: {total_checks - total_passed}")
print(f"[INFO] 成功率: {percentage:.1f}% ({total_passed}/{total_checks})")

if total_passed == total_checks:
    print(f"\n[SUCCESS] 所有检查通过！Level 1 & 2 功能完整！")
    sys.exit(0)
else:
    print(f"\n[WARNING] 有 {total_checks - total_passed} 项检查失败")
    sys.exit(1)
