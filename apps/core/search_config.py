"""
全文搜索配置管理
定义搜索引擎配置、索引配置和搜索策略
"""

import os
from typing import Dict, List, Any, Optional

# ============================================================================
# 搜索引擎配置
# ============================================================================

# 搜索后端选择
SEARCH_BACKEND = os.environ.get('SEARCH_BACKEND', 'whoosh')  # whoosh | elasticsearch

# Whoosh 配置
WHOOSH_CONFIG = {
    'index_dir': os.path.join(os.path.dirname(__file__), '../../indexes'),
    'default_schema': {
        'fields': {
            'id': {'type': 'ID', 'stored': True},
            'model': {'type': 'ID', 'stored': True},
            'title': {'type': 'TEXT', 'stored': True, 'field_boost': 2.0},
            'content': {'type': 'TEXT', 'stored': False},
            'description': {'type': 'TEXT', 'stored': True},
            'category': {'type': 'KEYWORD', 'stored': True},
            'tags': {'type': 'KEYWORD', 'stored': True},
            'url': {'type': 'TEXT', 'stored': True},
            'is_published': {'type': 'KEYWORD', 'stored': True},
            'created_at': {'type': 'DATETIME', 'stored': True},
            'updated_at': {'type': 'DATETIME', 'stored': True},
        }
    },
}

# Elasticsearch 配置
ELASTICSEARCH_CONFIG = {
    'host': os.environ.get('ELASTICSEARCH_HOST', 'localhost'),
    'port': int(os.environ.get('ELASTICSEARCH_PORT', 9200)),
    'index_name': 'shop_search',
    'settings': {
        'number_of_shards': 1,
        'number_of_replicas': 0,
        'analysis': {
            'analyzer': {
                'ik_max_word': {
                    'type': 'custom',
                    'tokenizer': 'ik_max_word',
                    'filter': ['lowercase'],
                },
            },
        },
    },
    'mappings': {
        'properties': {
            'id': {'type': 'keyword'},
            'model': {'type': 'keyword'},
            'title': {
                'type': 'text',
                'analyzer': 'ik_max_word',
                'fields': {
                    'keyword': {'type': 'keyword'},
                },
            },
            'content': {
                'type': 'text',
                'analyzer': 'ik_max_word',
            },
            'description': {
                'type': 'text',
                'analyzer': 'ik_max_word',
            },
            'category': {'type': 'keyword'},
            'tags': {'type': 'keyword'},
            'url': {'type': 'keyword'},
            'is_published': {'type': 'keyword'},
            'created_at': {'type': 'date'},
            'updated_at': {'type': 'date'},
        },
    },
}

# ============================================================================
# 可搜索模型配置
# ============================================================================

SEARCHABLE_MODELS = {
    'product': {
        'model': 'store.Product',
        'fields': ['name', 'description', 'category', 'tags'],
        'boost': 2.0,
        'enabled': True,
    },
    'order': {
        'model': 'store.Order',
        'fields': ['order_id', 'customer_name', 'items'],
        'boost': 1.0,
        'enabled': True,
    },
    'article': {
        'model': 'core.Article',
        'fields': ['title', 'content', 'category'],
        'boost': 1.5,
        'enabled': True,
    },
    'user': {
        'model': 'user_management.User',
        'fields': ['username', 'email', 'first_name', 'last_name'],
        'boost': 0.5,
        'enabled': False,  # 隐私保护
    },
}

# ============================================================================
# 搜索策略配置
# ============================================================================

SEARCH_STRATEGIES = {
    # 基础搜索策略
    'basic': {
        'type': 'basic',
        'fields': ['title', 'description', 'content'],
        'min_length': 1,
        'max_length': 500,
    },
    
    # 高级搜索策略
    'advanced': {
        'type': 'advanced',
        'supported_fields': [
            'title', 'content', 'description', 'category',
            'tags', 'created_at', 'price_min', 'price_max',
        ],
        'operators': ['AND', 'OR', 'NOT', 'RANGE'],
    },
    
    # 前缀搜索（自动完成）
    'prefix': {
        'type': 'prefix',
        'fields': ['title', 'description'],
        'min_length': 2,
        'max_results': 10,
    },
    
    # 模糊搜索
    'fuzzy': {
        'type': 'fuzzy',
        'fields': ['title', 'description'],
        'fuzziness': 1,
        'prefix_length': 0,
    },
}

# ============================================================================
# 分面导航配置
# ============================================================================

