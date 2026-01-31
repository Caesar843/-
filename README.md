# 商场店铺智能运营管理系统

## 项目简介
基于 Django 的商场店铺智能运营管理系统，包含店铺管理、合同管理、财务管理、运营数据、通知与备份等模块。

## 快速开始（本地）
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

访问：http://localhost:8000

## 可选：异步任务
```bash
pip install redis celery
celery -A config worker -l info
celery -A config beat -l info
```

## 主要模块
- 店铺管理（新增/编辑/导入/导出）
- 合同管理（状态流转/审批/到期提醒）
- 财务管理（账单、支付、提醒、报表）
- 运营分析（设备数据、分析看板）
- 通知与备份

## 运行说明
- 默认使用 SQLite
- 如需 PostgreSQL/MySQL，请在环境变量中配置数据库连接

## 环境变量（示例）
- DJANGO_SECRET_KEY
- DJANGO_ALLOWED_HOSTS
- DEBUG / DJANGO_DEBUG
- CORS_ALLOWED_ORIGINS
