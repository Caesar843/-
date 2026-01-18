# 🎯 工业级缺失功能 - 难度排序和优先级规划

## 📊 一览表

```
难度等级    | 工程量    | 时间估算  | 优先级
┌─────────────────────────────────────────────────┐
1. 极易     | 1-2 天    | ⭐☆☆☆☆  | P2
2. 简易     | 3-7 天    | ⭐⭐☆☆☆ | P2
3. 中等     | 1-3 周    | ⭐⭐⭐☆☆ | P1
4. 困难     | 2-4 周    | ⭐⭐⭐⭐☆ | P1
5. 很困难   | 1-2 个月  | ⭐⭐⭐⭐☆ | P1
6. 极困难   | 2-6 个月  | ⭐⭐⭐⭐⭐ | P0
```

---

## 🟩 第 1 级：极易（1-2 天）✅ 立即可做

### 1️⃣ CORS 配置（30 分钟）

**难度**: ⭐☆☆☆☆  
**工作量**: 30 分钟  
**影响**: 前端调用 API 必需

**实现步骤**:
```bash
# 1. 安装包
pip install django-cors-headers

# 2. 修改 settings.py
```

**settings.py 修改**:
```python
INSTALLED_APPS = [
    # ...现有应用...
    'corsheaders',  # 添加这一行
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 添加在最前面
    'django.middleware.common.CommonMiddleware',
    # ...其他 middleware...
]

# 添加 CORS 配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # 本地前端开发
    "http://localhost:8080",      # 备用
    "http://localhost:5173",      # Vite 开发服务器
    "https://yourdomain.com",     # 生产域名
]

CORS_ALLOW_CREDENTIALS = True
```

**验证**:
```bash
python manage.py runserver
# 测试跨域请求应该成功
```

**完成标志**: ✅ 前端能从不同域名调用后端 API

---

### 2️⃣ API 文档自动生成（1-2 小时）

**难度**: ⭐☆☆☆☆  
**工作量**: 1-2 小时  
**影响**: 开发者能查看 API 文档

**实现步骤**:
```bash
# 1. 安装 Spectacular
pip install drf-spectacular

# 2. 修改 settings.py
```

**settings.py 修改**:
```python
INSTALLED_APPS = [
    # ...
    'drf_spectacular',  # 添加这一行
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Spectacular 配置
SPECTACULAR_SETTINGS = {
    'TITLE': '商场店铺智能运营管理系统 API',
    'DESCRIPTION': '完整的 API 文档',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}
```

**urls.py 修改**:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...现有 URL...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

**访问**: http://localhost:8000/api/docs/

**完成标志**: ✅ 自动生成的 Swagger UI 文档可访问

---

### 3️⃣ 基础日志配置（1 小时）

**难度**: ⭐☆☆☆☆  
**工作量**: 1 小时  
**影响**: 能在控制台看到详细日志

**settings.py 添加**:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

**使用示例**:
```python
import logging

logger = logging.getLogger(__name__)

class ContractService:
    @staticmethod
    def submit_for_review(contract_id):
        logger.info(f'提交合同审核: {contract_id}')
        try:
            contract = Contract.objects.get(id=contract_id)
            contract.status = 'PENDING_REVIEW'
            contract.save()
            logger.info(f'合同 {contract_id} 状态已更新')
        except Exception as e:
            logger.error(f'提交审核失败: {str(e)}')
            raise
```

**完成标志**: ✅ logs/django.log 文件生成，日志内容完整

---

### 4️⃣ 环境变量管理（1 小时）

**难度**: ⭐☆☆☆☆  
**工作量**: 1 小时  
**影响**: 安全性提升，便于环境切换

**实现步骤**:
```bash
# 1. 安装 python-decouple
pip install python-decouple
```

**创建 .env 文件**:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
SMS_PROVIDER=ALIYUN
ALIYUN_ACCESS_KEY=xxx
ALIYUN_SECRET_KEY=xxx
```

**修改 settings.py**:
```python
from decouple import config, Csv

DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
DATABASE_URL = config('DATABASE_URL', default='sqlite:///db.sqlite3')

