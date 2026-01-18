# Level 4 Task 4 - Django 集成指南

## 📋 集成概述

本指南详细说明如何将国际化/本地化(i18n/l10n)系统集成到现有的 Django 商场管理系统中。

---

## 🚀 集成步骤

### 步骤 1: 文件位置确认

确认以下文件已在正确的位置：

```
apps/core/
├── __init__.py
├── i18n_config.py              # 新增 - 配置
├── i18n_manager.py             # 新增 - 核心管理器
├── i18n_views.py               # 新增 - API 视图
├── i18n_urls.py                # 新增 - URL 路由
├── models.py
├── views.py
├── urls.py
├── admin.py
├── tests/
│   ├── __init__.py
│   ├── test_level4_task4.py    # 新增 - 测试文件
│   └── ...
├── management/
│   └── commands/
│       ├── __init__.py
│       └── i18n_manage.py      # 新增 - CLI 管理命令
└── ...
```

### 步骤 2: 更新 Django 配置

#### 2.1 编辑 `config/settings.py`

在 `INSTALLED_APPS` 中确保包含：

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # REST Framework
    'rest_framework',
    
    # 自定义应用
    'apps.core',
    'apps.shop',
    'apps.finance',
    'apps.report',
    'apps.communication',
    
    # ... 其他应用
]
```

添加国际化配置：

```python
# ==================== 国际化配置 ====================

# 启用国际化支持
USE_I18N = True
USE_L10N = True

# 默认语言
LANGUAGE_CODE = 'zh-cn'

# 默认时区
TIME_ZONE = 'Asia/Shanghai'

# 支持的语言列表
LANGUAGES = [
    ('zh-cn', '中文 (简体)'),
    ('zh-hk', '中文 (繁体)'),
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'Français'),
    ('de', 'Deutsch'),
    ('ja', '日本語'),
    ('ko', '한국어'),
    ('ru', 'Русский'),
    ('pt', 'Português'),
    ('ar', 'العربية'),
    ('hi', 'हिन्दी'),
]

# 支持的时区列表
TIMEZONES = [
    'Asia/Shanghai',
    'America/New_York',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Asia/Tokyo',
    'Asia/Seoul',
    'Asia/Dubai',
    'Australia/Sydney',
]

# REST Framework 配置
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# i18n 缓存配置 (可选)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'i18n-cache',
        'TIMEOUT': 3600,
        'OPTIONS': {
            'MAX_ENTRIES': 10000
        }
    }
}
```

#### 2.2 编辑 `config/urls.py`

在主 URL 配置中添加 i18n 路由：

```python
# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 管理界面
    path('admin/', admin.site.urls),
    
    # i18n API 路由 (新增)
    path('api/i18n/', include('apps.core.i18n_urls')),
    
    # 其他 API 路由
    path('api/shop/', include('apps.shop.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/report/', include('apps.report.urls')),
    path('api/communication/', include('apps.communication.urls')),
    
    # 其他路由
    path('api/', include('apps.core.urls')),
]

# 静态文件和媒体文件配置
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### 步骤 3: 运行迁移 (如需要)

```bash
# 运行所有迁移
python manage.py migrate

# 创建超级用户 (如需要)
python manage.py createsuperuser
```

### 步骤 4: 验证安装

#### 4.1 运行测试

```bash
# 运行所有 i18n 测试
python manage.py test apps.core.tests.test_level4_task4

# 显示详细输出
python manage.py test apps.core.tests.test_level4_task4 -v 2

# 运行特定测试类
python manage.py test apps.core.tests.test_level4_task4.I18nManagerTests
```

**预期结果**: 所有 48 个测试应该通过

```
Ran 48 tests in 0.150s

OK
```

#### 4.2 启动开发服务器

```bash
# 启动 Django 开发服务器
python manage.py runserver

# 或指定端口
python manage.py runserver 0.0.0.0:8000
```

#### 4.3 测试 API 端点

在浏览器或使用 curl 测试以下端点：

```bash
# 获取语言列表
curl http://localhost:8000/api/i18n/languages/

# 获取货币列表
curl http://localhost:8000/api/i18n/currencies/

# 获取时区列表
curl http://localhost:8000/api/i18n/timezones/

# 翻译示例
curl -X POST http://localhost:8000/api/i18n/translate/ \
  -H "Content-Type: application/json" \
  -d '{"key": "hello", "language": "en"}'

# 货币转换示例
curl -X POST http://localhost:8000/api/i18n/convert-currency/ \
  -H "Content-Type: application/json" \
  -d '{"amount": "100", "from_currency": "CNY", "to_currency": "USD"}'
```

### 步骤 5: 测试 CLI 命令

