<!-- Level 4 Task 3 全文搜索系统快速开始指南 -->

# Level 4 Task 3: 全文搜索系统

## 📋 概述

本任务实现一个完整的全文搜索系统，支持以下功能：
- 🔍 多后端支持（Whoosh/Elasticsearch）
- 📝 多字段搜索和高级查询
- 🎯 分面导航和搜索建议
- ⚡ 自动完成和缓存优化
- 📊 搜索统计和性能分析

## ✨ 核心功能

### 1. 搜索后端

**Whoosh 后端**（轻量级）
- 纯 Python 实现
- 无需外部依赖
- 适合小到中等规模数据
- 文件系统存储

**Elasticsearch 后端**（企业级）
- 分布式搜索引擎
- 高性能和可扩展性
- 支持集群部署
- 适合大规模数据

### 2. 搜索功能

**基础搜索**
```python
search_manager.search('laptop', limit=50, page=1)
```

**高级查询**
```python
search_manager.advanced_search({
    'keywords': 'laptop',
    'category': 'electronics',
    'price_min': 500,
    'price_max': 2000,
})
```

**自动完成**
```python
suggestions = search_manager.autocomplete('lap', limit=10)
```

**搜索建议**
```python
suggestions = search_manager.get_suggestions('laptop')
```

### 3. 分面导航

按分类、标签、价格等分面过滤结果

```python
facets = get_facets_for_model('product')
```

### 4. 索引管理

- 自动索引更新
- 手动重建索引
- 索引状态监控
- 性能优化

## 🚀 快速开始

### 1. 安装依赖

```bash
# Whoosh（推荐用于开发）
pip install whoosh

# Elasticsearch（可选，用于生产）
pip install elasticsearch
```

### 2. 配置搜索后端

在 `config/settings.py` 中：

```python
# 搜索后端配置
SEARCH_BACKEND = 'whoosh'  # 或 'elasticsearch'

# Whoosh 配置
WHOOSH_INDEX_DIR = os.path.join(BASE_DIR, 'indexes')

# Elasticsearch 配置
ELASTICSEARCH_HOST = 'localhost'
ELASTICSEARCH_PORT = 9200
```

### 3. 初始化搜索管理器

```python
from apps.core.search_manager import get_search_manager

# 获取搜索管理器
search_manager = get_search_manager()

# 检查索引状态
status = search_manager.get_index_status()
```

### 4. 索引文档

```python
# 索引单个文档
search_manager.index_document('doc-123', {
    'title': '产品名称',
    'description': '产品描述',
    'category': 'electronics',
    'tags': 'new,featured',
    'url': '/products/123',
})
```

### 5. 执行搜索

```python
# 基础搜索
result = search_manager.search('laptop', limit=50, page=1)

# 遍历结果
for item in result['results']:
    print(f"{item['title']} - {item['score']:.2f}")
```

## 📖 API 使用

### REST API 端点

```
GET    /api/search/search/              - 基础搜索
POST   /api/search/search/advanced/     - 高级搜索
GET    /api/search/search/autocomplete/ - 自动完成
GET    /api/search/search/suggestions/  - 搜索建议
GET    /api/search/search/facets/       - 分面导航
GET    /api/search/search/metrics/      - 搜索指标
GET    /api/search/search/models/       - 可搜索模型
GET    /api/search/search-index/status/ - 索引状态
POST   /api/search/search-index/rebuild/- 重建索引
```

### 调用示例

**基础搜索**
```bash
curl "http://localhost:8000/api/search/search/?query=laptop&limit=50&page=1"
```

**自动完成**
```bash
curl "http://localhost:8000/api/search/search/autocomplete/?prefix=lap&limit=10"
```

**高级搜索**
```bash
curl -X POST http://localhost:8000/api/search/search/advanced/ \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "laptop",
    "category": "electronics",
    "price_min": 500,
    "price_max": 2000
  }'
```

**获取指标**
```bash
curl "http://localhost:8000/api/search/search/metrics/"
```

## 🛠️ CLI 工具

### 管理命令

```bash
# 列出可搜索模型
python manage.py search_manage --list-indexes

# 检查索引状态
python manage.py search_manage --index-status

# 重建索引
python manage.py search_manage --rebuild-index

# 执行搜索
python manage.py search_manage --search "laptop" --limit 50

# 高级搜索
python manage.py search_manage --advanced-search '{"keywords":"laptop","category":"electronics"}'

# 自动完成
python manage.py search_manage --autocomplete "lap"

# 获取建议
python manage.py search_manage --suggestions "laptop"

# 显示指标
python manage.py search_manage --metrics

# 测试连接
python manage.py search_manage --test
```

## 🧪 运行测试

```bash
# 运行所有搜索测试
python manage.py test apps.core.tests.test_level4_task3

# 运行特定测试类
python manage.py test apps.core.tests.test_level4_task3.SearchManagerTests

# 运行特定测试
python manage.py test apps.core.tests.test_level4_task3.SearchManagerTests.test_search_basic

# 显示详细输出
python manage.py test apps.core.tests.test_level4_task3 -v 2
```

**测试覆盖**：
- ✅ 11 个搜索管理器测试
- ✅ 6 个 Whoosh 后端测试
- ✅ 3 个配置测试
- ✅ 11 个 API 接口测试
- ✅ 4 个集成测试
- ✅ 2 个性能测试

**总计**: **37 个测试用例**

## 📝 配置详解

### 搜索策略

在 `search_config.py` 中定义搜索策略：

