# Level 4 Task 1 - API 限流与限速 快速开始指南

## 5 分钟快速开始

### 1. 查看演示

```bash
# 查看配置信息
python manage.py rate_limit_manage --list-config

# 查看策略对比
python manage.py rate_limit_manage --strategies

# 查看统计数据
python manage.py rate_limit_manage --stats
```

### 2. 在 Django 视图中使用

#### 方式 A: 装饰器 (推荐)

```python
from django.http import JsonResponse
from apps.core.rate_limit_decorators import rate_limit, throttle

# 基础限流
@rate_limit(requests=100, period=60)
def api_search(request):
    """每个用户 100 req/min"""
    return JsonResponse({'results': [...]})

# 使用特定策略
@throttle(strategy='token_bucket', rate=50, period=60)
def api_export(request):
    """导出功能，允许短时突发"""
    return JsonResponse({'status': 'exporting'})

# 成本限制
@cost_limit(max_cost=1000, operation='search')
def expensive_search(request):
    """限制昂贵操作的成本"""
    return JsonResponse({'status': 'ok'})
```

#### 方式 B: 函数调用

```python
from django.http import JsonResponse
from apps.core.rate_limiter import check_rate_limit

def api_view(request):
    # 检查是否超限
    allowed, info = check_rate_limit(
        user_id=request.user.id if request.user.is_authenticated else None,
        client_ip=get_client_ip(request),
        endpoint=request.path
    )
    
    if not allowed:
        return JsonResponse(
            {
                'error': '请求过于频繁，请稍候再试',
                'retry_after': info.get('reset_after', 60)
            },
            status=429
        )
    
    # 正常处理请求
    return JsonResponse({'data': 'your data'})
```

#### 方式 C: DRF 视图

```python
from rest_framework.viewsets import ModelViewSet
from apps.core.rate_limit_decorators import CustomUserThrottle

class MyViewSet(ModelViewSet):
    throttle_classes = [CustomUserThrottle]
    
    def create(self, request, *args, **kwargs):
        # 自动应用限流
        return super().create(request, *args, **kwargs)
```

### 3. 配置限流规则

```bash
# 调整用户级限流 (200 req/60s)
python manage.py rate_limit_manage --configure user 200 60

# 调整端点限流
python manage.py rate_limit_manage --configure endpoint 50 60

# 添加 IP 到白名单
python manage.py rate_limit_manage --whitelist ips add 10.0.0.0/8

# 添加用户到白名单
python manage.py rate_limit_manage --whitelist users add admin_user

# 将滥用用户加入黑名单
python manage.py rate_limit_manage --blacklist users add spammer
```

### 4. 监控限流情况

#### 使用管理命令

```bash
# 查看实时统计
python manage.py rate_limit_manage --stats

# 重置所有限流计数器
python manage.py rate_limit_manage --reset

# 重置特定用户的限流
python manage.py rate_limit_manage --reset-key user:123
```

#### 使用 API 端点

```bash
# 获取当前用户的限流状态
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/status/

# 获取统计信息
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/stats/

# 查看配置 (仅管理员)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  http://localhost:8000/api/core/rate-limit/config/
```

### 5. 测试

```bash
# 运行所有测试
python manage.py test test_level4_task1

# 运行特定测试
python manage.py test test_level4_task1.RateLimitStrategyTestCase
python manage.py test test_level4_task1.RateLimitAPITestCase

# 显示详细输出
python manage.py test test_level4_task1 -v 2
```

## 常见场景

### 场景 1: 保护登录端点

```python
# views.py
from rest_framework.views import APIView
from apps.core.rate_limit_decorators import rate_limit
from django.contrib.auth import authenticate

@rate_limit(requests=5, period=300)  # 5 次/5 分钟
def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    
    if user:
        return JsonResponse({'token': 'xxx'})
    return JsonResponse({'error': '登录失败'}, status=401)
```

**CLI 配置**:
```bash
python manage.py rate_limit_manage --configure user 5 300
```

### 场景 2: 大文件导出限制

```python
# views.py
from apps.core.rate_limit_decorators import cost_limit

@cost_limit(max_cost=5000, operation='export')
def export_data(request):
    # 导出需要消耗成本，防止过度导出
    file_size = len(data)
    return FileResponse(file_stream)
```

**配置**:
```bash
# 编辑 rate_limit_config.py，设置导出成本
# OPERATION_COSTS['export'] = 100
```

### 场景 3: API 分层访问

```python
# views.py
from apps.core.rate_limit_config import RateLimitConfig

def check_user_tier_limit(user):
    """根据用户层级应用不同的限流"""
    tier = get_user_tier(user)  # 'free', 'basic', 'premium', 'enterprise'
    multiplier = RateLimitConfig.USER_TIER_MULTIPLIERS[tier]
    
    # 获取基础限流
    user_limit = RateLimitConfig.DEFAULT_LIMITS['user']
    rate = user_limit['rate'] * multiplier
    period = user_limit['period']
    
    return rate, period
```

### 场景 4: 动态配置

