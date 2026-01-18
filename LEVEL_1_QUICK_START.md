# 🎯 第一级任务快速开始指南

> 完成日期: 2026-01-16  
> 预期工作量: 5.5 小时  
> 实际完成时间: ✅ 已完成

## 🔗 快速链接

| 功能 | 链接 | 说明 |
|------|------|------|
| **Swagger API 文档** | http://localhost:8000/api/docs/ | 交互式 API 测试 |
| **ReDoc 文档** | http://localhost:8000/api/redoc/ | 结构化 API 文档 |
| **OpenAPI Schema** | http://localhost:8000/api/schema/ | 原始 OpenAPI 格式 |
| **Django Admin** | http://localhost:8000/admin | 管理后台 |
| **主页面** | http://localhost:8000 | 系统首页 |

---

## ✅ 1️⃣ CORS 跨域配置

### 💡 什么是 CORS？
CORS (Cross-Origin Resource Sharing) 允许前端应用从不同域名调用后端 API。

### 🔧 配置详情

**已配置的前端地址**:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Vue/React
    "http://localhost:8080",      # 备用
    "http://localhost:5173",      # Vite
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173",
]
```

### 📝 使用示例

**JavaScript 调用 API**:
```javascript
// 前端在 http://localhost:3000 调用后端 API
const response = await fetch('http://localhost:8000/api/operations/device_data/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        device_id: 'DEVICE_001',
        temperature: 25.5,
        humidity: 60,
    })
});

const data = await response.json();
console.log(data);
```

**cURL 测试**:
```bash
curl -X POST http://localhost:8000/api/operations/device_data/ \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "DEVICE_001", "temperature": 25.5}'
```

### ✅ 验证 CORS 是否正常
- ✅ 打开浏览器控制台 (F12)
- ✅ 切换到 Network 标签
- ✅ 查看 Response Headers 中是否有 `Access-Control-Allow-Origin`

---

## ✅ 2️⃣ API 文档自动生成

### 📖 访问文档

**方式 1: Swagger UI（推荐）**
```
URL: http://localhost:8000/api/docs/
功能: 
  - 可视化 API 列表
  - 在线测试 API
  - 查看参数和响应
```

**方式 2: ReDoc**
```
URL: http://localhost:8000/api/redoc/
功能:
  - 更好的可读性
  - 详细的 API 描述
  - 自动生成目录
```

**方式 3: OpenAPI Schema**
```
URL: http://localhost:8000/api/schema/
功能:
  - 原始 JSON 格式
  - 用于代码生成
  - 用于 API 管理工具
```

### 🎨 Swagger UI 功能演示

1. **查看所有 API**:
   - 点击 Swagger UI 页面查看所有可用的 endpoints
   - 已自动生成的 endpoints:
     - POST `/api/operations/device_data/` - 设备数据上传
     - PATCH `/api/operations/device/{id}/` - 更新设备状态

2. **测试 API**:
   ```
   1. 找到要测试的 API
   2. 点击 "Try it out"
   3. 输入参数
   4. 点击 "Execute"
   5. 查看响应
   ```

3. **查看响应示例**:
   - 成功响应 (200)
   - 错误响应 (400, 401, 404 等)
   - 响应格式和类型

### 📝 为 API 添加文档

**在 View 中添加文档注释**:
```python
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

class DeviceDataView(APIView):
    @extend_schema(
        summary="设备数据上传",
        description="上传设备的实时数据（温度、湿度等）",
        tags=['设备数据'],
    )
    def post(self, request):
        """上传设备数据"""
        # ... 实现代码 ...
        return APIResponse.success(data={...})
```

---

## ✅ 3️⃣ 基础日志配置

### 📝 日志文件位置
```
logs/
├── django.log        # 主日志（INFO 及以上）
└── error.log         # 错误日志（ERROR 及以上）
```

### 🔍 查看日志

**实时查看日志**:
```bash
# 查看主日志
tail -f logs/django.log

# 查看错误日志
tail -f logs/error.log

# 搜索特定内容
grep "合同" logs/django.log
grep "ERROR" logs/error.log

# 查看最后 100 行
tail -100 logs/django.log
```

### 💻 在代码中使用日志

**方式 1: 简单使用**:
```python
import logging

logger = logging.getLogger(__name__)

logger.debug('调试信息')      # 开发时使用
logger.info('重要信息')       # 记录正常操作
logger.warning('警告信息')    # 记录潜在问题
logger.error('错误信息')      # 记录异常
```

**方式 2: 带上下文**:
```python
logger.info(f'用户 {user.id} 提交合同 {contract.id}')
logger.error(f'数据库查询失败: {str(e)}')
```

**方式 3: 异常日志**:
```python
try:
    # ... 业务逻辑 ...
except Exception as e:
    logger.exception(f'处理失败: {str(e)}')  # 自动包含堆栈跟踪
```

### 📊 日志级别说明

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 开发调试 | `logger.debug('变量值: ' + str(var))` |
| INFO | 正常操作 | `logger.info('合同已保存')` |
| WARNING | 潜在问题 | `logger.warning('库存不足')` |
| ERROR | 错误事件 | `logger.error('数据库连接失败')` |

### ⚙️ 日志配置文件

配置位置: `config/settings.py` - `LOGGING` 字典

修改日志级别:
```python
# 改变 django 日志级别
'django': {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',  # 改这里
    'propagate': False,
},
```

---

## ✅ 4️⃣ 环境变量管理

### 📄 .env 文件位置
```
项目根目录/.env
```

### 🔧 配置环境变量

**编辑 `.env` 文件**:
```env
# Django 基础配置
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,*.example.com

