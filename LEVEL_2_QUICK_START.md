# Level 2 快速启动指南

本指南帮助您快速了解和使用 Level 2 新增的功能。

---

## 🚀 5 分钟快速开始

### 1. 验证安装
```bash
cd "d:\Python经典程序合集\商场店铺智能运营管理系统设计与实现"
python manage.py check
# 输出：System check identified no issues (0 silenced).
```

### 2. 测试健康检查
```bash
# 启动服务器
python manage.py runserver

# 在另一个终端测试
curl http://localhost:8000/core/health/
```

### 3. 创建数据库备份
```bash
python manage.py database_backup
# 输出：备份已创建: backups/backup_YYYYMMDD_HHMMSS.sql.gz
```

### 4. 配置 Sentry（可选）
```bash
# 编辑 .env 文件
SENTRY_DSN=your-sentry-dsn-here
ENVIRONMENT=production
DEBUG=False

# Sentry 将自动初始化
python manage.py runserver
```

---

## 📚 详细文档

| 功能 | 文档位置 | 说明 |
|-----|---------|------|
| Sentry 错误追踪 | SENTRY_SETUP_GUIDE.md | 完整的 Sentry 使用指南 |
| 完成报告 | LEVEL_2_COMPLETION_REPORT.md | 详细的任务完成报告 |
| 快速摘要 | LEVEL_2_COMPLETION_SUMMARY.md | 本文档的详细版本 |
| 验证脚本 | test_level2.py | 自动化功能验证 |

---

## 🎯 各功能使用

### 健康检查端点

**用途**：监控系统各个组件的健康状态

**访问方式**：
```
GET /core/health/
```

**响应示例**：
```json
{
    "status": "healthy",
    "checks": {
        "database": {
            "status": "ok",
            "response_time_ms": 1.2
        },
        "redis": {
            "status": "ok",
            "response_time_ms": 0.8
        },
        "disk_space": {
            "status": "ok",
            "percent_used": 45
        },
        "active_connections": 23
    },
    "timestamp": "2024-01-16T18:04:45.123Z"
}
```

**应用场景**：
- Kubernetes liveness/readiness probe
- 监控系统定期检查
- 负载均衡器健康检查
- CI/CD 流水线验证

---

### 数据库备份脚本

**用途**：保护数据库数据安全，支持快速恢复

**命令**：
```bash
# 创建备份
python manage.py database_backup

# 查看所有备份
python manage.py database_backup --list

# 还原指定备份
python manage.py database_backup --restore backup_20240116_180445.sql.gz

# 清理超过 30 天的备份
python manage.py database_backup --cleanup 30

# 创建不压缩的备份
python manage.py database_backup --no-compress
```

**定时备份设置**（Cron）：
```bash
# 每天凌晨 2 点自动备份
0 2 * * * cd /path/to/project && python manage.py database_backup

# 每周日凌晨 3 点清理旧备份
0 3 * * 0 cd /path/to/project && python manage.py database_backup --cleanup 30
```

**Celery 集成**：
```python
# 在 celery 任务中调用
from apps.core.management.commands.database_backup import BackupManager

@shared_task
def backup_database():
    manager = BackupManager()
    result = manager.backup()
    return result
```

---

### Django 安全硬化

**已应用的安全措施**：

1. **HTTPS 强制**
   ```python
   SECURE_SSL_REDIRECT = True  # 生产环境
   ```

2. **HSTS 头**
   ```python
   SECURE_HSTS_SECONDS = 31536000  # 1 年
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   ```

3. **Cookie 安全**
   ```python
   SESSION_COOKIE_SECURE = True
   SESSION_COOKIE_HTTPONLY = True
   CSRF_COOKIE_SECURE = True
   CSRF_COOKIE_HTTPONLY = True
   ```

4. **内容安全策略**
   ```python
   SECURE_CONTENT_TYPE_NOSNIFF = True
   SECURE_BROWSER_XSS_FILTER = True
   X_FRAME_OPTIONS = 'DENY'
   ```

**验证安全配置**：
```bash
# 使用在线工具检查
# https://securityheaders.com
```

---

### 异常处理中间件

**用途**：统一捕获和处理所有异常，提供一致的错误响应

**自动捕获的异常**：
- Django 视图异常
- API 请求错误
- 数据库错误
- 中间件异常
- 未处理的 Python 异常

**错误响应格式**：
```json
{
    "success": false,
    "error_id": "550e8400-e29b-41d4-a716-446655440000",
    "error_code": "CONTRACT_ERROR",
    "message": "用户可见的错误信息",
    "data": {
        "field": "additional_context"
    },
    "category": "business_logic"
}
```

**使用业务异常**：
```python
from apps.core.exception_handlers import ContractException, FinanceException

# 合同相关错误
def create_contract(data):
    try:
        contract = Contract.objects.create(**data)
    except Exception as e:
        raise ContractException(
            message="合同创建失败，请检查输入数据",
            internal_message=str(e),
            data={"field": data}
        )

# 财务相关错误
def process_payment(order):
    if order.total <= 0:
        raise FinanceException(
            message="订单金额不合法",
            internal_message=f"Invalid amount: {order.total}"
        )
```

