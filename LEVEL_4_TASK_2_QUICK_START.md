<!-- Celery 异步任务系统快速开始指南 -->

# Level 4 Task 2: Celery 异步任务系统

## 📋 概述

本任务实现一个完整的异步任务队列系统，基于 Celery 和 Redis，用于处理以下场景：
- 💰 财务任务（账单检查、提醒、收入计算）
- 📊 报告生成（小时、日、周、月报告）
- 📧 通知系统（邮件发送、清理过期通知）
- 📤 数据处理（导出数据）
- 🔧 系统维护（备份数据库、清理缓存）

## ✨ 特性

### 1. **异步任务支持**
- 15+ 预定义任务
- 任务参数配置
- 失败自动重试
- 任务进度跟踪

### 2. **计划任务**（Beat Schedule）
- 每分钟：检查待支付账单
- 每小时：生成小时报告
- 每天 2:00 AM：清理过期通知
- 每周一 10:00 AM：生成周报告
- 每月 1 号午夜：生成月报告

### 3. **任务监控**
- 实时任务状态查询
- 任务执行统计
- 工作进程监控
- 队列信息查询
- 执行历史记录

### 4. **管理接口**
- RESTful API（7+ 端点）
- 命令行工具（10+ 命令）
- 权限控制
- 任务撤销功能

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保已安装依赖
pip install celery redis django-celery-beat

# 启动 Redis 服务器
redis-server

# 或 Windows 用户
redis-server.exe
```

### 2. Django 配置

在 `config/settings.py` 中添加：

```python
# Celery 配置
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = False
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 分钟
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 分钟
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_RESULT_EXPIRES = 3600  # 1 小时

# Beat 调度器
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

在 `config/urls.py` 中添加：

```python
urlpatterns = [
    # ... 其他路由
    path('api/core/', include('apps.core.celery_urls')),
]
```

### 3. 启动服务

```bash
# 终端 1: 启动 Celery Worker（处理普通任务）
celery -A config worker -l info -Q default,email,reports,finance

# 终端 2: 启动 Celery Beat（处理计划任务）
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 终端 3: 启动 Django 开发服务器
python manage.py runserver
```

## 📖 API 使用示例

### 1. 获取所有活动任务

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/tasks/
```

响应：
```json
{
  "count": 2,
  "results": [
    {
      "task_id": "abc-123",
      "task_name": "test_task",
      "status": "SUCCESS",
      "result": "Task received: test"
    }
  ]
}
```

### 2. 发送新任务

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "task_name": "test_task",
    "args": ["hello"],
    "kwargs": {}
  }' \
  http://localhost:8000/api/core/tasks/
```

### 3. 检查任务状态

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/tasks/abc-123/
```

### 4. 撤销任务

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/tasks/abc-123/revoke/
```

### 5. 获取任务统计

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/tasks/stats/
```

### 6. 获取执行历史

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/tasks/history/
```

### 7. 获取工作进程信息

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/core/workers/
```

## 🛠️ 命令行工具

### 1. 列出所有活动任务

```bash
python manage.py celery_manage --list-tasks
```

输出：
```
Active Celery Tasks
═══════════════════════════════════════════════════════════════
Task ID                          Task Name                Status
───────────────────────────────────────────────────────────────
abc123def456...                  test_task                SUCCESS
xyz789uvw012...                  check_pending_bills      PENDING
```

### 2. 发送任务

```bash
python manage.py celery_manage --send-task test_task

# 带参数
python manage.py celery_manage --send-task test_task \
  --args '["hello"]' \
  --kwargs '{"param": "value"}'

# 发送邮件通知
python manage.py celery_manage --send-task send_notification_email \
  --kwargs '{"email": "user@example.com", "subject": "Test", "message": "Hello"}'
