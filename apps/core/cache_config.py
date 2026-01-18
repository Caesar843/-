"""
缓存配置和优化模块

提供缓存配置管理、性能优化建议、以及缓存健康检查。
"""

import logging
from django.core.cache import cache
from django.conf import settings
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ============================================
# 缓存配置优化
# ============================================

class CacheOptimization:
    """缓存优化建议和最佳实践"""
    
    # 推荐的缓存键 TTL 值
    RECOMMENDED_TTL = {
        'user_profile': 3600,        # 用户信息：1 小时
        'product_list': 600,         # 产品列表：10 分钟
        'product_detail': 3600,      # 产品详情：1 小时
        'order_detail': 1800,        # 订单详情：30 分钟
        'statistics': 300,           # 统计数据：5 分钟
        'config': 86400,             # 配置信息：24 小时
        'session': 1800,             # 会话：30 分钟
    }
    
    # 缓存预算（预计缓存大小）
    CACHE_BUDGET = {
        'user_profile': 100000,      # 用户信息：100K
        'product_data': 500000,      # 产品数据：500K
        'session_data': 200000,      # 会话数据：200K
        'temporary': 300000,         # 临时数据：300K
    }
    
    @staticmethod
    def get_optimal_ttl(cache_type: str) -> int:
        """获取最优 TTL"""
        return CacheOptimization.RECOMMENDED_TTL.get(
            cache_type,
            300  # 默认 5 分钟
        )
    
    @staticmethod
    def check_cache_health() -> Dict[str, Any]:
        """检查缓存系统健康状况"""
        try:
            # 测试缓存连接
            test_key = "_cache_health_check"
            test_value = "healthy"
            
            cache.set(test_key, test_value, 60)
            result = cache.get(test_key)
            cache.delete(test_key)
            
            is_healthy = result == test_value
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'backend': settings.CACHES.get('default', {}).get('BACKEND'),
                'location': settings.CACHES.get('default', {}).get('LOCATION', 'N/A'),
                'message': '缓存系统正常' if is_healthy else '缓存系统异常'
            }
        except Exception as e:
            logger.error(f"缓存健康检查失败: {e}")
            return {
                'status': 'error',
                'message': f'缓存系统错误: {str(e)}'
            }


# ============================================
# 缓存配置
# ============================================

def get_cache_config() -> Dict[str, Any]:
    """
    获取推荐的缓存配置
    
    返回值包含开发和生产环境的配置示例
    """
    return {
        'development': {
            'CACHES': {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'unique-snowflake',
                    'OPTIONS': {
                        'MAX_ENTRIES': 10000,
                        'CULL_FREQUENCY': 3,  # 当满时删除 1/3 条目
                    },
                    'KEY_PREFIX': 'dev',
                    'VERSION': 1,
                    'TIMEOUT': 300,
                }
            }
        },
        'production': {
            'CACHES': {
                'default': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': 'redis://127.0.0.1:6379/1',
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                        'CONNECTION_POOL_KWARGS': {
                            'max_connections': 50,
                            'health_check_interval': 30,
                        },
                        'SOCKET_CONNECT_TIMEOUT': 5,
                        'SOCKET_TIMEOUT': 5,
                        'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                        'IGNORE_EXCEPTIONS': True,
                    },
                    'KEY_PREFIX': 'prod',
                    'VERSION': 1,
                    'TIMEOUT': 300,
                },
                # 会话缓存（独立配置）
                'session': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': 'redis://127.0.0.1:6379/2',
                    'TIMEOUT': 3600,
                },
                # 热数据缓存（高 TTL）
                'hot_data': {
                    'BACKEND': 'django_redis.cache.RedisCache',
                    'LOCATION': 'redis://127.0.0.1:6379/3',
                    'TIMEOUT': 3600,
                },
            },
            'SESSION_ENGINE': 'django_redis.sessions.SessionStore',
            'SESSION_CACHE_ALIAS': 'session',
        }
    }


# ============================================
# 缓存预热任务
# ============================================

class WarmupTasks:
    """缓存预热任务定义"""
    
    # 在应用启动时执行的预热任务
    STARTUP_WARMUP_TASKS = [
        'warmup_popular_products',
        'warmup_config_cache',
    ]
    
    # 定期执行的预热任务（Celery Beat）
    PERIODIC_WARMUP_TASKS = {
        'warmup_hourly_stats': {
            'schedule': 'crontab(minute=0)',  # 每小时
            'options': {}
        },
        'warmup_daily_cache': {
            'schedule': 'crontab(hour=2, minute=0)',  # 每天凌晨 2 点
            'options': {}
        },
        'cleanup_expired_cache': {
            'schedule': 'crontab(hour=*/6)',  # 每 6 小时
            'options': {}
        },
    }


# ============================================
# 缓存策略对比
# ============================================

CACHE_STRATEGIES = {
    'memory_cache': {
        'name': '内存缓存 (LocMemCache)',
        'pros': ['超快速', '无网络延迟'],
        'cons': ['进程独立', '内存占用大', '无法分布式'],
        'suitable_for': ['开发环境', '小规模应用'],
        'ttl_range': '1分钟 - 1小时',
    },
    'redis_cache': {
        'name': 'Redis 缓存',
        'pros': ['分布式', '高性能', '支持多种数据类型', '持久化'],
        'cons': ['需要额外服务', '网络延迟'],
        'suitable_for': ['生产环境', '分布式系统', '高并发场景'],
        'ttl_range': '1分钟 - 24小时',
    },
    'database_cache': {
        'name': '数据库缓存',
        'pros': ['数据持久化', '支持复杂查询'],
        'cons': ['性能一般', '数据库压力大'],
        'suitable_for': ['小规模应用', '特殊场景'],
        'ttl_range': '30分钟 - 7天',
    },
    'hybrid_cache': {
        'name': '混合缓存（L1+L2）',
        'pros': ['性能最优', '容错能力强'],
        'cons': ['配置复杂', '维护成本高'],
        'suitable_for': ['高并发系统', '关键业务'],
        'ttl_range': '根据分层调整',
    },
}

def get_cache_config(environment='dev'):
    """
    获取推荐的缓存配置
    
    Args:
        environment: 'dev' 或 'prod'
    
    Returns:
        缓存配置字典
    """
    if environment == 'prod':
        return {
            'backend': 'django_redis.cache.RedisCache',
            'location': 'redis://127.0.0.1:6379/1',
            'timeout': 300,
            'options': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            }
        }
    else:
        return {
            'backend': 'django.core.cache.backends.locmem.LocMemCache',
            'location': 'unique-snowflake',
            'timeout': 300,
            'options': {
                'MAX_ENTRIES': 1000,
            }
        }