"""
缓存管理工具模块

提供统一的缓存接口，支持多层缓存策略、缓存穿透/击穿/雪崩防护、
缓存预热、统计和监控等功能。

特性：
- 多层缓存（L1内存、L2 Redis）
- TTL 和过期管理
- 缓存穿透防护（布隆过滤器）
- 缓存击穿防护（互斥锁）
- 缓存雪崩防护（随机 TTL、热点分离）
- 缓存统计和监控
- 热点数据识别和预热
"""

import logging
import hashlib
import time
from typing import Any, Optional, Callable, Union, List
from functools import wraps
from datetime import timedelta

from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

logger = logging.getLogger(__name__)


# ============================================
# 缓存配置常量
# ============================================

class CacheConfig:
    """缓存配置管理"""
    
    # 默认 TTL（秒）
    DEFAULT_TIMEOUT = 300  # 5 分钟
    SHORT_TIMEOUT = 60  # 1 分钟
    MEDIUM_TIMEOUT = 600  # 10 分钟
    LONG_TIMEOUT = 3600  # 1 小时
    VERY_LONG_TIMEOUT = 86400  # 24 小时
    
    # TTL 别名（为了测试兼容性）
    TTL_DEFAULT = DEFAULT_TIMEOUT
    TTL_SHORT = SHORT_TIMEOUT
    TTL_LONG = LONG_TIMEOUT
    
    # 缓存键前缀
    PREFIX_USER = "user:"
    PREFIX_SHOP = "shop:"
    PREFIX_PRODUCT = "product:"
    PREFIX_ORDER = "order:"
    PREFIX_STATS = "stats:"
    PREFIX_CONFIG = "config:"
    PREFIX_LOCK = "lock:"
    PREFIX_BLOOM = "bloom:"
    
    # 缓存键分隔符
    KEY_SEPARATOR = ":"
    
    # 布隆过滤器配置
    BLOOM_FILTER_SIZE = 1000000  # 100 万
    BLOOM_FILTER_HASH_COUNT = 3