```

### 3. 检查任务状态

```bash
python manage.py celery_manage --task-status abc123def456...
```

### 4. 撤销任务

```bash
python manage.py celery_manage --revoke-task abc123def456...
```

### 5. 工作进程信息

```bash
python manage.py celery_manage --worker-stats
```

输出：
```
Worker Statistics
═══════════════════════════════════════════════════════════════
Worker                           Status       Active Tasks
───────────────────────────────────────────────────────────────
celery@hostname                  online       2
celery@hostname.2                online       1
```

### 6. 队列信息

```bash
python manage.py celery_manage --queue-stats
```

### 7. 任务统计

```bash
python manage.py celery_manage --task-stats
```

### 8. 执行历史

```bash
python manage.py celery_manage --history
```

### 9. 测试连接

```bash
python manage.py celery_manage --test-task
```

## 📋 预定义任务列表

### 财务任务

| 任务名 | 描述 | 计划 |
|--------|------|------|
| `check_pending_bills` | 检查待支付账单 | 每分钟 |
| `send_bill_reminders` | 发送账单提醒 | 按需 |
| `calculate_monthly_revenue` | 计算月度收入 | 按需 |

### 报告任务

| 任务名 | 描述 | 计划 |
|--------|------|------|
| `generate_hourly_report` | 生成小时报告 | 每小时 |
| `generate_daily_report` | 生成日报告 | 按需 |
| `generate_weekly_report` | 生成周报告 | 每周一 10:00 |
| `generate_monthly_report` | 生成月报告 | 每月 1 日午夜 |

### 通知任务

| 任务名 | 描述 | 计划 |
|--------|------|------|
| `send_notification_email` | 发送通知邮件 | 按需 |
| `cleanup_old_notifications` | 清理过期通知 | 每天 2:00 AM |

### 数据任务

| 任务名 | 描述 | 计划 |
|--------|------|------|
| `export_data` | 导出数据 | 按需 |

### 维护任务

| 任务名 | 描述 | 计划 |
|--------|------|------|
| `backup_database` | 备份数据库 | 按需 |
| `cleanup_cache` | 清理缓存 | 按需 |

## 🔐 权限控制

### API 权限

- **所有端点**: 需要认证 (`IsAuthenticated`)
- **撤销任务**: 需要管理员权限 (`IsAdminUser`)
- **获取工作进程**: 仅管理员

### 创建超级用户

```bash
python manage.py createsuperuser
```

## 🧪 运行测试

```bash
# 运行所有 Task 2 测试
python manage.py test apps.core.tests.test_level4_task2

# 运行特定测试类
python manage.py test apps.core.tests.test_level4_task2.CeleryTaskDefinitionTests

# 运行特定测试方法
python manage.py test apps.core.tests.test_level4_task2.CeleryTaskDefinitionTests.test_test_task

# 显示详细输出
python manage.py test apps.core.tests.test_level4_task2 -v 2
```

**测试覆盖**：
- ✅ 14 个任务定义测试
- ✅ 7 个监控系统测试
- ✅ 11 个 API 接口测试
- ✅ 6 个集成测试
- ✅ 5 个鲁棒性测试
- ✅ 3 个监控测试
- ✅ 3 个管理器测试

**总计**: **49 个测试用例**

## 🐛 调试技巧

### 1. 启用 Celery 日志

```python
# config/celery.py
import logging

logging.basicConfig(level=logging.DEBUG)
```

### 2. 在生产模式测试

```bash
# 禁用 eager 执行（真实异步）
export CELERY_ALWAYS_EAGER=False

# 启用 worker
celery -A config worker -l debug
```

### 3. 监控 Redis 队列

```bash
# 使用 Redis CLI
redis-cli

# 查看队列大小
LLEN celery

# 查看所有键
KEYS *
```

### 4. 检查失败的任务

```bash
# 在 Django Shell 中
python manage.py shell
>>> from celery.result import AsyncResult
>>> result = AsyncResult('task-id')
>>> result.status
>>> result.info  # 失败原因
```

## 📊 监控面板

### Flower（Celery 监控工具）

```bash
# 安装
pip install flower

# 启动
celery -A config events --broker redis://localhost:6379/0
flower --broker=redis://localhost:6379/0

# 访问
http://localhost:5555
```

## 🔄 集成场景

### 场景 1: 每小时生成报告

```python
from apps.core.celery_tasks import generate_hourly_report