**使用装饰器**：
```python
from apps.core.exception_handlers import handle_exceptions, handle_drf_exceptions

# 普通视图装饰器
@handle_exceptions
def my_view(request):
    # 任何异常都会被自动捕获
    user = User.objects.get(id=request.GET['id'])  # KeyError、DoesNotExist 都会被处理
    return render(request, 'template.html')

# DRF 视图装饰器
@handle_drf_exceptions
def my_api_view(request):
    # 返回统一格式的 JSON 错误响应
    data = request.POST.get('required_field')  # KeyError 自动处理
    return Response({'status': 'ok'})
```

---

### Sentry 错误追踪

**配置步骤**：

1. **创建 Sentry 项目**
   - 访问 https://sentry.io/
   - 创建新项目，选择 Django
   - 复制 DSN

2. **设置环境变量** (.env)
   ```
   SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/your-project-id
   ENVIRONMENT=production
   SENTRY_TRACES_SAMPLE_RATE=0.1
   RELEASE=1.0.0
   ```

3. **启动应用**
   ```bash
   DEBUG=False python manage.py runserver
   # Sentry 将自动初始化并捕获错误
   ```

**手动上报错误**：
```python
import sentry_sdk

# 上报异常
try:
    process_order(order)
except Exception as e:
    sentry_sdk.capture_exception(e)

# 上报消息
sentry_sdk.capture_message("订单处理开始", level="info")

# 添加自定义上下文
sentry_sdk.set_user({"id": user.id, "email": user.email})
sentry_sdk.set_tag("shop_id", shop_id)
sentry_sdk.set_context("order", {
    "order_id": order.id,
    "amount": order.total
})

# 添加面包屑
sentry_sdk.add_breadcrumb(
    category="payment",
    message="Payment processed",
    level="info"
)
```

**查看错误**：
- 访问 Sentry 仪表板
- 查看错误聚合和趋势
- 分析受影响的用户
- 配置告警规则

---

## 🔧 故障排除

### 问题：Django check 失败
```bash
# 解决方案
python manage.py check
# 如果仍有错误，检查 settings.py 和 urls.py

# 清除缓存
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
```

### 问题：备份创建失败
```bash
# 检查数据库连接
python manage.py dbshell

# 检查磁盘空间
df -h

# 检查权限
ls -la backups/
```

### 问题：Sentry 未捕获错误
```bash
# 检查配置
python -c "from django.conf import settings; print(settings.SENTRY_DSN, settings.DEBUG)"

# 测试连接
curl https://your-org.ingest.sentry.io/

# 查看初始化日志
python manage.py runserver 2>&1 | grep -i sentry
```

---

## 📊 监控与告警

### 设置健康检查监控
```bash
# Prometheus 配置示例
- job_name: 'django-health'
  static_configs:
    - targets: ['localhost:8000']
  metrics_path: '/core/health/'
```

### Sentry 告警规则
1. **新错误告警**
   - 条件：error.new_issues
   - 通知：Slack/Email

2. **错误频率告警**
   - 条件：error.rate > 100 / 1m
   - 通知：PagerDuty

3. **性能告警**
   - 条件：transaction.p95 > 1000ms
   - 通知：Email

---

## 📈 性能优化建议

### 生产环境配置
```python
# settings.py
SENTRY_TRACES_SAMPLE_RATE = 0.05  # 5% 追踪率
SENTRY_SAMPLE_RATE = 1.0          # 100% 错误上报

# 数据库性能
DATABASES['default']['CONN_MAX_AGE'] = 600  # 连接池

# 缓存
CACHES['default']['TIMEOUT'] = 3600  # 1 小时
```

### 备份性能
```bash
# 异步备份（使用 Celery）
celery -A config worker -l info

# 定时备份（使用 Celery Beat）
celery -A config beat -l info
```

---

## 🎓 学习资源

### 官方文档
- [Django 安全检查表](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Django REST Framework](https://www.django-rest-framework.org/)

### 本项目文档
- SENTRY_SETUP_GUIDE.md - Sentry 完整指南
- LEVEL_2_COMPLETION_REPORT.md - 详细完成报告
- 代码中的注释 - 函数和类的详细说明

---

## ✅ 快速检查清单

生产部署前的检查清单：

- [ ] 运行 `python manage.py check`
- [ ] 运行 `python test_level2.py`
- [ ] 配置 Sentry DSN（如需要）
- [ ] 设置定时备份任务
- [ ] 配置监控告警
- [ ] 进行安全审计
- [ ] 测试备份和恢复流程
- [ ] 配置日志收集
- [ ] 进行性能测试
- [ ] 准备发布说明

---

## 🆘 获取帮助

### 常见问题
查看 SENTRY_SETUP_GUIDE.md 中的"故障排除"章节

### 文档
- 本文档：LEVEL_2_QUICK_START.md
- 完成报告：LEVEL_2_COMPLETION_REPORT.md
- 总结：LEVEL_2_COMPLETION_SUMMARY.md

### 代码示例
项目中的所有新增代码都有详细的中文注释和文档字符串

---

**准备好使用 Level 2 的新功能了吗？现在就开始吧！** 🚀
