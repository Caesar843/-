# Level 3 Task 1: 缓存策略与优化实现指南

## 📋 任务概述

本任务实现了企业级缓存系统，包括：

1. **多层缓存架构** - 本地内存 + Redis 分布式缓存
2. **缓存防护机制** - 穿透、雪崩、击穿防护
3. **性能监控系统** - 实时统计、健康检查
4. **管理工具** - CLI 命令、API 监控、装饰器
5. **最佳实践** - TTL 优化、缓存预热、失效策略

---

## 📁 新增文件结构

```
apps/core/
├── cache_manager.py          ✅ 缓存管理器（430 行）
├── cache_config.py           ✅ 缓存配置（350 行）
├── decorators.py             ✅ 缓存装饰器（400 行）
├── management/
│   └── commands/
│       └── cache_manage.py   ✅ 管理命令（200 行）
├── views.py                  ✅ 监控视图（已更新）
└── urls.py                   ✅ 缓存路由（已更新）
```

---

## 🚀 快速启动

### 1. 查看缓存状态

```bash
# 列出所有缓存键
python manage.py cache_manage --list

# 显示缓存统计
python manage.py cache_manage --stats

# 检查缓存健康
python manage.py cache_manage --health-check
```

### 2. 管理缓存

```bash
# 清空所有缓存
python manage.py cache_manage --clear

# 清除匹配模式的缓存
python manage.py cache_manage --clear-pattern "user:*"

# 预热缓存
python manage.py cache_manage --warmup
```

### 3. API 接口

```bash
# 获取缓存统计（需认证和管理员权限）
GET /api/core/cache/stats/

# 检查缓存健康
GET /api/core/cache/health/

# 清除缓存
POST /api/core/cache/clear/
Body: {"pattern": "user:*"} 或 {"all": true}

# 预热缓存
POST /api/core/cache/warmup/
Body: {"targets": ["products", "categories"]}
```

---

## 💻 代码集成指南

### A. 在 settings.py 中配置缓存

#### 开发环境（本地内存缓存）

```python
# config/settings.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}
```

#### 生产环境（Redis 缓存）

```python
# 首先安装：pip install django-redis

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'TIMEOUT': 86400,  # 24 小时
    }
}

# 配置 session 使用 Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
```

### B. 在视图中使用缓存装饰器

#### 方法一：使用 @cache_view 装饰器

```python
from rest_framework import viewsets
from apps.core.decorators import cache_view, invalidate_cache

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    @cache_view(timeout=600, key_prefix='product_list')
    def list(self, request, *args, **kwargs):
        """列表视图 - 缓存 10 分钟"""
        return super().list(request, *args, **kwargs)
    
    @cache_view(timeout=300, key_prefix='product_detail')
    def retrieve(self, request, *args, **kwargs):
        """详情视图 - 缓存 5 分钟"""
        return super().retrieve(request, *args, **kwargs)
    
    @invalidate_cache(pattern='cache_view:product_*')
    def update(self, request, *args, **kwargs):
        """更新时清除相关缓存"""
        return super().update(request, *args, **kwargs)
    
    @invalidate_cache(pattern='cache_view:product_*')
    def destroy(self, request, *args, **kwargs):
        """删除时清除相关缓存"""
        return super().destroy(request, *args, **kwargs)
```

#### 方法二：使用 CacheManager 手动管理

```python
from apps.core.cache_manager import CacheManager, cached

class OrderService:
    def __init__(self):
        self.cache_manager = CacheManager()
    
    @cached(timeout=600, key_prefix='user_orders')
    def get_user_orders(self, user_id):
        """自动缓存用户订单"""
        return Order.objects.filter(user_id=user_id)
    
    def create_order(self, user_id, data):
        """创建订单后清除缓存"""
        order = Order.objects.create(**data)
        # 清除该用户的缓存
        self.cache_manager.clear_pattern(f'user_orders:*{user_id}*')
        return order
```

### C. 在模型中使用缓存

```python
from django.db import models
from apps.core.cache_manager import CacheManager

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        app_label = 'store'
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 保存时清除相关缓存
        cache_manager = CacheManager()
        cache_manager.clear_pattern(f'product:*')
    
    @classmethod
    def get_hot_products(cls, limit=50):
        """获取热销产品（带缓存）"""
        cache_manager = CacheManager()
        cache_key = f'products:hot:{limit}'
        
        # 尝试从缓存获取
        products = cache_manager.get(cache_key)
        if products is None:
            # 从数据库查询
            products = cls.objects.filter(
                sales__gte=100
            ).order_by('-sales')[:limit]
            # 缓存 1 小时
            cache_manager.set(cache_key, products, timeout=3600)
        
        return products
```

---

## 🔒 缓存防护机制详解

### 1. 缓存穿透防护（Cache Penetration）

**问题**：客户端请求不存在的数据 → 数据库查询 → 数据库压力大

**解决方案**：使用分布式锁

```python
def get_user(user_id):
    """获取用户 - 防止缓存穿透"""
    cache_manager = CacheManager()
    
    # 使用 get_or_set 自动处理分布式锁
    user = cache_manager.get_or_set(
        key=f'user:{user_id}',
        callable_func=lambda: User.objects.get(id=user_id),
        timeout=3600
    )
    return user
```

**原理**：
- 多个线程同时缺失时，只有一个获得锁，其他等待
- 获得锁的线程查询数据库并缓存
- 其他线程从缓存读取结果

