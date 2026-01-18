# 📚 Level 4 Task 4 - 快速参考指南 (Cheat Sheet)

## 🎯 快速命令参考

### Python 代码使用

```python
# ============ 导入 ============
from apps.core.i18n_manager import I18nFactory, I18nManager
from apps.core.i18n_config import *
from decimal import Decimal
from datetime import datetime

# ============ 创建管理器 ============
manager = I18nFactory.get_manager(
    language='en',
    currency='USD',
    timezone_str='America/New_York'
)

# 或使用默认
default_manager = I18nFactory.get_default_manager()

# ============ 翻译 ============
text = manager.translate('hello')                              # 'Hello'
greeting = manager.translate('greeting', name='John')         # 'Hello John'

# ============ 货币转换 ============
cny_100 = Decimal('100')
usd = manager.convert_currency(cny_100, 'CNY', 'USD')         # Decimal('14.49')
eur = manager.convert_currency(cny_100, 'CNY', 'EUR')         # Decimal('13.40')

# ============ 货币格式化 ============
formatted_usd = manager.format_currency(Decimal('1234.56'), 'USD')   # '$ 1,234.56'
formatted_cny = manager.format_currency(Decimal('1234.56'), 'CNY')   # '¥ 1,234.56'

# ============ 时区转换 ============
dt = datetime(2024, 1, 15, 12, 0, 0)
ny_time = manager.convert_timezone(dt, 'Asia/Shanghai', 'America/New_York')
london_time = manager.convert_timezone(dt, 'Asia/Shanghai', 'Europe/London')

# ============ 日期格式化 ============
date_str = manager.format_date(datetime.now(), 'date')        # '01/15/2024'
time_str = manager.format_date(datetime.now(), 'time')        # '02:30:45 PM'
datetime_str = manager.format_date(datetime.now(), 'datetime') # '01/15/2024 02:30:45 PM'

# ============ 数字格式化 ============
num_str = manager.format_number(1234567.89)                   # '1,234,567.89'
num_str = manager.format_number(1234567.89, 2)               # '1,234,567.89'

# ============ 获取信息 ============
lang_info = manager.get_language_info()                       # {'name': 'English', ...}
currency_symbol = manager.get_currency_symbol('USD')          # '$'
is_rtl = manager.is_rtl()                                     # False

# ============ 切换设置 ============
manager.set_language('zh-cn')
manager.set_currency('CNY')
manager.set_timezone('Asia/Shanghai')

# ============ 获取统计 ============
stats = manager.get_statistics()                              # {'translations': 5, ...}
```

---

## 🌐 REST API 快速参考

### 基本 URL
```
基础: http://localhost:8000/api/i18n/
```

### 获取数据 (GET)

```bash
# 获取所有支持的语言
curl http://localhost:8000/api/i18n/languages/

# 获取所有支持的货币
curl http://localhost:8000/api/i18n/currencies/

# 获取所有支持的时区
curl http://localhost:8000/api/i18n/timezones/

# 获取 i18n 信息
curl http://localhost:8000/api/i18n/info/
```

### 发送数据 (POST)

```bash
# 翻译字符串
curl -X POST http://localhost:8000/api/i18n/translate/ \
  -H "Content-Type: application/json" \
  -d '{
    "key": "hello",
    "language": "en"
  }'

# 货币转换
curl -X POST http://localhost:8000/api/i18n/convert-currency/ \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "100",
    "from_currency": "CNY",
    "to_currency": "USD"
  }'

# 货币格式化
curl -X POST http://localhost:8000/api/i18n/format-currency/ \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1234.56",
    "currency": "USD",
    "language": "en"
  }'

# 时区转换
curl -X POST http://localhost:8000/api/i18n/convert-timezone/ \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "2024-01-15T12:00:00",
    "from_timezone": "Asia/Shanghai",
    "to_timezone": "America/New_York"
  }'

# 日期格式化
curl -X POST http://localhost:8000/api/i18n/format-date/ \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "2024-01-15T12:00:00",
    "language": "en",
    "format_type": "date"
  }'

# 数字格式化
curl -X POST http://localhost:8000/api/i18n/format-number/ \
  -H "Content-Type: application/json" \
  -d '{
    "number": 1234567.89,
    "language": "en",
    "decimal_places": 2
  }'
```

---

## 🛠️ CLI 命令快速参考

### 列表命令

```bash
# 列出所有语言
python manage.py i18n_manage --list-languages

# 列出所有货币
python manage.py i18n_manage --list-currencies

# 列出所有时区
python manage.py i18n_manage --list-timezones
```

### 翻译命令

```bash
# 翻译单个词汇
python manage.py i18n_manage --translate hello --language en

# 翻译多个词汇
python manage.py i18n_manage --translate "hello" --language zh-cn
python manage.py i18n_manage --translate "goodbye" --language fr
```