```python
# Django shell
from apps.core.rate_limit_config import RateLimitConfig

# 在高负载时期降低限流
RateLimitConfig.configure_limit('global', rate=5000, period=60)

# 在维护期间白名单内部 IP
RateLimitConfig.add_whitelist('ips', ['192.168.0.0/16'])

# 事后恢复
RateLimitConfig.configure_limit('global', rate=10000, period=60)
```

## 管理命令完整参考

### 查看配置

```bash
python manage.py rate_limit_manage --list-config
```

输出:
```
=== 限流配置 ===

默认限流:
  global: 10000 req/60s
  user: 100 req/60s
  ip: 200 req/60s
  endpoint: 50 req/60s

端点限流:
  /api/login/: 5 req/60s
  /api/export/: 10 req/60s
  ...

用户层级倍数:
  free: 1.0x
  basic: 1.5x
  premium: 2.5x
  enterprise: 5.0x
```

### 配置限流

```bash
python manage.py rate_limit_manage --configure LEVEL RATE PERIOD

# 示例
python manage.py rate_limit_manage --configure user 150 60
# 将用户限流调为 150 req/60s
```

### 重置限流

```bash
# 重置所有
python manage.py rate_limit_manage --reset

# 重置特定键
python manage.py rate_limit_manage --reset-key user:123
python manage.py rate_limit_manage --reset-key ip:192.168.1.1
```

### 白名单管理

```bash
# 添加用户
python manage.py rate_limit_manage --whitelist users add admin

# 添加 IP
python manage.py rate_limit_manage --whitelist ips add 127.0.0.1

# 添加端点
python manage.py rate_limit_manage --whitelist endpoints add /api/health/

# 移除
python manage.py rate_limit_manage --whitelist users remove admin
```

### 黑名单管理

```bash
# 添加滥用用户
python manage.py rate_limit_manage --blacklist users add spammer

# 添加恶意 IP
python manage.py rate_limit_manage --blacklist ips add 203.0.113.0/24

# 移除
python manage.py rate_limit_manage --blacklist users remove spammer
```

### 查看统计

```bash
python manage.py rate_limit_manage --stats
```

输出:
```
=== 限流统计 ===

总请求数: 1523
允许: 1450
拒绝: 73
拒绝率: 4.79%
```

### 查看策略

```bash
python manage.py rate_limit_manage --strategies
```

输出:
```
=== 可用限流策略 ===

token_bucket:
  说明: 令牌桶算法
  优点: 允许短时突发，灵活
  缺点: 实现稍复杂
  使用场景: 一般 API，推荐

leaky_bucket:
  说明: 漏桶算法
  优点: 平滑流出，防止突发
  缺点: 处理能力恒定
  使用场景: 需要恒定处理速率
```

## API 端点参考

### 状态查询

```
GET /api/core/status/

响应:
{
  "allowed": true,
  "user_id": 123,
  "client_ip": "192.168.1.1",
  "limits": {
    "global": {"remaining": 9950, "reset_after": 60},
    "user": {"remaining": 95, "reset_after": 60},
    "ip": {"remaining": 195, "reset_after": 60},
    "endpoint": {"remaining": 48, "reset_after": 60}
  }
}
```

### 统计信息

```
GET /api/core/stats/

响应:
{
  "total_requests": 1523,
  "allowed": 1450,
  "denied": 73,
  "denial_rate": 0.0479
}
```

### 配置查询

```
GET /api/core/rate-limit/config/  (仅管理员)

响应:
{
  "limits": {...},
  "endpoint_limits": {...},
  "user_tiers": {...},
  "cost_budgets": {...}
}
```

### 重置限流

```
POST /api/core/rate-limit/reset/  (仅管理员)

请求体:
{
  "key": "user:123"  // 可选
}

响应:
{
  "message": "限流记录已重置: user:123"
}
```

## 故障排除

### 问题: 所有请求都被限流

**原因**: 限流配置过严格或缓存出现问题

**解决**:
```bash
# 检查配置
python manage.py rate_limit_manage --list-config

# 重置限流
python manage.py rate_limit_manage --reset

# 调整配置
python manage.py rate_limit_manage --configure user 500 60
```

### 问题: 白名单不工作

**原因**: IP 格式错误或用户名不匹配

**解决**:
```bash
# 检查 IP 格式 (应该是 x.x.x.x)
python manage.py rate_limit_manage --whitelist ips add 192.168.1.100

# 使用准确的用户名
python manage.py rate_limit_manage --whitelist users add exact_username
```

### 问题: 缓存占用空间过大

**原因**: 限流数据积累

**解决**:
```bash
# 定期重置
python manage.py rate_limit_manage --reset

# 或者在 settings.py 配置缓存过期时间
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 3600,  # 1 小时自动清除
    }
}
```

## 下一步

1. **集成中间件**: 将 `RateLimitMiddleware` 添加到 MIDDLEWARE
2. **保护关键端点**: 使用 `@rate_limit` 装饰器
3. **监控告警**: 设置告警阈值和通知
4. **升级到 Redis**: 对于生产环境，使用 Redis 替代内存缓存
5. **详细日志**: 启用详细日志记录限流事件

---

更详细的文档请参考 [LEVEL_4_TASK_1_REPORT.md](LEVEL_4_TASK_1_REPORT.md)