# 数据库
DATABASE_URL=sqlite:///db.sqlite3

# Redis（可选，用于缓存和 Celery）
REDIS_URL=redis://localhost:6379/0

# Celery（可选）
CELERY_BROKER_URL=redis://localhost:6379/0

# 短信服务（可选）
SMS_PROVIDER=ALIYUN
ALIYUN_ACCESS_KEY=your_key
ALIYUN_SECRET_KEY=your_secret
```

### 📝 如何使用

**在 Python 代码中读取**:
```python
from decouple import config

# 读取字符串
debug = config('DEBUG', default=True, cast=bool)
secret_key = config('SECRET_KEY')

# 读取列表（逗号分隔）
from decouple import Csv
hosts = config('ALLOWED_HOSTS', cast=Csv())
```

### 🔒 安全性

**已配置**:
- ✅ `.env` 已添加到 `.gitignore`
- ✅ `.env` 文件不会被提交到 Git
- ✅ 每个开发者可以有不同的 `.env` 配置

**最佳实践**:
```bash
# 生产环境
DEBUG=False
SECRET_KEY=super-secret-production-key
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@host/dbname

# 开发环境
DEBUG=True
SECRET_KEY=dev-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

---

## ✅ 5️⃣ 响应格式统一

### 📋 响应格式标准

所有 API 返回以下格式:

**成功响应**:
```json
{
    "code": 0,
    "message": "操作成功",
    "data": {
        "id": 1,
        "name": "Test",
        ...
    }
}
```

**错误响应**:
```json
{
    "code": 400,
    "message": "参数校验失败",
    "data": {
        "errors": {
            "field_name": ["error message"]
        }
    }
}
```

### 🔧 在视图中使用

**基本用法**:
```python
from rest_framework.views import APIView
from apps.core.response import APIResponse

class MyView(APIView):
    def get(self, request):
        return APIResponse.success(
            data={'message': 'Hello World'},
            message='获取成功'
        )
```

**处理错误**:
```python
def get(self, request, id):
    try:
        obj = MyModel.objects.get(id=id)
        return APIResponse.success(data=obj)
    except MyModel.DoesNotExist:
        return APIResponse.not_found('资源不存在')
    except Exception as e:
        return APIResponse.server_error('内部错误')
```

**创建资源**:
```python
def post(self, request):
    serializer = MySerializer(data=request.data)
    if not serializer.is_valid():
        return APIResponse.handle_serializer_errors(serializer)
    
    serializer.save()
    return APIResponse.created(
        data=serializer.data,
        message='创建成功'
    )
```

**分页响应**:
```python
def get(self, request):
    items = MyModel.objects.all()
    page = request.query_params.get('page', 1)
    
    return APIResponse.paginated(
        queryset_or_items=items,
        page_number=page,
        page_size=20,
        serializer_class=MySerializer
    )
```

### 📚 可用方法列表

| 方法 | HTTP 状态 | 用途 |
|------|---------|------|
| `success()` | 200 | 返回成功响应 |
| `created()` | 201 | 资源创建成功 |
| `error()` | 400 | 通用错误 |
| `bad_request()` | 400 | 请求参数错误 |
| `unauthorized()` | 401 | 需要认证 |
| `forbidden()` | 403 | 无权限 |
| `not_found()` | 404 | 资源不存在 |
| `conflict()` | 409 | 资源冲突 |
| `server_error()` | 500 | 服务器错误 |
| `paginated()` | 200 | 分页响应 |
| `list_response()` | 200 | 列表响应 |
| `validation_error()` | 400 | 验证错误 |

---

## 🎯 下一步

### 📌 第 2 级任务（简易，3-7 天）
```
[ ] Sentry 错误追踪集成        (1 天)
[ ] 健康检查端点               (1 天)
[ ] 数据库备份脚本             (2 天)
[ ] Django 安全加强            (2 天)
[ ] 异常处理中间件             (2 天)
```

### 📊 项目进度

```
第 1 级: ✅✅✅✅✅ 100% 完成
第 2 级: ⏳ 计划中
第 3 级: ⏳ 计划中
第 4 级: ⏳ 计划中
第 5 级: ⏳ 计划中
第 6 级: ⏳ 计划中
```

---

## 📞 问题排查

### 🔧 CORS 错误
```
错误: CORS policy: No 'Access-Control-Allow-Origin' header
原因: 前端域名不在 CORS_ALLOWED_ORIGINS 中
解决: 修改 settings.py 中的 CORS_ALLOWED_ORIGINS
```

### 📖 API 文档无法访问
```
错误: 404 Not Found
原因: drf-spectacular 未安装或 URL 配置错误
解决: pip install drf-spectacular
```

### 📝 日志文件不存在
```
错误: FileNotFoundError
原因: logs 目录不存在
解决: 自动创建（settings.py 中已配置）
```

### 🔐 环境变量未读取
```
错误: decouple.UndefinedValueError
原因: 未创建 .env 文件或变量未定义
解决: 创建 .env 文件并定义所需变量
```

---

## 📚 推荐阅读

- [Django CORS](https://github.com/adamchainz/django-cors-headers)
- [DRF Spectacular](https://drf-spectacular.readthedocs.io/)
- [Python Decouple](https://github.com/henriquebastos/python-decouple)
- [Django Logging](https://docs.djangoproject.com/en/6.0/topics/logging/)

---

**✨ 祝贺！第 1 级任务已 100% 完成！**