### 货币命令

```bash
# 货币转换
python manage.py i18n_manage --convert-currency 100 \
  --from-currency CNY --to-currency USD

# 多个货币转换
python manage.py i18n_manage --convert-currency 100 \
  --from-currency CNY --to-currency EUR
python manage.py i18n_manage --convert-currency 100 \
  --from-currency CNY --to-currency GBP

# 货币格式化
python manage.py i18n_manage --format-currency 1234.56 \
  --currency USD --language en

python manage.py i18n_manage --format-currency 1234.56 \
  --currency CNY --language zh-cn
```

### 时区命令

```bash
# 时区转换
python manage.py i18n_manage --convert-timezone "2024-01-15T12:00:00" \
  --from-timezone "Asia/Shanghai" \
  --to-timezone "America/New_York"

# 另一个时区转换
python manage.py i18n_manage --convert-timezone "2024-01-15T12:00:00" \
  --from-timezone "Asia/Shanghai" \
  --to-timezone "Europe/London"
```

### 格式化命令

```bash
# 日期格式化
python manage.py i18n_manage --format-date "2024-01-15T12:00:00" \
  --language en --format-type date

# 日期时间格式化
python manage.py i18n_manage --format-date "2024-01-15T12:00:00" \
  --language en --format-type datetime

# 时间格式化
python manage.py i18n_manage --format-date "2024-01-15T14:30:45" \
  --language en --format-type time

# 数字格式化
python manage.py i18n_manage --format-number 1234567.89 \
  --language en --decimal-places 2

python manage.py i18n_manage --format-number 1234567.89 \
  --language de --decimal-places 2
```

### 系统命令

```bash
# 显示 i18n 信息
python manage.py i18n_manage --info --language en

# 系统测试
python manage.py i18n_manage --test
```

---

## 📊 常见场景速查表

### 场景 1: 显示国际化商品价格

```python
# 用户选择: 中文 + CNY, 英文 + USD, 德文 + EUR
scenarios = [
    ('zh-cn', 'CNY'),
    ('en', 'USD'),
    ('de', 'EUR'),
]

product_price = Decimal('99.99')  # USD 价格

for language, currency in scenarios:
    manager = I18nFactory.get_manager(language=language, currency=currency)
    
    # 转换价格
    if currency != 'USD':
        converted = manager.convert_currency(product_price, 'USD', currency)
    else:
        converted = product_price
    
    # 格式化
    formatted = manager.format_currency(converted, currency)
    print(f"{language}: {formatted}")

# 输出:
# zh-cn: ¥ 688.00
# en: $ 99.99
# de: € 91.66
```

### 场景 2: 全球订单时间显示

```python
# 订单创建时间 (UTC)
order_time = datetime(2024, 1, 15, 12, 0, 0)

# 用户所在时区
user_timezones = ['America/New_York', 'Asia/Shanghai', 'Europe/London']

for tz in user_timezones:
    manager = I18nFactory.get_manager(timezone_str=tz)
    local_time = manager.convert_timezone(order_time, 'UTC', tz)
    formatted = manager.format_date(local_time, 'datetime')
    print(f"{tz}: {formatted}")

# 输出:
# America/New_York: 01/15/2024 07:00:00 AM
# Asia/Shanghai: 01/15/2024 08:00:00 PM
# Europe/London: 01/15/2024 12:00:00 PM
```

### 场景 3: 多语言统计显示

```python
sales_total = Decimal('1234567.89')
languages = ['en', 'zh-cn', 'de', 'fr']

for lang in languages:
    manager = I18nFactory.get_manager(language=lang)
    formatted = manager.format_number(sales_total)
    currency_symbol = manager.get_currency_symbol('CNY')
    print(f"{lang}: {currency_symbol} {formatted}")

# 输出:
# en: ¥ 1,234,567.89
# zh-cn: ¥ 1,234,567.89
# de: ¥ 1.234.567,89
# fr: ¥ 1 234 567,89
```

### 场景 4: RTL 语言界面调整

```python
rtl_languages = ['ar', 'he']
normal_languages = ['en', 'zh-cn', 'fr']

# 检查是否为 RTL
for lang in rtl_languages + normal_languages:
    manager = I18nFactory.get_manager(language=lang)
    if manager.is_rtl():
        print(f"{lang}: 右到左 (RTL) - 需要调整 UI")
    else:
        print(f"{lang}: 左到右 (LTR) - 正常显示")

# 输出:
# ar: 右到左 (RTL) - 需要调整 UI
# he: 右到左 (RTL) - 需要调整 UI
# en: 左到右 (LTR) - 正常显示
# zh-cn: 左到右 (LTR) - 正常显示
# fr: 左到右 (LTR) - 正常显示
```