FACETS_CONFIG = {
    'product': {
        'category': {
            'type': 'term',
            'limit': 10,
        },
        'tags': {
            'type': 'term',
            'limit': 20,
        },
        'price': {
            'type': 'range',
            'ranges': [
                {'name': '低于 $100', 'from': 0, 'to': 100},
                {'name': '$100-$500', 'from': 100, 'to': 500},
                {'name': '$500-$1000', 'from': 500, 'to': 1000},
                {'name': '超过 $1000', 'from': 1000},
            ],
        },
        'rating': {
            'type': 'range',
            'ranges': [
                {'name': '5 星', 'from': 5, 'to': 5},
                {'name': '4+ 星', 'from': 4, 'to': 5},
                {'name': '3+ 星', 'from': 3, 'to': 5},
            ],
        },
    },
    'article': {
        'category': {
            'type': 'term',
            'limit': 10,
        },
        'date': {
            'type': 'date_range',
            'ranges': [
                {'name': '过去 7 天', 'days': 7},
                {'name': '过去 30 天', 'days': 30},
                {'name': '过去 90 天', 'days': 90},
            ],
        },
    },
}

# ============================================================================
# 排序和相关性配置
# ============================================================================

RANKING_CONFIG = {
    # 字段权重
    'field_weights': {
        'title': 2.0,
        'description': 1.5,
        'tags': 1.0,
        'content': 0.5,
    },
    
    # 新近度权重 (越新越高分)
    'recency_boost': {
        'enabled': True,
        'max_age_days': 30,
        'boost_factor': 1.5,
    },
    
    # 热度权重 (点击量/浏览量)
    'popularity_boost': {
        'enabled': True,
        'field': 'view_count',
        'max_boost': 2.0,
    },
    
    # 默认排序
    'default_sort': [
        {'_score': {'order': 'desc'}},  # 相关性排序
        {'created_at': {'order': 'desc'}},  # 按创建时间
    ],
}

# ============================================================================
# 搜索缓存配置
# ============================================================================

SEARCH_CACHE_CONFIG = {
    'enabled': True,
    'ttl': 300,  # 5 分钟
    'max_size': 1000,  # 最多缓存 1000 个查询
    'cache_backend': 'default',  # Django 缓存后端
}

# ============================================================================
# 搜索监控和日志配置
# ============================================================================

SEARCH_MONITORING_CONFIG = {
    'enabled': True,
    'log_searches': True,
    'log_errors': True,
    'performance_threshold': 1000,  # ms，超过此值记录性能警告
    'statistics_retention': 2592000,  # 30 天
}

# ============================================================================
# 同义词和拼写纠正配置
# ============================================================================

SYNONYMS = {
    'laptop': ['computer', 'notebook', 'device'],
    'phone': ['mobile', 'smartphone', 'device'],
    'buy': ['purchase', 'order', 'checkout'],
}

SPELLING_CORRECTIONS = {
    'lapto': 'laptop',
    'phon': 'phone',
    'prodcut': 'product',
}

# ============================================================================
# 搜索分析配置
# ============================================================================

SEARCH_ANALYSIS_CONFIG = {
    'enabled': True,
    'track_queries': True,
    'track_clicks': True,
    'track_impressions': True,
    'analysis_retention': 2592000,  # 30 天
}

# ============================================================================
# 索引更新配置
# ============================================================================

INDEX_UPDATE_CONFIG = {
    'auto_update': True,
    'update_interval': 300,  # 5 分钟自动更新一次
    'batch_size': 100,  # 批量更新的数量
    'rebuild_schedule': '0 2 * * 0',  # 每周日凌晨 2 点重建索引
}

# ============================================================================
# 搜索权限配置
# ============================================================================

SEARCH_PERMISSIONS = {
    'public': {
        'models': ['product', 'article'],
        'fields': ['title', 'description', 'category', 'tags'],
    },
    'authenticated': {
        'models': ['product', 'article', 'order'],
        'fields': ['title', 'description', 'category', 'tags', 'price', 'status'],
    },
    'admin': {
        'models': ['product', 'article', 'order', 'user'],
        'fields': '*',  # 所有字段
    },
}

# ============================================================================
# 搜索结果过滤配置
# ============================================================================

SEARCH_RESULT_FILTERS = {
    'published_only': True,
    'exclude_archived': True,
    'exclude_deleted': True,
    'check_permissions': True,
}

# ============================================================================
# 帮助函数
# ============================================================================

def get_searchable_model_config(model_key: str) -> Dict[str, Any]:
    """获取可搜索模型配置"""
    return SEARCHABLE_MODELS.get(model_key, {})


def get_facets_for_model(model: str) -> Dict[str, Any]:
    """获取模型的分面配置"""
    return FACETS_CONFIG.get(model, {})


def get_search_strategy(strategy: str) -> Dict[str, Any]:
    """获取搜索策略配置"""
    return SEARCH_STRATEGIES.get(strategy, SEARCH_STRATEGIES['basic'])


def get_field_boost(field: str) -> float:
    """获取字段权重"""
    return RANKING_CONFIG['field_weights'].get(field, 1.0)


def is_model_searchable(model_key: str) -> bool:
    """检查模型是否可搜索"""
    config = get_searchable_model_config(model_key)
    return config.get('enabled', False)


def get_enabled_searchable_models() -> List[str]:
    """获取所有已启用的可搜索模型"""
    return [
        key for key, config in SEARCHABLE_MODELS.items()
        if config.get('enabled', False)
    ]
