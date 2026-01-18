# ============================================
# Sentry 错误追踪配置指南
# ============================================

## 概述
本项目使用 Sentry 进行生产环境的错误追踪、监控和告警。
Sentry 是一个实时错误报告平台，可以帮助开发团队识别和解决应用程序中的问题。

## 功能特性

### 1. 自动错误捕获
- Django 视图异常自动上报
- 中间件捕获的未处理异常
- 数据库错误和查询超时
- API 请求错误

### 2. 性能监控（Performance Monitoring）
- 追踪事务（HTTP 请求）
- 数据库查询监控
- 缓存操作监控
- 外部 API 调用时间

### 3. 自定义上下文
- 用户信息
- 请求详情（URL、参数、请求头）
- 自定义标签和面包屑

### 4. 智能告警
- 新错误通知
- 错误频率异常告警
- 性能降级告警
- 自定义告警规则

## 安装与配置

### 1. 安装依赖
```bash
pip install sentry-sdk
```

### 2. 配置环境变量
```bash
# .env 文件

# Sentry DSN（获取地址：https://sentry.io）
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# 环境标识
ENVIRONMENT=production

# 性能追踪采样率（0.0-1.0）
SENTRY_TRACES_SAMPLE_RATE=0.1  # 追踪 10% 的请求

# 错误采样率（0.0-1.0）
SENTRY_SAMPLE_RATE=1.0  # 报告所有错误

# 应用版本
RELEASE=1.0.0
```

### 3. 设置步骤

#### a) 创建 Sentry 项目
1. 访问 https://sentry.io/
2. 创建账户或登录
3. 创建新项目，选择 Django
4. 复制 DSN

#### b) 配置 Django
```python
# 在 settings.py 中自动初始化（已完成）
# 当 SENTRY_DSN 环境变量不为空且 DEBUG=False 时，自动初始化
```

#### c) 验证配置
```bash
python manage.py shell
>>> import sentry_sdk
>>> sentry_sdk.get_client().is_active()
True
```

## 使用示例

### 1. 自动捕获错误
```python
# 视图异常会自动上报
def my_view(request):
    user = User.objects.get(id=invalid_id)  # 会自动捕获异常
    return Response({'status': 'ok'})
```

### 2. 手动上报错误
```python
import sentry_sdk

try:
    # 某些操作
    process_data()
except Exception as e:
    # 手动上报异常
    sentry_sdk.capture_exception(e)
    
    # 或者只上报消息
    sentry_sdk.capture_message("数据处理失败", level="error")
```

### 3. 添加自定义上下文
```python
import sentry_sdk

# 设置用户信息
sentry_sdk.set_user({"id": user.id, "email": user.email})

# 添加自定义标签
sentry_sdk.set_tag("shop_id", request.shop_id)
sentry_sdk.set_tag("operation", "checkout")

# 添加额外数据
sentry_sdk.set_context("transaction", {
    "order_id": order.id,
    "amount": order.total,
    "status": order.status
})

# 添加面包屑（事件链）
sentry_sdk.add_breadcrumb(
    category="auth",
    message="User logged in",
    level="info",
    data={"user_id": user.id}
)
```

### 4. 自定义异常处理
```python
from apps.core.exception_handlers import ContractException
import sentry_sdk

def create_contract(data):
    try:
        contract = Contract.objects.create(**data)
    except Exception as e:
        # 业务异常
        sentry_sdk.set_tag("error_type", "contract_creation")
        raise ContractException("合同创建失败，请检查参数") from e
```

### 5. 性能监控
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# 自动追踪 HTTP 请求
# 在 settings.py 中配置 traces_sample_rate

# 手动创建事务
from sentry_sdk import start_transaction

with start_transaction(op="batch_process", name="Process Orders"):
    for order in orders:
        with start_transaction(op="process_order", name=f"Order {order.id}"):
            process_order(order)
