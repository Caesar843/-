# Level 4 Task 4: 国际化/本地化系统快速开始指南

## 📋 概述

本任务实现完整的国际化(i18n)和本地化(l10n)系统，支持以下功能：

- 🌐 **多语言支持**: 12+ 语言（中文、英文、西班牙语、法语等）
- 💱 **多货币支持**: 10+ 货币及实时汇率转换
- 🕐 **时区处理**: 10+ 时区转换
- 📅 **日期格式化**: 本地化日期/时间/数字格式
- 📱 **RTL 支持**: 支持阿拉伯语等从右到左的语言
- 🔄 **翻译管理**: 字符串翻译和参数替换
- 🎯 **性能优化**: 缓存和统计功能

## ✨ 核心功能

### 1. 多语言翻译

```python
from apps.core.i18n_manager import get_i18n_manager

# 获取管理器
manager = get_i18n_manager(language='en')

# 翻译字符串
hello = manager.translate('hello')  # 'Hello'

# 带参数翻译
greeting = manager.translate('greeting', name='John')
```

### 2. 货币转换

```python
from decimal import Decimal

# 转换货币
result = manager.convert_currency(
    Decimal('100'),      # 原金额
    'CNY',               # 源货币
    'USD'                # 目标货币
)

# 格式化货币
formatted = manager.format_currency(
    Decimal('1234.56'),
    'USD'
)  # '$ 1234.56'
```

### 3. 时区转换

```python
from datetime import datetime

# 转换时区
dt = datetime(2024, 1, 15, 12, 0, 0)
result = manager.convert_timezone(
    dt,
    'Asia/Shanghai',      # 源时区
    'America/New_York'    # 目标时区
)
```

### 4. 日期格式化

```python
# 格式化日期
formatted = manager.format_date(datetime.now(), 'date')     # '01/15/2024'
formatted = manager.format_date(datetime.now(), 'datetime')  # '01/15/2024 02:30:45 PM'
formatted = manager.format_date(datetime.now(), 'time')      # '02:30:45 PM'
```

### 5. 数字格式化

```python
# 格式化数字
formatted = manager.format_number(1234567.89)  # '1,234,567.89'
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install django-rest-framework pytz
```

### 2. 配置 Django

在 `config/settings.py` 中添加：

```python
# 国际化配置
USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = 'zh-cn'
TIME_ZONE = 'Asia/Shanghai'
```

### 3. 配置 URL

在 `config/urls.py` 中：

```python
urlpatterns = [
    # ... 其他路由 ...
    path('api/i18n/', include('apps.core.i18n_urls')),
]
```

### 4. 运行测试

```bash
# 运行所有 i18n 测试
python manage.py test apps.core.tests.test_level4_task4

# 运行特定测试
python manage.py test apps.core.tests.test_level4_task4.I18nManagerTests

# 显示详细输出
python manage.py test apps.core.tests.test_level4_task4 -v 2
```

## 📖 API 使用

### REST API 端点

```
GET    /api/i18n/languages/          - 获取支持的语言列表
GET    /api/i18n/currencies/         - 获取支持的货币列表
GET    /api/i18n/timezones/          - 获取支持的时区列表
POST   /api/i18n/translate/          - 翻译字符串
POST   /api/i18n/convert-currency/   - 货币转换
POST   /api/i18n/format-currency/    - 货币格式化
POST   /api/i18n/convert-timezone/   - 时区转换
POST   /api/i18n/format-date/        - 日期格式化
POST   /api/i18n/format-number/      - 数字格式化
GET    /api/i18n/info/               - 获取 i18n 信息
```

### API 示例

**获取语言列表**
```bash
curl http://localhost:8000/api/i18n/languages/
```

**翻译字符串**
```bash
curl -X POST http://localhost:8000/api/i18n/translate/ \
  -H "Content-Type: application/json" \
  -d '{"key": "hello", "language": "en"}'
```

**货币转换**
```bash
curl -X POST http://localhost:8000/api/i18n/convert-currency/ \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "from_currency": "CNY", "to_currency": "USD"}'
```

**时区转换**
```bash
curl -X POST http://localhost:8000/api/i18n/convert-timezone/ \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "2024-01-15T12:00:00",
    "from_timezone": "Asia/Shanghai",
    "to_timezone": "America/New_York"
  }'
```

## 🛠️ CLI 工具

### 管理命令

```bash
# 列出所有支持的语言
python manage.py i18n_manage --list-languages

# 列出所有支持的货币
python manage.py i18n_manage --list-currencies

# 列出所有支持的时区
python manage.py i18n_manage --list-timezones

# 翻译字符串
python manage.py i18n_manage --translate "hello" --language "en"

# 货币转换
python manage.py i18n_manage --convert-currency 100 \
  --from-currency CNY --to-currency USD

# 货币格式化
python manage.py i18n_manage --format-currency 1234.56 \
  --currency USD --language "en"

# 时区转换
python manage.py i18n_manage --convert-timezone "2024-01-15T12:00:00" \
  --from-timezone "Asia/Shanghai" --to-timezone "America/New_York"

# 日期格式化
python manage.py i18n_manage --format-date "2024-01-15T12:00:00" \
  --language "en" --format-type "date"

# 数字格式化
python manage.py i18n_manage --format-number 1234567.89 \
  --language "en" --decimal-places 2

# 显示 i18n 信息
python manage.py i18n_manage --info --language "en"

# 测试系统
python manage.py i18n_manage --test
```