# 数据库配置
if DATABASE_URL.startswith('sqlite'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DATABASE_URL.replace('sqlite:///', ''),
        }
    }
else:
    import dj_database_url
    DATABASES = {'default': dj_database_url.config()}
```

**.gitignore 添加**:
```
.env
.env.local
*.log
```

**完成标志**: ✅ 敏感信息不在代码中，可安全提交

---

### 5️⃣ 请求响应格式统一（2 小时）

**难度**: ⭐☆☆☆☆  
**工作量**: 2 小时  
**影响**: API 返回格式一致，便于前端开发

**创建 apps/core/response.py**:
```python
from rest_framework.response import Response
from rest_framework import status

class APIResponse:
    """统一 API 响应格式"""
    
    @staticmethod
    def success(data=None, message='操作成功', status_code=status.HTTP_200_OK):
        return Response({
            'code': 0,
            'message': message,
            'data': data,
        }, status=status_code)
    
    @staticmethod
    def error(message='操作失败', code=1, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            'code': code,
            'message': message,
            'data': None,
        }, status=status_code)
    
    @staticmethod
    def paginated(queryset, page_number=1, page_size=20):
        from django.core.paginator import Paginator
        
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)
        
        return Response({
            'code': 0,
            'message': '获取成功',
            'data': {
                'items': page.object_list,
                'total': paginator.count,
                'page': page_number,
                'page_size': page_size,
            }
        })
```

**使用示例**:
```python
from apps.core.response import APIResponse

class DeviceDataReceiveAPIView(APIView):
    def post(self, request):
        # ... 处理逻辑 ...
        return APIResponse.success(
            data={'record_id': 123},
            message='数据上传成功'
        )
```

**完成标志**: ✅ 所有 API 返回格式统一

---

## 🟨 第 2 级：简易（3-7 天）⭐ 周内完成

### 6️⃣ Sentry 错误追踪集成（1 天）

**难度**: ⭐⭐☆☆☆  
**工作量**: 1 天  
**影响**: 生产环境错误自动上报和追踪

**实现步骤**:
```bash
pip install sentry-sdk
```

**settings.py 修改**:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:  # 仅在生产环境启用
    sentry_sdk.init(
        dsn="https://your-sentry-dsn@sentry.io/project-id",
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% 采样
        environment='production',
        send_default_pii=False,
    )
```

**使用**:
```python
import sentry_sdk

# 自动捕获异常
try:
    problematic_code()
except Exception as e:
    sentry_sdk.capture_exception(e)

# 手动发送事件
sentry_sdk.capture_message('重要通知', level='warning')
```

**完成标志**: ✅ 错误自动上报到 Sentry

---

### 7️⃣ 健康检查端点（1 天）

**难度**: ⭐⭐☆☆☆  
**工作量**: 1 天  
**影响**: 负载均衡器和监控系统能检查服务健康

**创建 apps/core/views.py**:
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
import redis

class HealthCheckView(APIView):
    """健康检查端点"""
    
    def get(self, request):
        health_status = {
            'status': 'healthy',
            'checks': {}
        }
        
        # 1. 数据库检查
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['checks']['database'] = f'error: {str(e)}'
        
        # 2. Redis 检查
        try:
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
            health_status['checks']['redis'] = 'ok'
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['checks']['redis'] = f'error: {str(e)}'
        
        # 3. 磁盘空间检查
        import shutil
        total, used, free = shutil.disk_usage('/')
        health_status['checks']['disk_percent'] = (used / total) * 100
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return Response(health_status, status=status_code)
```

**urls.py**:
```python
from apps.core.views import HealthCheckView

urlpatterns = [
    path('health/', HealthCheckView.as_view()),
]
```

**完成标志**: ✅ curl http://localhost:8000/health/ 返回健康状态

---

### 8️⃣ 数据库备份脚本（2 天）

**难度**: ⭐⭐☆☆☆  
**工作量**: 2 天  
**影响**: 能自动备份数据库

**创建 scripts/backup_db.py**:
```python
import os
import subprocess
import shutil
from datetime import datetime

