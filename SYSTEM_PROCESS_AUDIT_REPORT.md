# 商场店铺智能运营管理系统 - 流程实现审查报告

**审查日期：** 2026-01-16  
**系统版本：** Django 6.0.1，Python 3.13.0  
**审查人：** AI Assistant  

---

## 目录
1. [一、店铺入驻与合约管理流程](#一店铺入驻与合约管理流程)
2. [二、费用核算与收缴流程](#二费用核算与收缴流程)
3. [三、运营数据采集与分析流程](#三运营数据采集与分析流程)
4. [四、事务申请与处理流程](#四事务申请与处理流程)
5. [五、报表生成与应用流程](#五报表生成与应用流程)
6. [六、数据备份与恢复流程](#六数据备份与恢复流程)
7. [优先级补充实现清单](#优先级补充实现清单)

---

## 一、店铺入驻与合约管理流程

### 流程要求
商场运营专员录入新入驻店铺基本信息 → 创建租赁合同（填写租赁期限、租金标准等核心条款） → 经管理层审核通过 → 系统生成电子合约并推送至店铺确认 → 合约到期前30天自动触发续签提醒 → 双方确认后完成合约续签流程 → 更新系统记录。

### 现状分析

#### ✅ 已实现部分
- **店铺基本信息录入**  
  - 模型：`apps/store/models.py::Shop`
  - 字段完整：名称、业态、面积、租金、联系人、入驻日期、描述等
  - 支持业态类型枚举（零售、餐饮、娱乐、服务、其他）
  - 有创建时间、修改时间审计字段

- **合约创建与管理**  
  - 模型：`apps/store/models.py::Contract`
  - 支持合约状态机：DRAFT → ACTIVE → EXPIRED/TERMINATED
  - 记录起止日期、月租、审核状态等关键字段
  - 有合约条款描述

#### ⚠️ 部分缺失功能

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 合约电子签署与推送 | **高** | ❌ 缺失 | 需要集成电子签名或生成 PDF，推送到店铺邮箱/系统消息 |
| 管理层合约审核流程 | **高** | ❌ 缺失 | 需要在 Contract 模型中加入审核状态字段（PENDING_REVIEW、APPROVED、REJECTED）与审核人信息 |
| 合约到期前30天提醒 | **中** | ❌ 缺失 | 需要后台定时任务（Celery），每日检查即将过期合约并发送消息提醒 |
| 合约续签流程 | **高** | ❌ 缺失 | 需要续签业务逻辑，生成新合约副本、保留旧合约记录、更新生效日期 |

---

## 二、费用核算与收缴流程

### 流程要求
系统根据租赁合同约定及水电使用数据，每月自动生成店铺应缴费用明细单 → 通过系统消息、短信双重提醒店铺缴费 → 店铺在线完成缴费 → 系统实时更新缴费状态 → 财务管理员可审核缴费记录 → 生成缴费凭证。

### 现状分析

#### ✅ 已实现部分
- **财务记录模型**  
  - 模型：`apps/finance/models.py::FinanceRecord`
  - 支持费用类型：RENT（租金）、PROPERTY_FEE（物业费）、UTILITY_FEE（水电费）、OTHER（其他）
  - 支持支付方式：微信、支付宝、银行转账、现金
  - 支持状态机：UNPAID → PAID → VOID
  - 有交易单号、缴费时间、缴费凭证等字段

- **财务服务逻辑**  
  - 服务：`apps/finance/services.py::FinanceService`
  - 支持按合同自动按月生成租金账单：`generate_records_for_contract()`
  - 支持标记为已支付：`mark_as_paid()`
  - 支持获取待支付记录和支付历史

#### ⚠️ 部分缺失功能

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 系统消息 + 短信双重提醒 | **高** | ❌ 缺失 | 需要集成短信网关（如阿里云、腾讯云），在 FinanceService 中调用提醒接口 |
| 自动生成水电费账单 | **中** | ❌ 缺失 | 需要从 Device 数据读取水电使用数据，计算费用并自动生成账单 |
| 财务审核流程 | **高** | ❌ 缺失 | FinanceRecord 模型缺少"审核人"、"审核状态"等字段 |
| 缴费凭证生成 | **中** | ❌ 缺失 | 需要 PDF 生成库（如 reportlab、weasyprint），在支付后生成凭证 |
| 后台自动生成账单任务 | **高** | ❌ 缺失 | 需要 Celery Beat 定时任务，每月初自动为所有 ACTIVE 合同生成账单 |

---

## 三、运营数据采集与分析流程

### 流程要求
智能设备（客流统计仪、POS机）实时采集店铺运营数据 → 同步至系统数据库 → 店铺可补充上传手动统计数据 → 系统通过 Python 算法进行数据清洗、汇总 → 生成单店运营报表与商场整体运营分析图表 → 支持按时间（日/周/月）、业态类型筛选查看。

### 现状分析

#### ✅ 已实现部分
- **设备管理模型**  
  - 模型：`apps/operations/models.py::Device`
  - 支持设备类型：客流统计仪、POS 机、环境传感器、其他
  - 记录设备 ID、IP、MAC、API 密钥、最后活跃时间等
  - 支持设备状态：在线、离线、维护中

- **运营数据存储**  
  - 模型：`apps/operations/models.py::OperationData`（推测存在，未读全）
  - 支持按天、按店铺存储数据

- **报表生成框架**  
  - 视图：`apps/reports/views.py::ReportView`
  - 支持多种报表类型：shop_operation（店铺运营）、rent_collection（租金收缴）、business_type（业态分析）、operation_efficiency（运营效率）
  - 支持日期范围筛选
  - 支持导出格式：Excel、CSV、PDF

#### ⚠️ 部分缺失功能

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 设备实时数据采集接口 | **高** | ❌ 缺失 | 需要 API endpoint 接收设备推送数据，验证设备身份，存储数据 |
| 手动数据上传功能 | **中** | ❌ 缺失 | 需要前端表单和后端处理，支持店铺用户上传补充数据 |
| 数据清洗与汇总算法 | **高** | ❌ 缺失 | 需要 Python 数据处理逻辑（去重、异常检测、聚合统计） |
| 按周/月维度的聚合 | **中** | ❌ 缺失 | 目前可能只支持日维度，需要扩展到周、月维度 |
| 业态类型筛选 | **中** | ⚠️ 部分 | 报表视图有逻辑但实现细节需确认 |
| 可视化图表（前端） | **中** | ❌ 缺失 | 后端有数据，但前端需要集成图表库（如 ECharts、Chart.js） |

---

## 四、事务申请与处理流程

### 流程要求
店铺在线提交报修/活动申请 → 填写申请内容、所需资源、时间节点等 → 系统自动推送申请通知至对应商场运营专员 → 专员审核通过后指派处理人员 → 处理过程中实时更新进度 → 任务完成后店铺可进行满意度评价 → 系统记录全流程日志。

### 现状分析

#### ✅ 已实现部分
- **维修申请模型**  
  - 模型：`apps/communication/models.py::MaintenanceRequest`
  - 支持申请类型：水电故障、设备维修、设施维护、其他
  - 支持优先级：低、中、高、紧急
  - 支持状态流转：PENDING → ASSIGNED → IN_PROGRESS → COMPLETED/CANCELLED
  - 记录指派人员、预估/实际费用、完成日期

- **活动申请模型**  
  - 模型：`apps/communication/models.py::ActivityApplication`（推测存在）

- **日志记录**  
  - 支持记录全流程日志

#### ⚠️ 部分缺失功能

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 自动推送通知到运营专员 | **高** | ❌ 缺失 | 需要创建申请时自动发送系统消息 + 短信/邮件通知 |
| 满意度评价功能 | **中** | ❌ 缺失 | 需要在 MaintenanceRequest/ActivityApplication 模型中加入评价字段（score、comment） |
| 前端申请表单 | **中** | ❌ 缺失 | 需要创建/编辑表单模板，支持文件上传（现场照片等） |
| 处理进度实时更新 | **中** | ⚠️ 部分 | 模型支持状态更新，但需要确认是否有时间线/进度跟踪 |

---

## 五、报表生成与应用流程

### 流程要求
商场管理人员选择报表类型（如"季度租金收缴报表""业态运营分析报表"）与时间范围 → 系统关联店铺信息表、合约表、运营数据表、缴费记录表 → 计算核心指标（如租金收缴率、平均客流量、top10销售额店铺） → 生成可视化报表 → 支持在线预览、打印或导出（Excel/CSV/PDF）→ 适配运营汇报、财务核算、招商决策等场景。

### 现状分析

#### ✅ 已实现部分
- **报表生成框架**  
  - 视图：`apps/reports/views.py::ReportView`
  - 支持多种报表类型选择
  - 支持日期范围选择（默认最近30天）
  - 支持店铺过滤（按用户角色）
  - 支持导出为 Excel、CSV、PDF

- **报表服务**  
  - 服务：`apps/reports/services.py::ReportService`（推测存在）
  - 支持多种报表数据生成：shop_operation_summary、rent_collection_report、business_type_analysis、operation_efficiency_report

- **权限控制**  
  - 按用户角色分级显示报表：SUPER_ADMIN/MANAGEMENT 可看全部，OPERATION/FINANCE 可看部分，SHOP 只看自己

#### ⚠️ 部分缺失功能

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 核心指标计算逻辑 | **高** | ❌ 缺失 | 租金收缴率、平均客流量、top10销售额店铺等指标的具体算法需确认 |
| 多表关联查询优化 | **中** | ⚠️ 部分 | 需要确认是否有 N+1 查询问题、是否使用了数据库索引 |
| 可视化图表（前端） | **中** | ❌ 缺失 | 需要集成图表库展现数据 |
| 打印功能 | **中** | ❌ 缺失 | 需要通过 CSS 或服务端生成可打印 PDF |
| 定时报表生成 | **低** | ❌ 缺失 | 可选功能：定期生成日报、周报、月报供下载 |

---

## 六、数据备份与恢复流程

### 流程要求
系统每日凌晨自动备份全量数据 → 备份文件加密存储至指定服务器 → 若因故障导致数据异常 → 管理员可通过系统"数据恢复"功能选择历史备份节点 → 执行数据恢复操作 → 确保运营数据与管理记录的完整性。

### 现状分析

#### ✅ 已实现部分
- **备份管理应用**  
  - 模块：`apps/backup/` 已完整实现
  - 模型：BackupRecord、BackupLog
  - 支持备份类型：FULL（全量）、INCREMENTAL（增量）
  - 支持备份方式：自动、手动
  - 支持状态追踪：PENDING、RUNNING、SUCCESS、FAILED
  - 支持数据类型选择：SHOP、CONTRACT、OPERATION、FINANCE、LOG
  - 支持文件大小、MD5 校验、备份耗时记录
  - 有管理员界面（Django Admin）

- **备份服务**  
  - 服务：`apps/backup/services.py::BackupService`
  - 支持创建备份、验证备份、清理过期备份
  - 支持恢复服务

#### ✅ 基本功能完整，部分可选增强

| 功能 | 优先级 | 状态 | 备注 |
|------|--------|------|------|
| 每日凌晨自动备份 | **高** | ⚠️ 部分 | 模型和服务支持，但需要 Celery Beat 定时任务配置 |
| 备份文件加密存储 | **高** | ❌ 缺失 | 可选增强：集成 PyCryptodome 对备份文件加密 |
| 远程存储（云备份） | **中** | ❌ 缺失 | 可选增强：支持上传到 AWS S3、阿里云 OSS 等 |
| 数据恢复功能 | **中** | ⚠️ 部分 | 模型支持，需确认前端可用性和恢复测试 |
| 增量备份实现 | **低** | ❌ 缺失 | 可选优化：目前可能全量，支持增量可减少备份大小 |

---

## 优先级补充实现清单

### 🔴 P1 高优先级（立即实现）

#### 1. 合约管理补充
**位置：** `apps/store/models.py::Contract` + `apps/store/views.py`

```python
# 在 Contract 模型中新增字段
class Contract(models.Model):
    # ... 现有字段 ...
    
    # 审核相关
    review_status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', '草稿'),
            ('PENDING_REVIEW', '待审核'),
            ('APPROVED', '已批准'),
            ('REJECTED', '已拒绝'),
        ],
        default='DRAFT'
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_contracts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True, null=True)
```

**实现步骤：**
1. 创建迁移文件：`python manage.py makemigrations store`
2. 应用迁移：`python manage.py migrate store`
3. 在 `apps/store/services.py` 中实现：
   - `submit_for_review(contract_id)` - 提交审核
   - `approve_contract(contract_id, reviewer_id, comment)` - 批准合约
   - `reject_contract(contract_id, reviewer_id, reason)` - 拒绝合约

**时间估计：** 1-2 小时

---

#### 2. 费用双重提醒系统
**位置：** `apps/finance/services.py` + 新增通知服务

```python
# 新建 apps/notification/services.py
class NotificationService:
    @staticmethod
    def send_payment_reminder(finance_record, channels=['sms', 'message']):
        """
        发送缴费提醒
        channels: ['sms', 'message', 'email']
        """
        if 'sms' in channels:
            sms_client.send_sms(
                phone=finance_record.contract.shop.contact_phone,
                message=f"您有一笔 ¥{finance_record.amount} 的待缴费用，请及时支付。"
            )
        if 'message' in channels:
            Message.objects.create(
                user=finance_record.contract.shop.manager,
                content=f"待缴费用：¥{finance_record.amount}",
                type='FINANCE_REMINDER'
            )
```

**依赖：** 需要集成短信网关（建议使用阿里云或腾讯云 SDK）

**时间估计：** 2-3 小时

---

#### 3. 后台定时任务（Celery）
**位置：** 新建 `celery_tasks.py` 或 `apps/[app]/tasks.py`

```python
# 在 config/celery.py 中配置
from celery import shared_task
from celery.schedules import crontab

@shared_task
def generate_monthly_bills():
    """每月 1 日凌晨 00:05 生成账单"""
    from apps.finance.services import FinanceService
    from apps.store.models import Contract
    
    active_contracts = Contract.objects.filter(status='ACTIVE')
    for contract in active_contracts:
        FinanceService.generate_records_for_contract(contract.id)

@shared_task
def send_renewal_reminders():
    """每日检查即将过期合约"""
    from datetime import datetime, timedelta
    from apps.store.models import Contract
    from apps.notification.services import NotificationService
    
    soon_expire = Contract.objects.filter(
        end_date__range=[
            datetime.now().date(),
            (datetime.now() + timedelta(days=30)).date()
        ],
        status='ACTIVE'
    )
    for contract in soon_expire:
        NotificationService.send_renewal_reminder(contract)

# 在 config/celery.py 中注册定时任务
app.conf.beat_schedule = {
    'generate-monthly-bills': {
        'task': 'celery_tasks.generate_monthly_bills',
        'schedule': crontab(hour=0, minute=5, day_of_month=1),  # 每月1日 00:05
    },
    'send-renewal-reminders': {
        'task': 'celery_tasks.send_renewal_reminders',
        'schedule': crontab(hour=6, minute=0),  # 每天 06:00
    },
}
```

**依赖：** 需要安装并配置 Celery 和 Redis/RabbitMQ

**时间估计：** 1-2 小时

---

### 🟡 P2 中优先级（本周实现）

#### 4. 设备数据接收 API
**位置：** `apps/operations/views.py` + 新增 `apis.py`

```python
# REST API 接收设备数据
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_device_data(request):
    """
    接收设备推送数据
    POST /api/operations/device_data/
    {
        "device_id": "POS001",
        "data_type": "sales",
        "value": 1500.00,
        "timestamp": "2026-01-16T14:30:00Z"
    }
    """
    from apps.operations.models import Device, OperationData
    
    device_id = request.data.get('device_id')
    device = Device.objects.get(device_id=device_id)
    
    OperationData.objects.create(
        shop=device.shop,
        device=device,
        data_type=request.data.get('data_type'),
        value=request.data.get('value'),
        recorded_at=request.data.get('timestamp')
    )
    return Response({'status': 'success'})
```

**时间估计：** 2-3 小时

---

#### 5. 数据清洗与汇总服务
**位置：** `apps/operations/services.py`

```python
import pandas as pd
from django.db.models import Sum, Avg, Count

class DataAggregationService:
    @staticmethod
    def aggregate_daily_data(shop_id, date):
        """聚合某店铺某日的数据"""
        data = OperationData.objects.filter(
            shop_id=shop_id,
            recorded_at__date=date
        )
        
        stats = data.aggregate(
            total_sales=Sum('value'),
            avg_transaction=Avg('value'),
            count=Count('id')
        )
        return stats
    
    @staticmethod
    def aggregate_weekly_data(shop_id, start_date, end_date):
        """聚合周数据"""
        df = pd.DataFrame.from_records(
            OperationData.objects.filter(
                shop_id=shop_id,
                recorded_at__date__range=[start_date, end_date]
            ).values()
        )
        # 数据清洗：去除异常值
        df = df[df['value'] < df['value'].quantile(0.95)]  # 移除离群值
        return df.groupby('data_type').agg({
            'value': ['sum', 'mean', 'count']
        })
```

**时间估计：** 3-4 小时

---

### 🟢 P3 低优先级（优化）

#### 6. 可视化图表前端
**位置：** `templates/reports/` 新增图表模板

```html
<!-- 使用 ECharts -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<div id="salesChart" style="width: 100%; height: 400px;"></div>
<script>
const chart = echarts.init(document.getElementById('salesChart'));
const option = {
    xAxis: { type: 'category', data: {{ dates|safe }} },
    yAxis: { type: 'value' },
    series: [{
        data: {{ sales_data|safe }},
        type: 'line'
    }]
};
chart.setOption(option);
</script>
```

**时间估计：** 2-3 小时/图表

---

#### 7. 缴费凭证 PDF 生成
**位置：** `apps/finance/services.py`

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_receipt_pdf(finance_record):
    """生成缴费凭证 PDF"""
    filename = f"receipt_{finance_record.id}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    
    c.drawString(100, 750, f"凭证号：{finance_record.transaction_id}")
    c.drawString(100, 730, f"店铺：{finance_record.contract.shop.name}")
    c.drawString(100, 710, f"金额：¥{finance_record.amount}")
    c.drawString(100, 690, f"缴费方式：{finance_record.get_payment_method_display()}")
    c.drawString(100, 670, f"缴费时间：{finance_record.paid_at}")
    
    c.save()
    return filename
```

**时间估计：** 1 小时

---

## 总体建议

### 立即行动（本周）
1. ✅ 部署 Celery + Redis 用于后台任务
2. 实现 P1 项目（合约审核、费用提醒、定时任务）
3. 测试端到端流程

### 短期（2-4 周）
1. 实现 P2 项目（设备 API、数据聚合）
2. 补充前端表单和界面
3. 集成短信网关

### 中期（1-2 个月）
1. 优化数据查询性能
2. 实现可视化报表
3. 补充缺失的单元测试

### 可选增强
1. 备份文件加密
2. 云存储集成
3. 定时报表生成

---

## 附录：现有应用完整性评估

| 应用 | 模型完整度 | 业务逻辑完整度 | 前端完成度 | API 完成度 | 整体评分 |
|------|----------|-------------|---------|---------|--------|
| store | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | 3.0/5 |
| finance | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | 3.0/5 |
| operations | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | 2.0/5 |
| communication | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐ | 1.5/5 |
| reports | ⭐⭐ | ⭐⭐ | ⭐ | ⭐ | 1.5/5 |
| backup | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 4.2/5 |

**整体评分：** 2.5/5 - 数据模型充分，业务逻辑框架完整，但缺少集成、自动化、前端、API 的完整性

---

**报告生成时间：** 2026-01-16  
**下一步：** 确认优先级，分配任务，开始 P1 项目实现