### 2. 缓存雪崩防护（Cache Avalanche）

**问题**：大量缓存同时过期 → 数据库请求激增

**解决方案**：随机 TTL

```python
# cache_manager.py 中自动实现
cache.set(key, value, timeout + random_offset)

# 随机偏移：±20% 的超时时间
# 例：timeout=300 → 实际 240-360 秒过期
```

### 3. 缓存击穿防护（Cache Breakdown）

**问题**：热点数据过期 → 并发请求打穿数据库

**解决方案**：缓存预热 + 主动更新

```python
from apps.core.cache_manager import CacheWarmup

# 应用启动时预热
CacheWarmup.warmup_popular_products(limit=50)

# 或定期更新
class WarmupTask(Task):
    def run(self):
        CacheWarmup.warmup_popular_products(limit=50)

# 使用 Celery 定期执行
app.conf.beat_schedule = {
    'warmup-cache-every-hour': {
        'task': 'apps.core.tasks.warmup_cache',
        'schedule': crontab(minute=0),  # 每小时
    },
}
```

---

## 📊 性能监控

### 查看缓存统计

```bash
# 方式 1：命令行
python manage.py cache_manage --stats

# 方式 2：API
curl http://localhost:8000/api/core/cache/stats/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 返回示例：
{
    "hits": 1500,
    "misses": 300,
    "hit_rate": 0.833,
    "errors": 2,
    "avg_time_ms": 1.5,
    "total_operations": 1802
}
```

### 关键指标解释

| 指标 | 含义 | 目标值 |
|------|------|--------|
| hit_rate | 缓存命中率 | > 80% |
| avg_time_ms | 平均响应时间 | < 5ms |
| errors | 缓存错误数 | = 0 |
| total_operations | 总操作数 | 越多越好 |

---

## 🛠️ 高级用法

### 1. 条件缓存

```python
from apps.core.decorators import cache_if

def should_cache(request):
    """仅为非认证用户缓存"""
    return not request.user.is_authenticated

@cache_if(should_cache)
def list_products(request):
    return ProductSerializer(Product.objects.all(), many=True).data
```

### 2. 自定义缓存键

```python
from apps.core.cache_manager import CacheManager

manager = CacheManager()

# 使用自定义键前缀
user_orders = manager.get_or_set(
    key='orders:user_123:2024',
    callable_func=lambda: Order.objects.filter(
        user_id=123, 
        created_year=2024
    ),
    timeout=3600
)
```

### 3. 缓存预热

```python
from apps.core.cache_manager import CacheWarmup

# 预热热销产品
CacheWarmup.warmup_popular_products(limit=100)

# 预热用户排名
class UserRanking(models.Model):
    @classmethod
    def warmup_rankings(cls):
        """预热用户排名缓存"""
        cache_manager = CacheManager()
        
        rankings = cls.objects.all().order_by('-points')[:50]
        cache_manager.set(
            'rankings:top_50',
            rankings,
            timeout=3600
        )
```

---

## ⚙️ 故障排除

### 1. Redis 连接失败

```bash
# 检查 Redis 状态
redis-cli ping
# 输出：PONG

# 检查缓存健康
python manage.py cache_manage --health-check
```

### 2. 缓存未生效

```python
# 确保已在 settings.py 配置 CACHES
# 检查缓存后端
from django.core.cache import cache
cache.set('test', 'value', 10)
print(cache.get('test'))  # 应输出 'value'
```

### 3. 缓存键冲突

```python
# 使用更具体的前缀
cache_manager.set(f'user:{user_id}:profile', data, 3600)
cache_manager.set(f'user:{user_id}:orders', data, 3600)

# 清除时指定模式
cache_manager.clear_pattern(f'user:{user_id}:*')
```

---

## 📈 性能基准

### 缓存命中时间（毫秒）

| 后端 | 命中 | 缺失 | 平均 |
|------|------|------|------|
| 本地内存 | 0.1-0.5 | 10-20 | 1-2 |
| Redis | 1-2 | 15-30 | 2-3 |
| 数据库 | - | 50-200 | 100-150 |

### 缓存模式 vs 无缓存

```
无缓存：100 req/s
缓存 50% 命中：500 req/s
缓存 80% 命中：1000 req/s
缓存 95% 命中：2000 req/s
```

---

## ✅ 验证清单

- [ ] 已在 settings.py 配置 CACHES
- [ ] 已测试 `python manage.py cache_manage --health-check`
- [ ] 已测试缓存命令行工具
- [ ] 已测试 API 监控端点
- [ ] 已在视图中添加 @cache_view 装饰器
- [ ] 已验证缓存统计数据
- [ ] 已配置 Redis（生产环境）
- [ ] 已设置缓存预热任务

---

## 📚 相关文件

- [cache_manager.py](../apps/core/cache_manager.py) - 核心缓存管理
- [cache_config.py](../apps/core/cache_config.py) - 配置和优化
- [decorators.py](../apps/core/decorators.py) - 装饰器工具
- [管理命令](../apps/core/management/commands/cache_manage.py) - CLI 工具

---

## 🎯 下一步任务

- [ ] Task 2: API 限流与节流
- [ ] Task 3: 异步任务队列（Celery）
- [ ] Task 4: 全文搜索集成
- [ ] Task 5: 国际化（i18n/l10n）

---

**状态**：✅ Task 1 - 40% 完成（需要集成测试）  
**完成日期**：2024  
**维护者**：系统管理员