```

## 告警配置

### 1. 创建告警规则
在 Sentry 项目中：
1. 进入 Project Settings → Alerts
2. 创建新告警规则

### 2. 常用告警条件
- **新错误**：`error.new_issues`
- **错误频率**：`error.rate > 100 / 1m`
- **性能降级**：`transaction.p95 > 1000ms`
- **特定错误**：`error.type == "ContractException"`

### 3. 告警通知
- Email 通知
- Slack 集成
- PagerDuty 集成
- Webhook 集成

## 数据隐私与安全

### 1. 敏感数据过滤
```python
# 在 Sentry 初始化时自动配置
# - 不捕获本地变量（include_local_variables=False）
# - 自动过滤敏感字段（密码、token、API 密钥）
```

### 2. 数据保留
```python
# Sentry 账户设置中配置
# - 默认保留 90 天
# - 生产环境可根据需要调整
```

### 3. 合规性
- GDPR 合规：可在 Sentry 设置中删除用户数据
- 自定义数据过滤：`before_send` 回调函数

## 集成与扩展

### 1. Slack 集成
```bash
# 在 Sentry 项目中安装 Slack 应用
# 配置通知频道
```

### 2. GitHub 集成
```bash
# 连接 GitHub 仓库
# 自动创建 Issue（如果配置）
# 追踪提交和发布
```

### 3. CI/CD 集成
```bash
# GitLab CI
SENTRY_AUTH_TOKEN=your_token sentry-cli releases create...

# GitHub Actions
- uses: getsentry/action-release@v1
```

## 监控仪表板

### 1. 关键指标
- **错误率**：错误数 / 总请求数
- **受影响用户**：遇到错误的用户数
- **新错误**：24 小时内新发现的错误类型
- **P95 响应时间**：慢请求的阈值

### 2. 自定义仪表板
在 Sentry 中创建自定义仪表板来追踪：
- 关键业务指标错误
- API 端点性能
- 第三方服务依赖性

## 故障排除

### 1. 错误未上报
```python
# 检查 DEBUG 设置
DEBUG = False  # 必须是 False

# 检查 DSN
SENTRY_DSN = config('SENTRY_DSN')
print(SENTRY_DSN)  # 应该有值

# 验证初始化
import sentry_sdk
print(sentry_sdk.get_client().is_active())  # 应该是 True
```

### 2. 性能问题
```python
# 降低 traces_sample_rate
SENTRY_TRACES_SAMPLE_RATE = 0.01  # 只追踪 1% 的请求

# 增加 max_breadcrumbs
max_breadcrumbs = 10  # 减少内存占用
```

### 3. 数据量过大
```python
# 使用 sample_rate 降采样
SENTRY_SAMPLE_RATE = 0.5  # 只报告 50% 的错误

# 配置 ignore_errors 排除特定错误
```

## 最佳实践

### 1. 错误分类
使用标签区分：
```python
sentry_sdk.set_tag("error_category", "payment")  # 支付错误
sentry_sdk.set_tag("error_category", "inventory")  # 库存错误
sentry_sdk.set_tag("error_category", "notification")  # 通知错误
```

### 2. 发布版本管理
```bash
# 每次部署时更新 RELEASE
RELEASE=v1.0.0-20240116  # YYYY-MM-DD 格式
```

### 3. 环境隔离
```python
# 不同环境使用不同的 Sentry 项目
# .env.production: SENTRY_DSN=https://...@prod-project
# .env.staging: SENTRY_DSN=https://...@staging-project
```

### 4. 定期审查
- 每周审查错误报告
- 识别和修复重复出现的错误
- 优化性能基准

## 生产部署清单

- [ ] 配置 SENTRY_DSN
- [ ] 设置 ENVIRONMENT=production
- [ ] 配置合理的 SENTRY_TRACES_SAMPLE_RATE
- [ ] 设置告警规则
- [ ] 配置 Slack/Email 通知
- [ ] 定义错误应对流程
- [ ] 测试错误上报
- [ ] 配置数据保留策略
- [ ] 设置用户反馈表单
- [ ] 培训团队使用 Sentry

## 参考资源

- Sentry 官网：https://sentry.io/
- Django 集成文档：https://docs.sentry.io/platforms/python/guides/django/
- API 文档：https://docs.sentry.io/api/
- 最佳实践：https://blog.sentry.io/

## 支持与帮助

- 技术支持：support@sentry.io
- 社区论坛：https://forum.sentry.io/
- GitHub 问题：https://github.com/getsentry/sentry/issues