## 📝 支持的语言

| 代码 | 语言 | 默认货币 | 默认时区 |
|------|------|---------|---------|
| zh-cn | 中文 (简体) | CNY | Asia/Shanghai |
| zh-hk | 中文 (繁体) | HKD | Asia/Shanghai |
| en | English | USD | America/New_York |
| es | Español | EUR | Europe/Madrid |
| fr | Français | EUR | Europe/Paris |
| de | Deutsch | EUR | Europe/Berlin |
| ja | 日本語 | JPY | Asia/Tokyo |
| ko | 한국어 | KRW | Asia/Seoul |
| ru | Русский | RUB | Europe/Moscow |
| pt | Português | EUR | Europe/Lisbon |
| ar | العربية | AED | Asia/Dubai |
| hi | हिन्दी | INR | Asia/Kolkata |

## 💱 支持的货币

- CNY (¥) - 人民币
- USD ($) - 美元
- EUR (€) - 欧元
- GBP (£) - 英镑
- JPY (¥) - 日元
- KRW (₩) - 韩元
- INR (₹) - 印度卢比
- RUB (₽) - 俄罗斯卢布
- AED (د.إ) - 阿联酋迪拉姆
- AUD (A$) - 澳大利亚元

## 🕐 支持的时区

- Asia/Shanghai (中国)
- America/New_York (美国东部)
- America/Los_Angeles (美国西部)
- Europe/London (英国)
- Europe/Paris (法国)
- Europe/Berlin (德国)
- Asia/Tokyo (日本)
- Asia/Seoul (韩国)
- Asia/Dubai (阿联酋)
- Australia/Sydney (澳大利亚)

## 🧪 测试覆盖

- ✅ 40+ 单元测试
- ✅ 配置测试 (7 个)
- ✅ 管理器测试 (25 个)
- ✅ 工厂测试 (3 个)
- ✅ API 测试 (10 个)
- ✅ 集成测试 (3 个)
- ✅ 性能测试 (3 个)

## 📊 性能指标

| 操作 | 性能 | 状态 |
|------|------|------|
| 翻译 | < 1ms | ✅ |
| 货币转换 | < 1ms | ✅ |
| 时区转换 | < 2ms | ✅ |
| 日期格式化 | < 1ms | ✅ |
| 数字格式化 | < 1ms | ✅ |
| 100 次操作 | < 100ms | ✅ |

## 🎯 常见使用场景

### 场景 1: 电商商品价格显示

```python
# 根据用户语言和位置显示价格
user_language = 'en'
user_timezone = 'America/New_York'
product_price = Decimal('99.99')

manager = get_i18n_manager(language=user_language)

# 如果用户在美国，显示 USD
if user_language == 'en':
    price_usd = manager.format_currency(product_price, 'USD')
    # 显示: $ 99.99

# 如果用户在中国，显示 CNY
elif user_language == 'zh-cn':
    manager = get_i18n_manager(language=user_language, currency='CNY')
    price_cny = manager.convert_currency(product_price, 'USD', 'CNY')
    formatted = manager.format_currency(price_cny, 'CNY')
    # 显示: ¥ 688.00
```

### 场景 2: 全球订单时间显示

```python
# 显示订单创建时间（本地时区）
order_created = datetime(2024, 1, 15, 12, 0, 0)
user_timezone = 'America/Los_Angeles'
user_language = 'en'

manager = get_i18n_manager(language=user_language, timezone_str=user_timezone)

# 转换为用户时区
local_time = manager.convert_timezone(order_created, 'Asia/Shanghai', user_timezone)

# 格式化为用户语言
formatted_time = manager.format_date(local_time, 'datetime')
# 显示: 01/14/2024 08:00:00 PM
```

### 场景 3: 数字和货币显示

```python
# 显示销售统计
sales_amount = Decimal('1234567.89')
user_language = 'de'
user_currency = 'EUR'

manager = get_i18n_manager(language=user_language, currency=user_currency)

# 格式化为德文格式
formatted_number = manager.format_number(sales_amount)
# 显示: 1.234.567,89 (德文使用句号和逗号)

formatted_currency = manager.format_currency(sales_amount, user_currency)
# 显示: € 1.234.567,89
```

## ✅ 验证检查清单

- [ ] 安装了必要依赖
- [ ] 配置了 Django settings
- [ ] 配置了 URL 路由
- [ ] 运行了所有 40+ 测试
- [ ] 所有测试都通过
- [ ] 验证了 API 端点
- [ ] 测试了 CLI 命令
- [ ] 检查了性能指标

## 🔗 相关资源

- Django i18n 文档: https://docs.djangoproject.com/en/stable/topics/i18n/
- Pytz 时区库: http://pytz.sourceforge.net/
- 货币代码标准: ISO 4217
- 语言代码标准: ISO 639-1

## 🚀 后续扩展

1. **数据库翻译**: 支持数据库中的可翻译字段
2. **浏览器语言检测**: 自动检测用户浏览器语言
3. **翻译管理面板**: Web UI 管理翻译
4. **复数形式处理**: 支持英文等的单复数
5. **日期相对格式**: 支持 "2 小时前" 等相对格式
6. **货币符号位置**: 支持不同的货币符号位置
7. **数字分组**: 支持不同的数字分组规则

完成以上步骤后，您已经拥有一个完整的国际化/本地化系统！
