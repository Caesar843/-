# 💻 系统演示操作指南

## 快速演示 (5 分钟)

### 第 1 步: 启动服务器
```bash
cd "d:\Python经典程序合集\商场店铺智能运营管理系统设计与实现"
python manage.py runserver
```

访问: http://localhost:8000

### 第 2 步: 创建超级用户 (如果还未创建)
```bash
python manage.py createsuperuser
# 输入用户名、邮箱、密码
```

### 第 3 步: 访问管理后台
```
URL: http://localhost:8000/admin
使用刚才创建的超级用户登录
```

---

## 功能演示脚本

### 演示 1: 合同评审工作流

#### 场景: 提交合同审核

```python
# 进入 Django Shell
python manage.py shell

# 导入必要的模块
from apps.store.models import Contract, Shop
from apps.store.services import StoreService
from django.contrib.auth.models import User

# 创建测试数据
shop = Shop.objects.first()  # 获取第一个店铺

# 创建一个合同
contract = Contract.objects.create(
    shop=shop,
    contract_number='TEST-2024-001',
    rent_amount=5000.00,
    status=Contract.Status.DRAFT,
    contract_start_date='2024-01-01',
    contract_end_date='2024-12-31'
)

# 提交审核
StoreService.submit_for_review(contract.id)
print(f"合同状态已更新为: {contract.status}")  # PENDING_REVIEW

# 获取审核人
reviewer = User.objects.filter(is_staff=True).first()

# 审批合同
StoreService.approve_contract(
    contract_id=contract.id,
    reviewer_id=reviewer.id,
    comment='合同条款合理，已批准'
)

# 查看审批结果
contract.refresh_from_db()
print(f"最终状态: {contract.status}")  # APPROVED
print(f"审核人: {contract.reviewed_by}")
print(f"审核时间: {contract.reviewed_at}")
print(f"审核意见: {contract.review_comment}")
```

---

### 演示 2: 发送通知

#### 场景: 创建和发送系统通知

```python
from apps.notification.services import NotificationService
from django.contrib.auth.models import User

# 获取目标用户
user = User.objects.first()

# 方法 1: 直接创建通知
notification = NotificationService.create_notification(
    recipient_id=user.id,
    type='CONTRACT_SUBMITTED',
    content='您有一份合同待审核',
    business_object_type='contract',
    business_object_id=1
)
print(f"通知已创建: {notification.id}")

# 方法 2: 使用模板发送
# 先创建一个通知模板
from apps.notification.models import NotificationTemplate

template = NotificationTemplate.objects.create(
    name='payment_reminder',
    type='SYSTEM',
    content='您有一笔账单即将到期: {amount} 元，请于 {due_date} 前支付',
    is_active=True
)

# 使用模板发送
notification = NotificationService.send_notification_by_template(
    recipient_id=user.id,
    template_name='payment_reminder',
    variables={
        'amount': '1000',
        'due_date': '2024-02-01'
    }
)

# 方法 3: 发送短信
result = NotificationService.send_sms(
    phone_number='13800138000',
    content='提醒：您有一笔待付款账单，请及时处理',
    provider='ALIYUN'
)
print(f"短信发送状态: {result['status']}")

# 获取用户的所有通知
notifications = NotificationService.get_user_notifications(user.id)
print(f"用户通知总数: {notifications.count()}")

# 标记通知为已读
NotificationService.mark_as_read(notification.id)
```

---

### 演示 3: 生成支付提醒

#### 场景: 自动发送支付提醒

```python
from apps.finance.services import FinanceService

# 发送 3 天内到期的账单提醒
result = FinanceService.send_payment_reminder_notifications(days_ahead=3)

print(f"处理账单数: {result['total']}")
print(f"发送系统消息: {result['notification_sent']} 条")
print(f"发送短信: {result['sms_sent']} 条")
print(f"发送失败: {result['failed']} 条")

# 发送逾期告警（给管理员）
overdue_result = FinanceService.send_overdue_payment_alert(days_overdue=0)
print(f"逾期账单告警已发送")
```

---

### 演示 4: 生成 PDF 收据

#### 场景: 为支付账单生成 PDF 收据