# 立即执行
result = generate_hourly_report.apply_async()
print(f"任务 ID: {result.id}")

# 查看状态
from apps.core.celery_monitor import TaskMonitor
monitor = TaskMonitor()
status = monitor.get_task_status(result.id)
print(f"状态: {status['status']}")
```

### 场景 2: 批量发送邮件

```python
from apps.core.celery_tasks import send_notification_email

emails = ['user1@example.com', 'user2@example.com']
for email in emails:
    send_notification_email.apply_async(
        args=(email, '欢迎', '感谢使用系统')
    )
```

### 场景 3: 监控任务执行

```python
from apps.core.celery_monitor import TaskMonitor

monitor = TaskMonitor()

# 获取统计信息
stats = monitor.get_task_stats()
print(f"总任务数: {stats.get('total_tasks', 0)}")

# 获取执行历史
history = monitor.get_task_history(limit=10)
for task in history:
    print(f"{task['task_name']}: {task['status']}")
```

## 🌐 多队列配置

系统使用以下队列：
- `default`: 默认队列（测试任务等）
- `finance`: 财务任务
- `reports`: 报告生成任务
- `email`: 邮件通知任务

启动特定队列的 worker：

```bash
# 仅处理财务任务
celery -A config worker -l info -Q finance

# 处理多个队列
celery -A config worker -l info -Q default,finance,reports

# 为不同队列启动多个 worker
celery -A config worker -l info -Q finance &
celery -A config worker -l info -Q reports,email &
```

## 📈 性能优化

### 1. 调整 Worker 并发数

```bash
# 增加并发数（CPU 密集型）
celery -A config worker -l info --concurrency 8

# 减少并发数（I/O 密集型）
celery -A config worker -l info --concurrency 2
```

### 2. 配置池类型

```bash
# 使用线程池（I/O 密集型）
celery -A config worker -l info --pool threads

# 使用进程池（CPU 密集型，默认）
celery -A config worker -l info --pool prefork
```

### 3. 优化 Redis 连接

```python
# config/celery.py
CELERY_BROKER_POOL_LIMIT = None  # 无限连接
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

## 📝 最佳实践

1. **使用专用队列**: 为不同类型的任务创建专用队列
2. **设置合理超时**: 避免任务永久挂起
3. **实现重试逻辑**: 使用 `autoretry_for` 处理临时故障
4. **监控死信队列**: 追踪失败的任务
5. **定期清理结果**: 防止 Redis 内存溢出
6. **使用任务签名**: 确保任务参数有效
7. **实现错误通知**: 在任务失败时发送警告

## 🆘 故障排除

### 问题：Worker 无法连接 Redis

```bash
# 检查 Redis 服务
redis-cli ping

# 验证配置
python manage.py shell
>>> from django.conf import settings
>>> settings.CELERY_BROKER_URL
```

### 问题：任务一直处于 PENDING 状态

```bash
# 确保 Worker 运行中
celery -A config worker -l debug

# 检查队列
redis-cli LLEN celery

# 清除过期任务
redis-cli FLUSHDB
```

### 问题：结果无法检索

```bash
# 检查结果后端配置
redis-cli SELECT 1  # 结果存储库
KEYS *  # 查看存储的结果

# 增加结果过期时间
CELERY_RESULT_EXPIRES = 86400  # 24 小时
```

## 📞 支持

- 查看日志: `logs/celery.log`
- 运行诊断: `python diagnose.py`
- 检查权限: `python manage.py test_permissions.py`

## ✅ 验证检查清单

- [ ] Redis 服务运行中
- [ ] Celery Worker 已启动
- [ ] Celery Beat 已启动
- [ ] Django 应用已启动
- [ ] API 端点响应正常
- [ ] 任务可以成功发送
- [ ] 任务状态可以查询
- [ ] 监控数据可以获取
- [ ] 命令行工具正常工作
- [ ] 所有 49 个测试通过
- [ ] 无错误日志

完成以上步骤后，您已经拥有一个完整的异步任务处理系统！