def backup_database():
    """备份 SQLite 数据库"""
    
    # 备份目录
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # 源文件
    db_file = 'db.sqlite3'
    
    # 备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{backup_dir}/db_backup_{timestamp}.sqlite3'
    
    # 复制文件
    shutil.copy2(db_file, backup_file)
    
    print(f'✅ 备份完成: {backup_file}')
    
    # 如果是 PostgreSQL，使用 pg_dump
    # os.system('pg_dump dbname > backup.sql')

if __name__ == '__main__':
    backup_database()
```

**创建 Cron 任务（Linux/Mac）**:
```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * cd /path/to/project && python scripts/backup_db.py
```

**Windows 任务计划**:
```batch
# 创建 backup_db.bat
@echo off
cd D:\Python经典程序合集\商场店铺智能运营管理系统设计与实现
python scripts/backup_db.py
```

**完成标志**: ✅ 备份目录自动生成备份文件

---

### 9️⃣ Django Security 配置加强（2 天）

**难度**: ⭐⭐☆☆☆  
**工作量**: 2 天  
**影响**: 安全性大幅提升

**settings.py 修改**:
```python
# 安全配置
if not DEBUG:
    # HTTPS 相关
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS
    SECURE_HSTS_SECONDS = 31536000  # 1 年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # 其他安全设置
    SECURE_CONTENT_SECURITY_POLICY = {
        'DEFAULT_SRC': ("'self'",),
        'SCRIPT_SRC': ("'self'",),
        'STYLE_SRC': ("'self'", "'unsafe-inline'"),
    }
    
    X_FRAME_OPTIONS = 'DENY'
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Session 安全
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 小时

# CSRF 配置
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'
```

**完成标志**: ✅ Django check 无安全警告

---

### 🔟 异常处理中间件（2 天）

**难度**: ⭐⭐☆☆☆  
**工作量**: 2 天  
**影响**: 统一的错误处理和响应

**创建 apps/core/exceptions.py**:
```python
from rest_framework import status
from rest_framework.exceptions import APIException