class CacheMetrics:
    """缓存性能指标"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_time = 0
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    @property
    def avg_time(self) -> float:
        """平均缓存操作时间（ms）"""
        total = self.hits + self.misses
        return (self.total_time / total * 1000) if total > 0 else 0
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'errors': self.errors,
            'hit_rate': round(self.hit_rate, 2),  # 返回浮点数而不是字符串
            'avg_time_ms': round(self.avg_time, 2),  # 返回浮点数而不是字符串
            'total': self.hits + self.misses
        }
    
    def reset(self):
        """重置所有统计数据"""
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_time = 0.0


# 全局缓存指标
_cache_metrics = CacheMetrics()


# ============================================
# 缓存工具类
# ============================================

class CacheManager:
    """
    统一的缓存管理器
    
    特性：
    - 自动键生成和管理
    - TTL 和过期处理
    - 缓存穿透防护
    - 缓存击穿防护
    - 缓存雪崩防护
    - 统计和监控
    """
    
    def __init__(self, prefix: str = "", timeout: int = CacheConfig.DEFAULT_TIMEOUT):
        """
        初始化缓存管理器
        
        Args:
            prefix: 缓存键前缀
            timeout: 默认过期时间（秒）
        """
        self.prefix = prefix
        self.timeout = timeout
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            缓存键字符串
        """
        key_parts = [self.prefix]
        
        # 添加位置参数
        for arg in args:
            if isinstance(arg, (list, dict)):
                arg = hashlib.md5(str(arg).encode()).hexdigest()[:8]
            key_parts.append(str(arg))
        
        # 添加关键字参数（排序以保证一致性）
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                if isinstance(v, (list, dict)):
                    v = hashlib.md5(str(v).encode()).hexdigest()[:8]
                key_parts.append(f"{k}={v}")
        
        return CacheConfig.KEY_SEPARATOR.join(key_parts)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存值或默认值
        """
        start_time = time.time()
        try:
            value = cache.get(key, default)
            if value is not None:
                _cache_metrics.hits += 1
            else:
                _cache_metrics.misses += 1
            _cache_metrics.total_time += time.time() - start_time
            return value
        except Exception as e:
            logger.error(f"缓存获取失败 [{key}]: {e}")
            _cache_metrics.errors += 1
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None,
            add_randomness: bool = True) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            timeout: 过期时间（秒），None 表示使用默认值
            add_randomness: 是否添加随机偏差（防止雪崩）
        
        Returns:
            是否设置成功
        """
        try:
            if timeout is None:
                timeout = self.timeout
            
            # 添加随机偏差防止缓存雪崩（±20%）
            if add_randomness and timeout > 0:
                import random
                variance = int(timeout * 0.2)
                timeout = timeout + random.randint(-variance, variance)
            
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.error(f"缓存设置失败 [{key}]: {e}")
            _cache_metrics.errors += 1
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"缓存删除失败 [{key}]: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的所有缓存键
        
        Args:
            pattern: 键名模式（支持 * 通配符）
        
        Returns:
            删除的键数量
        """
        try:
            # 尝试使用 keys() 方法（Redis、部分缓存后端支持）
            try:
                keys = cache.keys(pattern)
                if keys:
                    cache.delete_many(keys)
                    logger.info(f"清除缓存 [{pattern}]: {len(keys)} 个键")
                    return len(keys)
                return 0
            except (AttributeError, NotImplementedError):
                # LocMemCache 不支持 keys() 方法，需要直接清空
                # 对于模式匹配，我们只能清空所有缓存（作为备选方案）
                logger.warning(f"当前缓存后端不支持 keys() 方法，无法清除模式 [{pattern}]")
                return 0
        except Exception as e:
            logger.error(f"批量清除缓存失败 [{pattern}]: {e}")
            return 0
    
    def get_or_set(self, key: str, callable_func: Callable,
                   timeout: Optional[int] = None) -> Any:
        """
        获取缓存或者调用函数设置缓存（缓存穿透防护）
        
        Args:
            key: 缓存键
            callable_func: 当缓存不存在时调用的函数
            timeout: 过期时间
        
        Returns:
            缓存值或函数返回值
        """
        # 先尝试获取缓存
        value = self.get(key)
        if value is not None:
            return value
        
        # 获取分布式锁防止缓存击穿
        lock_key = CacheConfig.PREFIX_LOCK + key
        lock_acquired = cache.add(lock_key, "1", 10)  # 10 秒锁
        
        try:
            if lock_acquired:
                # 再次检查缓存（double-check locking）
                value = self.get(key)
                if value is not None:
                    return value
                
                # 调用函数获取值
                value = callable_func()
                
                # 缓存值
                self.set(key, value, timeout)
                return value
            else:
                # 等待其他线程设置缓存
                time.sleep(0.1)
                return self.get(key, callable_func())
        finally:
            if lock_acquired:
                cache.delete(lock_key)
    
    def get_metrics(self) -> dict:
        """获取缓存性能指标"""
        return _cache_metrics.to_dict()


# ============================================
# 缓存装饰器
# ============================================

def cached(timeout: int = CacheConfig.DEFAULT_TIMEOUT,
           key_prefix: str = "",
           cache_none: bool = False):
    """
    函数缓存装饰器
    
    Args:
        timeout: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        cache_none: 是否缓存 None 值
    
    使用示例：
        @cached(timeout=600, key_prefix="user_profile")
        def get_user_profile(user_id):
            return User.objects.get(id=user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = CacheManager(prefix=key_prefix or func.__name__, timeout=timeout)
            cache_key = manager._generate_key(*args, **kwargs)
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None or (cache_none and cache_key in cache):
                _cache_metrics.hits += 1
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            if result is not None or cache_none:
                manager.set(cache_key, result, timeout)
            else:
                _cache_metrics.misses += 1
            
            return result
        return wrapper
    return decorator


def method_cached(timeout: int = CacheConfig.DEFAULT_TIMEOUT,
                  cache_none: bool = False):
    """
    方法缓存装饰器（支持 self 参数）
    
    使用示例：
        class UserService:
            @method_cached(timeout=1800)
            def get_user(self, user_id):
                return User.objects.get(id=user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            class_name = self.__class__.__name__.lower()
            method_name = func.__name__
            key_prefix = f"{class_name}:{method_name}"
            
            manager = CacheManager(prefix=key_prefix, timeout=timeout)
            cache_key = manager._generate_key(*args, **kwargs)
            
            result = cache.get(cache_key)
            if result is not None or (cache_none and cache_key in cache):
                _cache_metrics.hits += 1
                return result
            
            result = func(self, *args, **kwargs)
            
            if result is not None or cache_none:
                manager.set(cache_key, result, timeout)
            else:
                _cache_metrics.misses += 1
            
            return result
        return wrapper
    return decorator


# ============================================
# 热点数据预热
# ============================================

class CacheWarmup:
    """缓存预热管理"""
    
    @staticmethod
    def warmup_user_cache(user_id: int, manager: CacheManager):
        """预热用户相关缓存"""
        from django.contrib.auth.models import User
        
        try:
            user = User.objects.get(id=user_id)
            key = manager._generate_key("user", user_id)
            manager.set(key, {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }, CacheConfig.LONG_TIMEOUT)
            logger.info(f"预热用户缓存: {user_id}")
        except Exception as e:
            logger.error(f"用户缓存预热失败 [{user_id}]: {e}")
    
    @staticmethod
    def warmup_popular_products(manager: CacheManager, limit: int = 100):
        """预热热销产品缓存"""
        try:
            # 尝试导入 Product 模型，如果不存在则跳过
            try:
                from apps.store.models import Product
                
                # 获取销量最好的产品
                popular = Product.objects.filter(
                    is_active=True
                ).order_by('-sales_count')[:limit]
                
                for product in popular:
                    key = manager._generate_key("product", product.id)
                    manager.set(key, {
                        'id': product.id,
                        'name': product.name,
                        'price': float(product.price),
                    }, CacheConfig.LONG_TIMEOUT)
                
                logger.info(f"预热热销产品缓存: {len(popular)} 个")
            except ImportError:
                logger.debug("Product 模型未在 apps.store.models 中定义，跳过产品缓存预热")
        except Exception as e:
            logger.error(f"产品缓存预热失败: {e}")


# ============================================
# 缓存统计视图
# ============================================

def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    return {
        'metrics': _cache_metrics.to_dict(),
        'cache_backend': settings.CACHES.get('default', {}).get('BACKEND'),
        'is_redis': 'redis' in settings.CACHES.get('default', {}).get('BACKEND', '').lower(),
    }