---

## 🔍 快速查询表

### 支持的语言代码

| 代码 | 语言 | 默认货币 | 默认时区 |
|------|------|---------|---------|
| zh-cn | 中文 (简) | CNY | Asia/Shanghai |
| zh-hk | 中文 (繁) | HKD | Asia/Shanghai |
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

### 支持的货币代码

| 代码 | 名称 | 符号 | 小数位 | 汇率 (vs CNY) |
|------|------|------|--------|----------------|
| CNY | 人民币 | ¥ | 2 | 1.00 |
| USD | 美元 | $ | 2 | 0.1449 |
| EUR | 欧元 | € | 2 | 0.1340 |
| GBP | 英镑 | £ | 2 | 0.1689 |
| JPY | 日元 | ¥ | 0 | 15.00 |
| KRW | 韩元 | ₩ | 0 | 186.00 |
| INR | 印度卢比 | ₹ | 2 | 12.00 |
| RUB | 俄罗斯卢布 | ₽ | 2 | 13.00 |
| AED | 阿联酋迪拉姆 | د.إ | 2 | 0.5317 |
| AUD | 澳大利亚元 | A$ | 2 | 0.2210 |

### 支持的时区

| 地区 | 时区字符串 | UTC 偏移 | 用途 |
|------|-----------|---------|------|
| 中国 | Asia/Shanghai | UTC+8 | 商务 |
| 美国东部 | America/New_York | UTC-5 | 金融 |
| 美国西部 | America/Los_Angeles | UTC-8 | 科技 |
| 英国 | Europe/London | UTC+0 | 伦敦市场 |
| 法国 | Europe/Paris | UTC+1 | 欧洲市场 |
| 德国 | Europe/Berlin | UTC+1 | 欧洲市场 |
| 日本 | Asia/Tokyo | UTC+9 | 亚太市场 |
| 韩国 | Asia/Seoul | UTC+9 | 亚太市场 |
| 迪拜 | Asia/Dubai | UTC+4 | 中东市场 |
| 悉尼 | Australia/Sydney | UTC+11 | 太平洋市场 |

---

## ⚡ 性能优化提示

```python
# ✅ 好: 重用管理器
manager = I18nFactory.get_manager(language='en', currency='USD')
for i in range(1000):
    text = manager.translate(f'item_{i}')
    price = manager.format_currency(Decimal('99.99'), 'USD')

# ❌ 不好: 每次都创建新管理器
for i in range(1000):
    manager = I18nFactory.get_manager(language='en', currency='USD')
    text = manager.translate(f'item_{i}')
    price = manager.format_currency(Decimal('99.99'), 'USD')

# ✅ 好: 使用单例管理器
default_manager = I18nFactory.get_default_manager()
for i in range(1000):
    text = default_manager.translate(f'item_{i}')

# ✅ 好: 批量操作
manager = I18nFactory.get_manager(language='en', currency='USD')
items = [manager.format_currency(Decimal(str(price)), 'USD') for price in prices]
```

---

## 🐛 常见问题速查

### Q: 如何在 Django 视图中使用?
```python
def my_view(request):
    language = request.GET.get('language', 'en')
    currency = request.GET.get('currency', 'USD')
    
    manager = I18nFactory.get_manager(language=language, currency=currency)
    
    return JsonResponse({
        'price': manager.format_currency(Decimal('99.99'), currency),
        'date': manager.format_date(datetime.now(), 'date'),
    })
```

### Q: 如何添加新语言?
编辑 `i18n_config.py`:
```python
SUPPORTED_LANGUAGES['new_code'] = {
    'name': 'New Language',
    'native_name': 'Native Name',
    'default_currency': 'USD',
    'default_timezone': 'UTC',
}
```

### Q: 如何自定义汇率?
编辑 `i18n_config.py`:
```python
EXCHANGE_RATES = {
    'CNY': 1.0,
    'USD': 0.15,  # 修改这里
    # ...
}
```

### Q: 如何改变数字格式?
编辑 `i18n_config.py`:
```python
NUMBER_FORMATS = {
    'en': {'thousands': ',', 'decimal': '.'},
    'de': {'thousands': '.', 'decimal': ','},
    # 添加自定义格式
    'custom': {'thousands': ' ', 'decimal': ','},
}
```

---

## 📞 快速支持

- 完整文档: `LEVEL_4_TASK_4_COMPLETION_REPORT.md`
- 快速开始: `LEVEL_4_TASK_4_QUICK_START.md`
- 集成指南: `LEVEL_4_TASK_4_INTEGRATION_GUIDE.md`
- 测试文件: `apps/core/tests/test_level4_task4.py`

---

**最后更新**: 2024
**版本**: 1.0.0
**维护者**: 项目团队