```bash
# 列出所有支持的语言
python manage.py i18n_manage --list-languages

# 列出所有支持的货币
python manage.py i18n_manage --list-currencies

# 列出所有支持的时区
python manage.py i18n_manage --list-timezones

# 翻译示例
python manage.py i18n_manage --translate "hello" --language "en"

# 货币转换示例
python manage.py i18n_manage --convert-currency 100 \
  --from-currency CNY --to-currency USD

# 系统测试
python manage.py i18n_manage --test
```

---

## 🔧 高级集成

### 1. 在 Django 模型中使用 i18n

```python
# apps/shop/models.py

from django.db import models
from apps.core.i18n_manager import I18nFactory
from decimal import Decimal

class Product(models.Model):
    """产品模型"""
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def get_localized_name(self, language='zh-cn'):
        """获取本地化名称"""
        manager = I18nFactory.get_manager(language=language)
        return f"{self.name} ({manager.get_language_info()['name']})"
    
    def get_price_in_currency(self, target_currency='USD', language='en'):
        """获取指定货币的价格"""
        manager = I18nFactory.get_manager(language=language, currency=target_currency)
        
        # 从 CNY 转换为目标货币
        converted = manager.convert_currency(
            Decimal(str(self.price)),
            'CNY',
            target_currency
        )
        
        # 格式化
        return manager.format_currency(converted, target_currency)
```

### 2. 在 Django 视图中使用 i18n

```python
# apps/shop/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.i18n_manager import I18nFactory
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    """产品 ViewSet"""
    
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    @action(detail=True, methods=['get'])
    def localized_details(self, request, pk=None):
        """获取本地化的产品详情"""
        
        product = self.get_object()
        language = request.query_params.get('language', 'zh-cn')
        currency = request.query_params.get('currency', 'CNY')
        
        # 获取 i18n 管理器
        manager = I18nFactory.get_manager(language=language, currency=currency)
        
        # 构建响应
        return Response({
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'language': language,
            'currency': currency,
            'original_price': str(product.price),
            'localized_price': product.get_price_in_currency(currency, language),
            'language_info': manager.get_language_info(),
        })
    
    @action(detail=False, methods=['post'])
    def bulk_localize(self, request):
        """批量本地化产品"""
        
        language = request.data.get('language', 'zh-cn')
        currency = request.data.get('currency', 'CNY')
        
        manager = I18nFactory.get_manager(language=language, currency=currency)
        
        products = self.queryset[:10]  # 获取前 10 个产品
        
        localized_products = []
        for product in products:
            localized_products.append({
                'id': product.id,
                'name': product.name,
                'localized_price': product.get_price_in_currency(currency, language),
            })
        
        return Response({
            'language': language,
            'currency': currency,
            'products': localized_products,
            'count': len(localized_products),
        })
```

### 3. 在 Django 模板中使用 i18n (可选)

```html
<!-- templates/shop/product_detail.html -->

{% load static %}

<div class="product-details">
    <h1>{{ product.name }}</h1>
    <p>{{ product.description }}</p>
    
    <!-- 显示不同货币的价格 -->
    <div class="prices">
        <h3>{{ translated_strings.price }}</h3>
        
        {% for currency in currencies %}
            <div class="price-item">
                <span class="currency">{{ currency }}</span>
                <span class="amount">{{ product|get_price_in_currency:currency }}</span>
            </div>
        {% endfor %}
    </div>
    
    <!-- 时区信息 -->
    <div class="timezone-info">
        <p>{{ user_timezone }}</p>
        <p>{{ user_language }}</p>
    </div>
</div>
```

### 4. 创建自定义中间件 (可选)

```python
# apps/core/middleware.py

from django.utils.translation import activate, get_language
from apps.core.i18n_manager import I18nFactory

class I18nMiddleware:
    """国际化中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 从请求中获取语言参数
        language = request.GET.get('language') or \
                  request.POST.get('language') or \
                  get_language()
        
        # 激活 Django 的语言
        activate(language)
        
        # 创建 i18n 管理器并附加到请求
        timezone_str = request.GET.get('timezone', 'Asia/Shanghai')
        currency = request.GET.get('currency', 'CNY')
        
        request.i18n_manager = I18nFactory.get_manager(
            language=language,
            currency=currency,
            timezone_str=timezone_str
        )
        
        response = self.get_response(request)
        return response
```

在 settings.py 中添加中间件：

```python
MIDDLEWARE = [
    # ... 其他中间件 ...
    'apps.core.middleware.I18nMiddleware',
]
```

### 5. 创建自定义序列化器字段 (可选)

