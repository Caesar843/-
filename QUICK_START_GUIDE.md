# 🚀 商场店铺智能运营管理系统 - 快速启动指南

## 系统状态

✅ **Django 系统检查已通过** - 零错误
✅ **所有应用已注册** - 12个 Django 应用就绪
✅ **所有数据库迁移已应用** - 完整的数据模型
✅ **服务层已完成** - 业务逻辑实现
✅ **API 端点已配置** - REST 接口就绪

---

## 环境配置

### 1. Python 版本要求
```bash
Python 3.10+ （推荐 3.11 或 3.13）
当前: Python 3.13.0
```

### 2. 已安装的核心依赖
```
Django 6.0.1
Django REST Framework
SQLite3 (开发环境)
```

### 3. 可选但推荐的依赖（用于完整功能）

#### 异步任务支持（Celery + Redis）
```bash
pip install celery redis
```

用途：
- 定时任务执行（12+ 定时任务）
- 后台任务处理（支付提醒、备份、报表生成等）
- 数据聚合与清洗

#### PDF 生成支持
```bash
pip install weasyprint reportlab
```

用途：
- 生成支付收据 PDF
- 报表导出
- 双引擎支持（主: WeasyPrint, 备: ReportLab）

---

## 快速启动步骤

### 步骤 1: 安装所有依赖（可选）
```bash
pip install -r requirements.txt
```

### 步骤 2: 运行服务器
```bash
python manage.py runserver
```

访问：http://localhost:8000

### 步骤 3: 访问管理后台
```
URL: http://localhost:8000/admin
用户名: (需要创建超级用户)
密码: (需要创建超级用户)
```

创建超级用户：
```bash
python manage.py createsuperuser
```

---

## 启用完整功能（可选）

### 启用 Celery 任务队列

#### 3.1 安装依赖
```bash
pip install celery redis
```

#### 3.2 启动 Redis（如果未运行）
```bash
# Windows (使用 WSL 或 Docker)
wsl redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis
```

#### 3.3 启动 Celery Worker
```bash
celery -A config worker -l info
```

#### 3.4 启动 Celery Beat（定时任务）
```bash
celery -A config beat -l info
```

#### 3.5 监控 Celery（可选）
```bash
pip install flower
celery -A config flower --port=5555
访问: http://localhost:5555
```

---

## 已实现的功能模块

### 1. 店铺管理 (Store)
- ✅ 店铺信息管理
- ✅ **合同评审工作流** (新增)
  - 提交审核 → 审核员审批 → 确认状态
  - 完整的审计跟踪

### 2. 财务管理 (Finance)
- ✅ 账单管理
- ✅ **支付提醒服务** (新增)
  - 双渠道提醒（系统消息 + 短信）
  - 自动化支付提醒流程
- ✅ **PDF 收据生成** (新增)
  - 支持双引擎渲染
  - 批量生成

### 3. 通知系统 (Notification) - 新增
- ✅ 4 个通知模型
  - NotificationTemplate（通知模板）
  - Notification（系统通知）
  - SMSRecord（短信记录）
  - NotificationPreference（用户偏好）
- ✅ NotificationService（通知服务）
  - 模板渲染
  - 多渠道发送
  - SMS 提供商抽象

### 4. 运营数据 (Operations) - 增强
- ✅ **设备数据 API** (新增)
  - POST /api/operations/device_data/ (单条或批量上传)
  - PATCH /api/operations/device/<device_id>/status/
- ✅ **数据聚合服务** (新增)
  - 小时级聚合
  - 日级聚合
  - 月级聚合
- ✅ **数据清洗** (新增)
  - 重复数据清除
  - 异常值修复
  - 数据质量评分

### 5. 定时任务 (Celery) - 新增
- ✅ 18 个定时任务
  - 财务: 3 个任务（账单、提醒、告警）
  - 店铺: 3 个任务（续签、过期、统计）
  - 备份: 3 个任务（备份、验证、清理）
  - 系统: 3 个任务（清理、健康检查、日志）
  - 报表: 3 个任务（日报、周报、月报）
  - 运营: 5 个任务（聚合、清洗、状态检查）

### 6. 备份系统 (Backup)
- ✅ 数据库备份
- ✅ 增量备份支持
- ✅ 备份验证
- ✅ 恢复功能

### 7. 报表系统 (Reports)
- ✅ 日报表
- ✅ 周报表
- ✅ 月报表

### 8. 用户管理 (User Management)
- ✅ 用户权限管理
- ✅ 角色分配