class BusinessException(APIException):
    """业务异常"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '业务异常'
    
    def __init__(self, detail=None, code=None):
        self.detail = detail or self.default_detail

class ContractException(BusinessException):
    """合同异常"""
    pass

class FinanceException(BusinessException):
    """财务异常"""
    pass

class NotificationException(BusinessException):
    """通知异常"""
    pass
```

**创建异常处理器**:
```python
# apps/core/exception_handlers.py
from rest_framework.views import exception_handler
from apps.core.exceptions import BusinessException

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is None and isinstance(exc, BusinessException):
        return Response(
            {
                'code': -1,
                'message': str(exc.detail),
                'data': None,
            },
            status=exc.status_code
        )
    
    return response
```

**settings.py 配置**:
```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.core.exception_handlers.custom_exception_handler',
}
```

**完成标志**: ✅ 所有异常都返回统一格式

---

## 🟧 第 3 级：中等（1-3 周）⭐⭐⭐ 本月目标

### 1️⃣1️⃣ JWT 认证实现（2-3 周）

**难度**: ⭐⭐⭐☆☆  
**工作量**: 2-3 周  
**影响**: 实现用户认证，API 安全

**安装依赖**:
```bash
pip install djangorestframework-simplejwt
```

**settings.py 配置**:
```python
from datetime import timedelta

INSTALLED_APPS = [
    # ...
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

**urls.py**:
```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

**使用示例**:
```python
from rest_framework.permissions import IsAuthenticated

class ContractListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
```

**测试**:
```bash
# 获取 token
curl -X POST http://localhost:8000/api/token/ \
  -d "username=admin&password=password"

# 使用 token 调用 API
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/contracts/
```

**完成标志**: ✅ API 需要有效 token 才能访问

---

### 1️⃣2️⃣ API 速率限制（1-2 周）

**难度**: ⭐⭐⭐☆☆  
**工作量**: 1-2 周  
**影响**: 防止 API 被滥用

**安装依赖**:
```bash
pip install djangorestframework
```

**settings.py 配置**:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',      # 匿名用户
        'user': '1000/hour',     # 认证用户
    }
}
```

**自定义限流**:
```python
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'burst': '10/second',
        'sustained': '100/hour',
    }
}
```

**应用到视图**:
```python
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

class DeviceDataView(APIView):
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
```

**完成标志**: ✅ 频繁请求会返回 429 Too Many Requests

---

### 1️⃣3️⃣ 基础权限系统（2-3 周）

**难度**: ⭐⭐⭐☆☆  
**工作量**: 2-3 周  
**影响**: 用户无法访问不属于他们的数据

**创建权限类**:
```python
# apps/core/permissions.py
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """只能访问自己的对象"""
    
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsContractReviewer(BasePermission):
    """只有审核人员能看合同"""
    
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='合同审核').exists()

class IsFinanceManager(BasePermission):
    """只有财务管理员能看财务数据"""
    
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='财务管理').exists()
```

**应用到视图**:
```python
class ContractDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsContractReviewer]
    queryset = Contract.objects.all()

class FinanceRecordListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsFinanceManager]
    queryset = FinanceRecord.objects.all()
    
    def get_queryset(self):
        # 财务人员只能看自己门店的账单
        return FinanceRecord.objects.filter(shop__manager=self.request.user)
```

**创建用户组**:
```python
from django.contrib.auth.models import Group

# 创建群组
contract_group, _ = Group.objects.get_or_create(name='合同审核')
finance_group, _ = Group.objects.get_or_create(name='财务管理')

# 添加用户到群组
user.groups.add(contract_group)
```

**完成标志**: ✅ 不同权限用户只能看到自己的数据

---

### 1️⃣4️⃣ 输入数据验证加强（1-2 周）

**难度**: ⭐⭐⭐☆☆  
**工作量**: 1-2 周  
**影响**: 防止非法数据进入系统

**创建序列化器**:
```python
from rest_framework import serializers
from apps.store.models import Contract

class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ['id', 'contract_number', 'rent_amount', 'status', ...]
        read_only_fields = ['id', 'created_at', 'reviewed_by', 'reviewed_at']
    
    def validate_contract_number(self, value):
        """合同号必须唯一"""
        if Contract.objects.filter(contract_number=value).exists():
            raise serializers.ValidationError("合同号已存在")
        return value
    
    def validate_rent_amount(self, value):
        """租金必须为正数"""
        if value <= 0:
            raise serializers.ValidationError("租金必须为正数")
        return value
    
    def validate(self, data):
        """交叉字段验证"""
        if data['contract_start_date'] >= data['contract_end_date']:
            raise serializers.ValidationError(
                "合同开始日期必须早于结束日期"
            )
        return data
```

**在视图中使用**:
```python
class ContractCreateView(generics.CreateAPIView):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    
    def perform_create(self, serializer):
        # 自动设置创建者
        serializer.save(created_by=self.request.user)
```

**完成标志**: ✅ 无效数据被正确拒绝

---

### 1️⃣5️⃣ 数据库查询优化（1-2 周）

**难度**: ⭐⭐⭐☆☆  
**工作量**: 1-2 周  
**影响**: API 响应速度提升 50%+

**优化示例**:
```python
# ❌ 错误：N+1 查询问题
def get_contracts(request):
    contracts = Contract.objects.all()
    for contract in contracts:
        print(contract.shop.name)  # 每个都会查一次数据库

# ✅ 正确：使用 select_related
def get_contracts(request):
    contracts = Contract.objects.select_related('shop', 'reviewed_by')
    for contract in contracts:
        print(contract.shop.name)  # 已加载在内存中

# ✅ 正确：使用 prefetch_related（对于多对多和反向关系）
def get_shops_with_contracts(request):
    shops = Shop.objects.prefetch_related('contracts_set')
    for shop in shops:
        for contract in shop.contracts_set.all():  # 已预加载
            pass
```

**使用数据库索引**:
```python
class Contract(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, db_index=True)  # 添加索引
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['shop', 'status']),
        ]
```

**使用 only() 和 defer()**:
```python
# 只获取需要的字段
contracts = Contract.objects.only('id', 'contract_number', 'status')

# 延迟加载大字段
contracts = Contract.objects.defer('description', 'attachment')
```

**完成标志**: ✅ API 响应时间从 500ms 降至 100ms

---

## 🟥 第 4 级：困难（2-4 周）⭐⭐⭐⭐ 下月目标

### 1️⃣6️⃣ Redis 缓存集成（2-3 周）

**难度**: ⭐⭐⭐⭐☆  
**工作量**: 2-3 周  
**影响**: 高频数据缓存，API 速度快 10 倍

**安装**:
```bash
pip install redis django-redis
```

**settings.py**:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_KWARGS': {'encoding': 'utf-8'},
            'POOL_KWARGS': {'max_connections': 50},
        }
    }
}
```

**使用示例**:
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# 方法 1: 手动缓存
@cache.cached_property
def get_shop_summary(shop_id):
    key = f'shop_summary_{shop_id}'
    data = cache.get(key)
    
    if data is None:
        data = {
            'total_contracts': Contract.objects.filter(shop_id=shop_id).count(),
            'total_revenue': FinanceRecord.objects.filter(shop_id=shop_id).aggregate(
                Sum('amount')
            )['amount__sum']
        }
        cache.set(key, data, 60 * 60)  # 缓存 1 小时
    
    return data

# 方法 2: 视图缓存
@cache_page(60 * 5)  # 缓存 5 分钟
def get_shops(request):
    return Response(ShopSerializer(Shop.objects.all(), many=True).data)

# 方法 3: 缓存失效
def update_contract(contract):
    contract.save()
    # 清除相关缓存
    cache.delete(f'shop_summary_{contract.shop_id}')
```

**完成标志**: ✅ Redis 连接正常，缓存命中率 > 80%

---

### 1️⃣7️⃣ 基础测试框架（2-3 周）

**难度**: ⭐⭐⭐⭐☆  
**工作量**: 2-3 周  
**影响**: 代码质量可验证，回归风险降低

**安装**:
```bash
pip install pytest pytest-django pytest-cov
```

**pytest.ini**:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
testpaths = apps
```

**示例测试**:
```python
# apps/store/tests/test_contract.py
import pytest
from django.test import TestCase
from apps.store.models import Contract, Shop
from apps.store.services import StoreService

@pytest.mark.django_db
class TestContractService:
    
    @pytest.fixture
    def shop(self):
        return Shop.objects.create(name='Test Shop')
    
    @pytest.fixture
    def contract(self, shop):
        return Contract.objects.create(
            shop=shop,
            contract_number='TEST001',
            rent_amount=5000,
            status=Contract.Status.DRAFT
        )
    
    def test_submit_for_review(self, contract):
        """测试提交审核"""
        StoreService.submit_for_review(contract.id)
        contract.refresh_from_db()
        assert contract.status == Contract.Status.PENDING_REVIEW
    
    def test_approve_contract(self, contract, admin_user):
        """测试批准合同"""
        contract.status = Contract.Status.PENDING_REVIEW
        contract.save()
        
        StoreService.approve_contract(
            contract.id,
            admin_user.id,
            'Approved'
        )
        
        contract.refresh_from_db()
        assert contract.status == Contract.Status.APPROVED
        assert contract.reviewed_by == admin_user
```

**运行测试**:
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest apps/store/tests/test_contract.py::TestContractService::test_submit_for_review

# 生成覆盖率报告
pytest --cov=apps --cov-report=html
```

**完成标志**: ✅ 测试覆盖率 > 60%，CI 流程通过

---

### 1️⃣8️⃣ 监控告警系统基础（2 周）

**难度**: ⭐⭐⭐⭐☆  
**工作量**: 2 周  
**影响**: 能及时发现和处理生产问题

**安装**:
```bash
pip install prometheus-client django-prometheus
```

**settings.py**:
```python
INSTALLED_APPS = [
    # ...
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusMiddleware',
    # ...其他 middleware...
    'django.middleware.common.CommonMiddleware',
]
```

**urls.py**:
```python
from django_prometheus import views as prometheus_views

urlpatterns = [
    path('metrics/', prometheus_views.metrics),
]
```

**自定义指标**:
```python
from prometheus_client import Counter, Histogram

# 计数器
contract_created = Counter(
    'contract_created_total',
    'Total contracts created'
)

# 直方图（用于时间测量）
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# 使用
contract_created.inc()

with request_duration.time():
    # 业务逻辑
    pass
```

**访问指标**: http://localhost:8000/metrics/

**完成标志**: ✅ Prometheus 能正确抓取指标

---

### 1️⃣9️⃣ Celery 任务监控（1-2 周）

**难度**: ⭐⭐⭐⭐☆  
**工作量**: 1-2 周  
**影响**: 能看到后台任务执行情况

**启动 Flower**:
```bash
pip install flower
celery -A config flower --port=5555
```

**访问**: http://localhost:5555

**配置持久化**:
```python
# config/celery.py
from celery import Celery

app = Celery('config')

app.conf.update(
    # ...现有配置...
    
    # Flower 配置
    flower_basic_auth=['user:password'],
    flower_persistent=True,
    flower_db='sqlite:///flower.db',
)
```

**任务监控**:
```python
from apps.finance.tasks import send_payment_reminder_task

# 查看任务状态
task = send_payment_reminder_task.delay(days_ahead=3)
print(task.id)
print(task.status)  # PENDING, STARTED, SUCCESS, FAILURE

# 在 Flower 界面查看所有任务
# 访问 http://localhost:5555
```

**完成标志**: ✅ Flower 界面能看到所有任务执行情况

---

### 2️⃣0️⃣ Docker 容器化（2-3 周）

**难度**: ⭐⭐⭐⭐☆  
**工作量**: 2-3 周  
**影响**: 一键部署，环境一致

**创建 Dockerfile**:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建非 root 用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 运行迁移并启动
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4"]

EXPOSE 8000
```

**创建 docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:password@db:5432/shop_management
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
  
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=shop_management
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  celery:
    build: .
    command: celery -A config worker -l info
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/shop_management
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

**运行**:
```bash
docker-compose up -d
docker-compose logs -f web
```

**完成标志**: ✅ docker-compose up 可正常启动完整环境

---

## 🟪 第 5 级：很困难（1-2 个月）⭐⭐⭐⭐⭐ 3 月目标

### 2️⃣1️⃣ CI/CD 流水线（3-4 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 3-4 周  
**影响**: 自动化测试和部署，质量保证

**GitHub Actions 示例** (.github/workflows/test.yml):
```yaml
name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.13
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-django pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=apps --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

**自动部署** (.github/workflows/deploy.yml):
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to server
      run: |
        mkdir -p ~/.ssh
        echo "${{ secrets.DEPLOY_KEY }}" > ~/.ssh/deploy_key
        chmod 600 ~/.ssh/deploy_key
        ssh -i ~/.ssh/deploy_key user@server.com 'cd /app && git pull && docker-compose up -d'
```

**完成标志**: ✅ 提交代码自动运行测试，主分支自动部署

---

### 2️⃣2️⃣ 前端框架搭建（3-4 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 3-4 周  
**影响**: 能使用前端应用

**搭建 Vue.js 项目**:
```bash
npm create vite@latest shop-management -- --template vue
cd shop-management
npm install
npm install axios element-plus
```

**主要页面结构**:
```
src/
├── pages/
│   ├── LoginPage.vue         # 登录
│   ├── ContractListPage.vue  # 合同列表
│   ├── FinancePage.vue       # 财务管理
│   ├── DashboardPage.vue     # 仪表板
│   └── NotificationPage.vue  # 通知中心
├── components/
│   ├── Header.vue
│   ├── Sidebar.vue
│   └── DataTable.vue
├── services/
│   └── api.js               # API 调用封装
├── stores/
│   └── useStore.js          # 状态管理
└── router.js
```

**API 调用封装**:
```javascript
// src/services/api.js
import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000/api',
})

API.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const contractAPI = {
  list: () => API.get('/contracts/'),
  create: (data) => API.post('/contracts/', data),
  update: (id, data) => API.patch(`/contracts/${id}/`, data),
  delete: (id) => API.delete(`/contracts/${id}/`),
}

export const authAPI = {
  login: (username, password) => API.post('/token/', { username, password }),
  refresh: (refresh) => API.post('/token/refresh/', { refresh }),
}
```

**完成标志**: ✅ 前端能登录并显示数据列表

---

### 2️⃣3️⃣ 微服务化重构（6-8 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 6-8 周  
**影响**: 支持高并发，易于扩展

**服务拆分**:
```
原架构:
┌─────────────────────────────────────────┐
│  Django Monolith                        │
│  ├─ Store Service                      │
│  ├─ Finance Service                    │
│  ├─ Notification Service               │
│  ├─ Operations Service                 │
│  └─ Shared Database                    │
└─────────────────────────────────────────┘

微服务架构:
┌──────────────────────────────────────────────────────────┐
│  API Gateway (Kong/Nginx)                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ Store MS    │  │ Finance MS  │  │ Notify MS    │   │
│  │ :8001       │  │ :8002       │  │ :8003        │   │
│  └─────────────┘  └─────────────┘  └──────────────┘   │
│         │               │                   │          │
│  ┌──────────┐    ┌──────────┐      ┌──────────┐      │
│  │ DB Store │    │ DB Fin   │      │ DB Notify│      │
│  └──────────┘    └──────────┘      └──────────┘      │
│         │               │                   │          │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Message Queue (RabbitMQ/Kafka)                  │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**完成标志**: ✅ 各服务独立部署，可水平扩展

---

## 🟫 第 6 级：极困难（2-6 个月）⭐⭐⭐⭐⭐ 后续迭代

### 2️⃣4️⃣ Kubernetes 容器编排（3-4 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 3-4 周  
**影响**: 自动化运维，高可用部署

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shop-management
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shop-management
  template:
    metadata:
      labels:
        app: shop-management
    spec:
      containers:
      - name: shop-management
        image: shop-management:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**完成标志**: ✅ kubectl apply 能正常部署应用

---

### 2️⃣5️⃣ 完整的前端应用（6-8 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 6-8 周  
**影响**: 完整的用户界面

**需要实现的页面**:
- 登录/注册 (1 周)
- 店铺管理 (1.5 周)
- 合同管理 (1.5 周)
- 财务查询 (1 周)
- 数据分析 (1.5 周)
- 通知中心 (0.5 周)
- 个人设置 (0.5 周)

**完成标志**: ✅ 完整前端应用可用，无重大 Bug

---

### 2️⃣6️⃣ 性能优化和调优（4-6 周）

**难度**: ⭐⭐⭐⭐⭐  
**工作量**: 4-6 周  
**影响**: API 响应时间 < 100ms

**包括内容**:
- 数据库查询优化
- 缓存策略优化
- CDN 配置
- 前端资源优化
- 性能基准测试
- 持续监控和优化

**完成标志**: ✅ P95 响应时间 < 200ms，QPS > 1000

---

## 📊 完整优先级排序表

| 优先级 | 难度 | 工作量 | 功能 | 预计完成 |
|--------|------|--------|------|---------|
| P0 | ⭐ | 1 天 | CORS 配置 | 本周 |
| P0 | ⭐ | 1-2 小时 | API 文档 | 本周 |
| P0 | ⭐ | 1 小时 | 日志配置 | 本周 |
| P0 | ⭐ | 1 小时 | 环境变量 | 本周 |
| P0 | ⭐ | 2 小时 | 响应格式统一 | 本周 |
| P1 | ⭐⭐ | 1 天 | Sentry 集成 | 本周 |
| P1 | ⭐⭐ | 1 天 | 健康检查 | 本周 |
| P1 | ⭐⭐ | 2 天 | 备份脚本 | 本周末 |
| P1 | ⭐⭐ | 2 天 | 安全加强 | 本周末 |
| P1 | ⭐⭐ | 2 天 | 异常处理 | 本周末 |
| P2 | ⭐⭐⭐ | 2-3 周 | JWT 认证 | 本月 |
| P2 | ⭐⭐⭐ | 1-2 周 | 速率限制 | 本月 |
| P2 | ⭐⭐⭐ | 2-3 周 | 权限系统 | 本月 |
| P2 | ⭐⭐⭐ | 1-2 周 | 数据验证 | 本月 |
| P2 | ⭐⭐⭐ | 1-2 周 | 查询优化 | 本月 |
| P3 | ⭐⭐⭐⭐ | 2-3 周 | Redis 缓存 | 下月 |
| P3 | ⭐⭐⭐⭐ | 2-3 周 | 测试框架 | 下月 |
| P3 | ⭐⭐⭐⭐ | 2 周 | 监控告警 | 下月 |
| P3 | ⭐⭐⭐⭐ | 1-2 周 | Celery 监控 | 下月 |
| P3 | ⭐⭐⭐⭐ | 2-3 周 | Docker 化 | 下月 |
| P4 | ⭐⭐⭐⭐⭐ | 3-4 周 | CI/CD | 3 月 |
| P4 | ⭐⭐⭐⭐⭐ | 3-4 周 | 前端框架 | 3 月 |
| P5 | ⭐⭐⭐⭐⭐ | 6-8 周 | 微服务化 | 6 月 |
| P5 | ⭐⭐⭐⭐⭐ | 3-4 周 | Kubernetes | 6 月 |
| P5 | ⭐⭐⭐⭐⭐ | 6-8 周 | 前端应用 | 6 月 |

---

## 📅 建议的实施计划

### ✅ 第 1 周（本周）- 快速赢
```
□ CORS 配置 (30 分钟)
□ API 文档 (1-2 小时)  
□ 日志配置 (1 小时)
□ 环境变量管理 (1 小时)
□ 响应格式统一 (2 小时)

预计工作量: 1 人，1 周
成果: 基础开发体验大幅提升
```

### 📅 第 2-3 周 - 安全加固
```
□ Sentry 集成 (1 天)
□ 健康检查 (1 天)
□ 备份脚本 (2 天)
□ 安全加强 (2 天)
□ 异常处理 (2 天)

预计工作量: 1 人，2.5 周
成果: 生产环境基本可用
```

### 📅 第 4-6 周 - 用户管理
```
□ JWT 认证 (2-3 周)
□ 权限系统 (2-3 周)  
□ 速率限制 (1-2 周)

预计工作量: 2 人，3 周
成果: 多用户系统可用
```

### 📅 第 7-10 周 - 性能优化
```
□ 查询优化 (1-2 周)
□ Redis 缓存 (2-3 周)
□ 监控告警 (2 周)
□ 测试框架 (2-3 周)

预计工作量: 2 人，4 周
成果: 系统性能和稳定性大幅提升
```

### 📅 第 11-16 周 - 运维自动化
```
□ Docker 化 (2-3 周)
□ CI/CD 流水线 (3-4 周)
□ Celery 监控 (1-2 周)

预计工作量: 2 人，3-4 周
成果: 自动化部署，运维效率提升
```

### 📅 第 17-22 周 - 前端开发
```
□ 前端框架搭建 (3-4 周)
□ 核心页面开发 (4-6 周)

预计工作量: 2-3 人，6 周
成果: 完整的用户界面
```

### 📅 第 23+ 周 - 长期演进
```
□ 微服务化重构 (6-8 周)
□ Kubernetes 部署 (3-4 周)
□ 持续优化和扩展

预计工作量: 3+ 人，持续
成果: 企业级系统架构
```

---

## 🎯 总结

**按难度排序的完整路线图**:

1️⃣ **这周快速完成** (5 个任务，5 小时)
2️⃣ **本月安全加固** (5 个任务，2-3 周)
3️⃣ **下月用户管理** (3 个任务，3 周)
4️⃣ **6 周后性能优化** (4 个任务，4 周)
5️⃣ **11 周后运维自动化** (3 个任务，3-4 周)
6️⃣ **17 周后前端开发** (2 个任务，6 周)
7️⃣ **半年后微服务化** (持续演进)

**总投入**: 3-5 人，6 个月，达到工业级水平

这样安排既能快速看到成果，又能循序渐进地提升系统质量！🚀