```python
from apps.finance.services import FinanceService
from apps.finance.models import FinanceRecord

# 获取一笔账单
finance_record = FinanceRecord.objects.first()

# 生成 PDF 收据
pdf_path = FinanceService.generate_payment_receipt_pdf(finance_record.id)
print(f"PDF 已生成: {pdf_path}")

# 批量生成多个收据
record_ids = FinanceRecord.objects.values_list('id', flat=True)[:5]
batch_result = FinanceService.batch_generate_payment_receipts(list(record_ids))

print(f"总共处理: {batch_result['total']} 个")
print(f"成功生成: {batch_result['success']} 个")
print(f"生成失败: {batch_result['failed']} 个")
print(f"生成文件: {batch_result['generated_files']}")
```

---

### 演示 5: 上传设备数据

#### 场景: 通过 API 上传设备数据

```bash
# 单条设备数据上传
curl -X POST http://localhost:8000/api/operations/device_data/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "device_id": "CAMERA-001",
    "device_type": "CAMERA",
    "shop_id": 1,
    "foot_traffic": 150,
    "sales_amount": 2500.50,
    "temperature": 22.5,
    "humidity": 45.0,
    "timestamp": "2024-01-15T14:30:00Z"
  }'

# 响应示例:
# {
#   "status": "success",
#   "record_id": 12345,
#   "device_id": "CAMERA-001",
#   "timestamp": "2024-01-15T14:30:00Z"
# }

# 批量上传设备数据
curl -X POST http://localhost:8000/api/operations/device_data/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "records": [
      {
        "device_id": "CAMERA-001",
        "device_type": "CAMERA",
        "shop_id": 1,
        "foot_traffic": 150,
        "sales_amount": 2500.50,
        "timestamp": "2024-01-15T14:30:00Z"
      },
      {
        "device_id": "SENSOR-002",
        "device_type": "SENSOR",
        "shop_id": 1,
        "foot_traffic": 200,
        "sales_amount": 3000.00,
        "timestamp": "2024-01-15T14:30:00Z"
      }
    ]
  }'

# 更新设备状态
curl -X PATCH http://localhost:8000/api/operations/device/CAMERA-001/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "status": "ONLINE",
    "ip_address": "192.168.1.100"
  }'
```

---

### 演示 6: 数据聚合分析

#### 场景: 执行数据聚合和分析

```python
from apps.operations.services import DeviceDataAggregationService
from datetime import date, datetime

# 小时级聚合
hourly_data = DeviceDataAggregationService.aggregate_hourly_data(
    shop_id=1,
    hour=datetime.now().replace(minute=0, second=0, microsecond=0)
)
print(f"小时聚合: 足迹 {hourly_data['total_foot_traffic']}，销售 {hourly_data['total_sales']}")

# 日级聚合
daily_data = DeviceDataAggregationService.aggregate_daily_data(
    shop_id=1,
    date=date.today()
)
print(f"日级聚合: 足迹 {daily_data['total_foot_traffic']}，销售 {daily_data['total_sales']}")

# 月级聚合
monthly_data = DeviceDataAggregationService.aggregate_monthly_data(
    shop_id=1,
    year=2024,
    month=1
)
print(f"月级聚合: 足迹 {monthly_data['total_foot_traffic']}，销售 {monthly_data['total_sales']}")

# 数据清洗
clean_result = DeviceDataAggregationService.clean_device_data()
print(f"清洗完成: 删除 {clean_result['duplicates_removed']} 条重复，修复 {clean_result['anomalies_fixed']} 条异常")
```

---

### 演示 7: 启动定时任务

#### 场景: 启动 Celery 后台任务

```bash
# 终端 1: 启动 Celery Worker
celery -A config worker -l info

# 输出示例:
# ---------- celery@HOSTNAME ready.
# [Tasks]
#   . apps.finance.tasks.generate_monthly_accounts_task
#   . apps.finance.tasks.send_payment_reminder_task
#   . apps.finance.tasks.send_overdue_payment_alert_task
#   ...

# 终端 2: 启动 Celery Beat（定时调度）
celery -A config beat -l info

# 输出示例:
# LocalTime -> 2024-01-15 10:00:00
# Scheduler -> celery.beat.PersistentScheduler
# [Beat] Ticking next 18 tasks in 58.60 seconds

# 终端 3: 启动 Flower 监控（可选）
celery -A config flower

# 访问 http://localhost:5555 查看任务执行情况
```