```python
# apps/core/serializers.py

from rest_framework import serializers
from apps.core.i18n_manager import I18nFactory
from decimal import Decimal

class LocalizedCurrencyField(serializers.Field):
    """本地化货币字段"""
    
    def __init__(self, currency='CNY', language='en', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currency = currency
        self.language = language
    
    def to_representation(self, value):
        """将值转换为本地化货币格式"""
        manager = I18nFactory.get_manager(
            language=self.language,
            currency=self.currency
        )
        return manager.format_currency(Decimal(str(value)), self.currency)
    
    def to_internal_value(self, data):
        """将输入转换为十进制值"""
        return Decimal(data)


class LocalizedDateField(serializers.Field):
    """本地化日期字段"""
    
    def __init__(self, language='en', format_type='date', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        self.format_type = format_type
    
    def to_representation(self, value):
        """将日期转换为本地化格式"""
        manager = I18nFactory.get_manager(language=self.language)
        return manager.format_date(value, self.format_type)
    
    def to_internal_value(self, data):
        """将输入转换为日期对象"""
        from datetime import datetime
        return datetime.fromisoformat(data)
```

---

## 📊 集成检查清单

### 配置检查

- [ ] 更新了 `config/settings.py`
  - [ ] 添加了 `rest_framework` 到 INSTALLED_APPS
  - [ ] 添加了国际化配置
  - [ ] 配置了 REST Framework

- [ ] 更新了 `config/urls.py`
  - [ ] 添加了 i18n URL 路由
  - [ ] 路由路径正确

### 文件检查

- [ ] `apps/core/i18n_config.py` 存在
- [ ] `apps/core/i18n_manager.py` 存在
- [ ] `apps/core/i18n_views.py` 存在
- [ ] `apps/core/i18n_urls.py` 存在
- [ ] `apps/core/management/commands/i18n_manage.py` 存在
- [ ] `apps/core/tests/test_level4_task4.py` 存在

### 功能检查

- [ ] 运行了所有测试 (48 个测试通过)
- [ ] 测试了 API 端点
- [ ] 测试了 CLI 命令
- [ ] 验证了翻译功能
- [ ] 验证了货币转换功能
- [ ] 验证了时区转换功能
- [ ] 验证了日期格式化
- [ ] 验证了数字格式化

### 性能检查

- [ ] 翻译响应时间 < 1ms
- [ ] 货币转换响应时间 < 1ms
- [ ] 时区转换响应时间 < 2ms
- [ ] 100 次操作 < 100ms

### 文档检查

- [ ] 阅读了快速开始指南
- [ ] 阅读了完成报告
- [ ] 理解了 API 端点
- [ ] 理解了 CLI 命令
- [ ] 查看了代码注释

---

## 🐛 故障排除

### 问题 1: 导入错误

**错误信息**: `ModuleNotFoundError: No module named 'apps.core.i18n_manager'`

**解决方案**:
1. 检查文件是否在正确的位置
2. 确保 `apps/core/__init__.py` 存在
3. 运行 `python manage.py migrate`

### 问题 2: API 404 错误

**错误信息**: `404 Not Found` 访问 `/api/i18n/languages/`

**解决方案**:
1. 检查 `config/urls.py` 是否包含了 i18n 路由
2. 确保拼写正确: `path('api/i18n/', include('apps.core.i18n_urls'))`
3. 重启 Django 开发服务器

### 问题 3: 测试失败

**错误信息**: `ImportError` 在运行测试时

**解决方案**:
1. 运行 `pip install -r requirements.txt`
2. 确保 `pytz` 已安装
3. 检查 Django 版本 (应该是 3.2+)

### 问题 4: 缓存问题

**症状**: 翻译没有更新

**解决方案**:
1. 清除缓存: `python manage.py shell`
   ```python
   from django.core.cache import cache
   cache.clear()
   ```
2. 或在 CLI 中: `python manage.py i18n_manage --clear-cache` (如果支持)

---

## 📚 更多资源

- [Django i18n 文档](https://docs.djangoproject.com/en/stable/topics/i18n/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)
- [pytz 文档](http://pytz.sourceforge.net/)
- [LEVEL_4_TASK_4_QUICK_START.md](LEVEL_4_TASK_4_QUICK_START.md)
- [LEVEL_4_TASK_4_COMPLETION_REPORT.md](LEVEL_4_TASK_4_COMPLETION_REPORT.md)

---

## ✅ 完成确认

集成完成后，您应该能够：

✓ 访问 10 个 REST API 端点
✓ 使用 13 个 CLI 管理命令
✓ 支持 12+ 语言
✓ 支持 10+ 货币
✓ 支持 10+ 时区
✓ 所有 48 个测试通过
✓ 系统性能达标

**祝贺! 您已成功集成了国际化/本地化系统! 🎉**
