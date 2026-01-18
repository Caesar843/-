# Celery 定时任务配置指南

## 概述

本项目使用 Celery 实现后台定时任务和异步处理。Celery 支持：
- ✅ 定时任务（Celery Beat）
- ✅ 异步任务执行（Celery Worker）
- ✅ 任务重试机制
- ✅ 任务监控（Flower）

## 部署前提

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

关键依赖：
- `celery` - 任务队列框架
- `redis` - 消息代理（推荐）或使用 RabbitMQ
- `flower` - 任务监控工具

### 2. 配置消息代理（Broker）

#### 方案A: 使用 Redis（推荐）

```bash
# Windows 下安装 Redis
choco install redis

# 或者使用 Docker
docker run -d -p 6379:6379 redis:latest
```

#### 方案B: 使用 RabbitMQ

```bash
# Windows 下安装
choco install rabbitmq

# 或使用 Docker
docker run -d -p 5672:5672 rabbitmq:latest
```

### 3. 配置 Django 设置

在 `config/settings.py` 中配置：

```python
# 使用 Redis
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# 或使用 RabbitMQ
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
```

## 启动 Celery

### 1. 启动 Celery Worker（执行任务）

```bash
# 基础启动
celery -A config worker -l info

# 指定并发数
celery -A config worker -l info --concurrency=4

# 后台运行（使用 nohup）
nohup celery -A config worker -l info > celery_worker.log 2>&1 &

# Windows 下使用 eventlet
celery -A config worker -l info -p eventlet
```

### 2. 启动 Celery Beat（定时任务调度）

```bash
# 基础启动
celery -A config beat -l info

# 指定数据库存储调度信息
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 后台运行
nohup celery -A config beat -l info > celery_beat.log 2>&1 &
```

### 3. 启动 Flower（监控工具）

```bash
# 启动 Flower 监控面板（访问 http://localhost:5555）
celery -A config flower

# 指定端口
celery -A config flower --port=5555
```

## 定时任务配置

### 任务列表

| 任务名 | 模块 | 执行频率 | 功能 |
|-------|------|---------|------|
| `generate-monthly-accounts` | finance | 每天 8:00 | 生成当月账单 |
| `send-payment-reminders` | finance | 工作日 10:00 | 发送支付提醒 |
| `send-overdue-alerts` | finance | 工作日 14:00 | 发送逾期告警 |
| `send-renewal-reminders` | store | 每月 1 日 9:00 | 发送续签提醒 |
| `backup-database` | backup | 周五 20:00 | 执行数据库备份 |
| `cleanup-old-data` | core | 每天 3:00 | 清理旧数据 |
| `generate-daily-reports` | reports | 工作日 7:00 | 生成日报表 |

### 修改任务计划

在 `config/celery.py` 中修改 `beat_schedule` 字典：

```python
app.conf.beat_schedule = {
    'your-task': {
        'task': 'apps.module.tasks.your_task_function',
        'schedule': crontab(hour=9, minute=0),  # 每天 9:00 执行
        'kwargs': {'param': 'value'}
    },
}
```

Crontab 语法示例：
```python
crontab(hour=9, minute=0)              # 每天 9:00
crontab(hour=9, minute=0, day_of_week='1-5')  # 工作日 9:00
crontab(hour=0, minute=0, day_of_month=1)     # 每月 1 日 00:00
crontab(day_of_week='0')               # 每周日
```

## 手动执行任务

### 1. 通过 Django Shell

```bash
python manage.py shell

# 在 Shell 中
from apps.finance.tasks import generate_monthly_accounts_task
result = generate_monthly_accounts_task.delay()
print(result.get())  # 等待结果
```

### 2. 通过 Celery 命令行

```bash
# 执行立即任务
celery -A config call apps.finance.tasks.generate_monthly_accounts_task

# 在 5 分钟后执行
celery -A config apply_async \
    -A config \
    --name=apps.finance.tasks.generate_monthly_accounts_task \
    --countdown=300
```

### 3. 在代码中执行

```python
from apps.finance.tasks import generate_monthly_accounts_task

# 异步执行
task = generate_monthly_accounts_task.delay()
print(f"Task ID: {task.id}")

# 立即执行并等待结果
result = generate_monthly_accounts_task.apply(timeout=30).get()
```

## 监控和调试

### 1. Flower 监控面板

访问 `http://localhost:5555`，可以查看：
- 正在执行的任务
- 已完成的任务
- 任务执行时间
- 错误日志
- Worker 状态

### 2. 查看任务日志

```bash
# 实时监控日志
tail -f celery_worker.log

# 查看特定任务的日志
celery -A config inspect active  # 查看活跃任务
celery -A config inspect stats   # 查看统计信息
```

### 3. 测试任务

```python
# 在 Django Shell 中测试
from apps.core.tasks import debug_task
result = debug_task.delay()
print(result.get(timeout=5))
```

## 生产部署

### 使用 Supervisor 管理进程

创建 `/etc/supervisor/conf.d/celery.conf`：

```ini
[program:celery_worker]
command=celery -A config worker -l info
directory=/path/to/project
autostart=true
autorestart=true
stderr_logfile=/var/log/celery_worker.log

[program:celery_beat]
command=celery -A config beat -l info
directory=/path/to/project
autostart=true
autorestart=true
stderr_logfile=/var/log/celery_beat.log
```

启动：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery_worker
sudo supervisorctl start celery_beat
```

### 使用 Systemd 管理进程

创建 `/etc/systemd/system/celery.service`：

```ini
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/usr/local/bin/celery -A config worker -l info --logfile=/var/log/celery.log --pidfile=/var/run/celery.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

启动：
```bash
sudo systemctl start celery
sudo systemctl enable celery  # 开机自启
```

## 常见问题

### 1. Redis 连接错误

```
Error: Unable to connect to Redis
```

**解决方案：**
```bash
# 检查 Redis 是否运行
redis-cli ping  # 应返回 PONG

# 检查连接 URL
CELERY_BROKER_URL = 'redis://localhost:6379/0'
```

### 2. 任务没有被执行

```bash
# 检查 Worker 是否运行
celery -A config inspect active

# 检查 Beat 是否运行
celery -A config inspect scheduled

# 查看日志
celery -A config worker -l debug
```

### 3. 任务重试无限循环

在任务中设置最大重试次数：
```python
@shared_task(bind=True, max_retries=3)
def my_task(self):
    try:
        # 任务代码
    except Exception as e:
        raise self.retry(exc=e, countdown=60)  # 60秒后重试
```

## 最佳实践

1. **使用声明式任务**：使用 `@shared_task` 装饰器
2. **设置合理的超时**：`CELERY_TASK_TIME_LIMIT`
3. **记录详细日志**：方便调试和监控
4. **使用重试机制**：处理网络等临时故障
5. **监控任务执行**：使用 Flower 或其他监控工具
6. **定期备份**：重要的定时任务添加备份和恢复机制

## 参考资源

- [Celery 官方文档](https://docs.celeryproject.io/)
- [Django Celery Beat](https://github.com/celery/django-celery-beat)
- [Flower 文档](https://flower.readthedocs.io/)