---

## 管理后台 (Django Admin) 操作

### 访问管理后台
1. 打开浏览器访问: http://localhost:8000/admin
2. 使用超级用户登录

### 可管理的对象

#### Store 应用
- **Shops** - 店铺列表，可编辑店铺信息
- **Contracts** - 合同管理，可查看评审状态和意见

#### Finance 应用
- **Finance Records** - 账单管理，可查看支付和提醒状态

#### Notification 应用
- **Notification Templates** - 通知模板管理
- **Notifications** - 系统通知记录
- **SMS Records** - 短信发送记录
- **Notification Preferences** - 用户通知偏好设置

#### Operations 应用
- **Devices** - 设备列表和状态
- **Device Data** - 设备数据记录

---

## 常见操作场景

### 场景 1: 审批新合同

1. 超级用户登录管理后台
2. 进入 Store → Contracts
3. 找到状态为 "PENDING_REVIEW" 的合同
4. 点击进入编辑
5. 审核合同内容
6. 设置 "reviewed_by" 为当前用户
7. 更改 "status" 为 "APPROVED" 或 "REJECTED"
8. 填写 "review_comment"
9. 保存

### 场景 2: 查看通知消息

1. 管理员登录后台
2. 进入 Notification → Notifications
3. 按 "type" 或 "status" 筛选
4. 点击通知查看详细信息
5. 查看关联的业务对象 (如合同 ID)

### 场景 3: 配置通知模板

1. 进入 Notification → Notification Templates
2. 点击"Add Notification Template"
3. 填写:
   - 名称 (name)
   - 类型 (type): SYSTEM, SMS, EMAIL, PUSH
   - 内容 (content): 可包含变量如 {amount}, {date}
   - 勾选 "is_active"
4. 保存

### 场景 4: 查看设备数据

1. 进入 Operations → Devices
2. 查看设备列表和在线状态
3. 点击设备查看详细信息和历史数据
4. 在 Device Data 中查看时间序列数据

---

## 测试数据创建

### 创建测试合同

```python
python manage.py shell

from apps.store.models import Shop, Contract
from datetime import date

shop = Shop.objects.first()

Contract.objects.create(
    shop=shop,
    contract_number='TEST-2024-001',
    rent_amount=5000.00,
    status=Contract.Status.DRAFT,
    contract_start_date='2024-01-01',
    contract_end_date='2024-12-31'
)

print("测试合同已创建")
```

### 创建测试账单

```python
from apps.finance.models import FinanceRecord
from datetime import datetime, timedelta

record = FinanceRecord.objects.create(
    contract_id=1,
    shop_id=1,
    amount=10000.00,
    status=FinanceRecord.Status.UNPAID,
    due_date=datetime.now().date() + timedelta(days=3),
    created_at=datetime.now()
)

print(f"测试账单已创建: {record.id}")
```

---

## 日志和调试

### 查看 Django 日志
```bash
# Django 开发服务器会在控制台输出所有请求和错误
# 默认日志级别: DEBUG
```

### 启用 Celery 日志
```bash
# Worker 已设置 -l info，显示任务执行信息
# 可更改为 debug 获取更详细的日志
celery -A config worker -l debug
```

### 检查数据库
```python
python manage.py shell

# 查看最近的通知
from apps.notification.models import Notification
Notification.objects.order_by('-created_at')[:5]

# 查看待发送的提醒
from apps.finance.models import FinanceRecord
FinanceRecord.objects.filter(reminder_sent=False)
```

---

## 故障排除

### 问题 1: Celery 无法启动
**解决**: 
```bash
pip install celery redis
```

### 问题 2: 通知发送失败
**检查**:
1. 用户 ID 是否正确
2. SMS 提供商配置是否完整
3. 查看日志找到具体错误信息

### 问题 3: PDF 生成失败
**原因**: WeasyPrint 依赖缺失
**解决**:
```bash
pip install weasyprint reportlab
```

### 问题 4: 数据聚合缓慢
**优化**:
1. 添加数据库索引
2. 使用批量聚合操作
3. 增加 Celery Worker 数量

---

**演示完成！现在您可以开始使用系统了！🎉**