---

## 数据库状态

### 已应用的迁移
```
✅ store: 0001 - 0005 (最新: 合同评审字段)
✅ finance: 0001 - 0003 (最新: 提醒标志字段)
✅ notification: 0001 (新: 4 个通知模型)
✅ operations: 0001 - 0002 (设备数据模型)
✅ 其他应用: 所有迁移已应用
```

### 表结构
- Store.Contract: 添加了 reviewed_by, reviewed_at, review_comment
- Finance.FinanceRecord: 添加了 reminder_sent
- Notification: 新增 4 个表
  - notification_notificationtemplate
  - notification_notification
  - notification_smsrecord
  - notification_notificationpreference

---

## 配置参数说明

### Django 设置 (config/settings.py)

#### 时区与语言
```python
TIME_ZONE = 'Asia/Shanghai'
LANGUAGE_CODE = 'zh-Hans'
```

#### Celery 配置（可选）
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30分钟
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25分钟
```

---

## 常见问题

### Q1: Celery 未安装可以运行项目吗？
**A:** 是的。系统已实现优雅降级。没有 Celery 时：
- 所有 Web API 正常工作
- 定时任务不会执行
- 可以手动触发异步操作

### Q2: 如何测试通知系统？
```python
from apps.notification.services import NotificationService

NotificationService.send_sms(
    phone_number='13800138000',
    content='这是一条测试短信'
)
```

### Q3: 如何测试 PDF 生成？
```python
from apps.finance.services import FinanceService

# 生成单个收据
pdf_file = FinanceService.generate_payment_receipt_pdf(finance_record_id=1)

# 批量生成
result = FinanceService.batch_generate_payment_receipts([1, 2, 3])
```

### Q4: 如何上传设备数据？
```bash
curl -X POST http://localhost:8000/api/operations/device_data/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEVICE001",
    "device_type": "CAMERA",
    "shop_id": 1,
    "foot_traffic": 100,
    "sales_amount": 1000.00,
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

---

## 下一步

### 推荐配置
1. ✅ 安装 Celery 和 Redis
2. ✅ 启动后台任务队列
3. ✅ 配置 SMS 服务提供商（短信功能）
4. ✅ 创建管理用户进行权限管理

### 生产环境部署
1. 配置数据库（MySQL/PostgreSQL）
2. 配置缓存（Redis）
3. 配置消息队列（RabbitMQ/Redis）
4. 配置静态文件服务
5. 配置日志系统
6. 配置监控告警

参考文档: [CELERY_SETUP_GUIDE.md](CELERY_SETUP_GUIDE.md)

---

## 文档索引

| 文档 | 说明 |
|-----|------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 完整的实现总结（9个功能模块） |
| [CELERY_SETUP_GUIDE.md](CELERY_SETUP_GUIDE.md) | Celery 部署和配置指南 |
| [MANUAL_START_GUIDE.md](MANUAL_START_GUIDE.md) | 手动启动指南 |
| [BUG_FIX_REPORT.md](BUG_FIX_REPORT.md) | 修复报告 |

---

## 系统架构

```
商场店铺智能运营管理系统
├── Frontend
│   └── 模板系统 (Django Templates)
│
├── API Layer
│   ├── REST Framework
│   ├── Device Data API
│   ├── Operations API
│   └── ...其他 API
│
├── Business Logic (Services)
│   ├── StoreService (合同管理)
│   ├── FinanceService (财务管理 + PDF)
│   ├── NotificationService (通知系统)
│   ├── OperationAnalysisService (数据分析)
│   ├── DeviceDataAggregationService (数据聚合)
│   └── ...其他服务
│
├── Models
│   ├── Store (店铺、合同)
│   ├── Finance (账单、提醒)
│   ├── Notification (消息、短信)
│   ├── Operations (设备、数据)
│   └── ...其他模型
│
├── Task Queue (Celery) - 可选
│   ├── Worker (任务执行)
│   ├── Beat (定时调度)
│   └── Result Backend (结果存储)
│
└── Database
    └── SQLite3 / MySQL / PostgreSQL
```

---

## 系统要求总结

### 最小配置
- Python 3.10+
- Django 6.0.1
- SQLite3

### 推荐配置
- Python 3.11+
- Django 6.0.1
- PostgreSQL（生产）
- Redis（缓存 + 任务队列）
- RabbitMQ（生产消息队列）

---

**系统已准备就绪！🎉**

任何问题请参考详细文档或查看代码注释。