```python
SEARCH_STRATEGIES = {
    'basic': {
        'type': 'basic',
        'fields': ['title', 'description', 'content'],
    },
    'advanced': {
        'type': 'advanced',
        'operators': ['AND', 'OR', 'NOT'],
    },
    'prefix': {
        'type': 'prefix',
        'min_length': 2,
    },
}
```

### 可搜索模型

定义哪些模型可被索引和搜索：

```python
SEARCHABLE_MODELS = {
    'product': {
        'model': 'store.Product',
        'fields': ['name', 'description', 'category', 'tags'],
        'enabled': True,
    },
    'article': {
        'model': 'core.Article',
        'fields': ['title', 'content', 'category'],
        'enabled': True,
    },
}
```

### 分面配置

为模型定义分面：

```python
FACETS_CONFIG = {
    'product': {
        'category': {'type': 'term', 'limit': 10},
        'price': {'type': 'range', 'ranges': [...]},
        'rating': {'type': 'range', 'ranges': [...]},
    },
}
```

### 排序和相关性

```python
RANKING_CONFIG = {
    'field_weights': {
        'title': 2.0,
        'description': 1.5,
        'tags': 1.0,
    },
    'recency_boost': {
        'enabled': True,
        'max_age_days': 30,
        'boost_factor': 1.5,
    },
}
```

## 🔍 搜索示例

### Python API 示例

```python
from apps.core.search_manager import get_search_manager

search_manager = get_search_manager()

# 基础搜索
results = search_manager.search('laptop')
print(f"找到 {results['total']} 个结果")

for item in results['results']:
    print(f"- {item['title']} ({item['score']:.2f})")

# 高级搜索
adv_results = search_manager.advanced_search({
    'keywords': 'laptop',
    'category': 'electronics',
})

# 自动完成
suggestions = search_manager.autocomplete('lap')
print(f"建议: {suggestions}")

# 获取指标
metrics = search_manager.get_search_metrics()
print(f"总搜索数: {metrics['total_searches']}")
```

## 🎯 集成场景

### 场景 1: 产品搜索

```python
# 索引产品
product_data = {
    'title': 'MacBook Pro 2024',
    'description': '高性能笔记本电脑',
    'category': 'electronics',
    'tags': 'laptop,apple,new',
    'price': 1999,
}

search_manager.index_document('prod-123', product_data)

# 搜索
results = search_manager.search('MacBook')
```

### 场景 2: 文章搜索

```python
# 索引文章
article_data = {
    'title': 'Python 最佳实践',
    'content': '...',
    'category': 'programming',
    'tags': 'python,coding,tutorial',
}

search_manager.index_document('article-456', article_data)

# 搜索
results = search_manager.search('Python')
```

### 场景 3: 前缀搜索

```python
# 在搜索框中自动完成
prefix = 'mac'
suggestions = search_manager.autocomplete(prefix)
# 返回: ['MacBook', 'Mac Mini', 'Mac Studio']
```

## ⚙️ 高级配置

### 启用 Elasticsearch

```python
# settings.py
SEARCH_BACKEND = 'elasticsearch'

ELASTICSEARCH_CONFIG = {
    'host': 'elasticsearch.example.com',
    'port': 9200,
}
```

### 自定义分析器

```python
# 在 Elasticsearch 配置中
'analysis': {
    'analyzer': {
        'custom_analyzer': {
            'type': 'custom',
            'tokenizer': 'standard',
            'filter': ['lowercase', 'stop'],
        },
    },
}
```

### 性能优化

```python
# 启用缓存
SEARCH_CACHE_CONFIG = {
    'enabled': True,
    'ttl': 300,  # 5 分钟
}

# 批量索引
for doc in large_document_list:
    search_manager.index_document(doc['id'], doc)
```

## 🐛 常见问题

### 问题 1: 索引文件过大

**解决**: 定期重建索引或使用 Elasticsearch

```bash
python manage.py search_manage --rebuild-index
```

### 问题 2: 搜索速度慢

**解决**: 
- 启用缓存
- 优化字段权重
- 使用 Elasticsearch

### 问题 3: 搜索不到最新文档

**解决**: 确保文档被正确索引

```python
# 检查索引状态
status = search_manager.get_index_status()
print(f"文档数: {status['document_count']}")
```

## 📊 监控和日志

### 获取搜索指标

```python
metrics = search_manager.get_search_metrics()
print(f"总搜索数: {metrics['total_searches']}")
print(f"热门查询: {metrics['top_queries']}")
```

### 查看日志

```bash
tail -f logs/search.log
```

## 📚 最佳实践

1. **定期重建索引**: 每周或每月重建一次
2. **使用缓存**: 减少重复查询的开销
3. **优化字段权重**: 根据业务逻辑调整相关性
4. **监控性能**: 跟踪搜索时间和缓存命中率
5. **提供建议**: 使用自动完成改善用户体验

## 🆘 支持和维护

- 查看日志: `logs/search.log`
- 运行诊断: `python diagnose.py`
- 测试系统: `python manage.py search_manage --test`

## ✅ 验证检查清单

- [ ] 安装了搜索后端依赖
- [ ] 配置了搜索后端
- [ ] 初始化了搜索管理器
- [ ] 索引了测试文档
- [ ] API 端点可以访问
- [ ] CLI 命令正常工作
- [ ] 所有 37 个测试通过
- [ ] 性能指标满足要求

完成以上步骤后，您已经拥有一个完整的全文搜索系统！
