"""
缓存装饰器模块

为 Django 视图和 DRF 提供缓存装饰器，支持：
- 函数和方法缓存
- 视图缓存（自动处理认证）
- 列表视图缓存（支持分页）
- 条件缓存（基于查询参数）
"""

from functools import wraps
from django.core.cache import cache
from django.http import HttpRequest
from rest_framework.response import Response
import logging
import hashlib

logger = logging.getLogger(__name__)


def _get_cache_key_from_request(request: HttpRequest, view_name: str, prefix: str = '') -> str:
    """
    从请求对象生成缓存键
    
    参数：
        request: Django HTTP 请求对象
        view_name: 视图名称或功能标识
        prefix: 缓存键前缀（默认空）
    
    返回：
        缓存键字符串
    """
    # 获取用户标识
    user_id = request.user.id if request.user.is_authenticated else 'anonymous'
    
    # 获取查询参数哈希
    query_string = request.GET.urlencode() if request.GET else ''
    query_hash = hashlib.md5(query_string.encode()).hexdigest()[:8]
    
    # 生成缓存键
    cache_key_parts = [prefix or 'view', view_name, f'user_{user_id}', f'query_{query_hash}']
    cache_key = ':'.join(filter(None, cache_key_parts))
    
    return cache_key


def cache_view(timeout: int = 300, key_prefix: str = '', exclude_params: list = None):
    """
    视图级缓存装饰器
    
    为 DRF 视图缓存响应数据。仅缓存 GET 请求，
    使用用户 ID 和查询参数作为缓存键的一部分。
    
    使用方式：
        @cache_view(timeout=600, key_prefix='user_list')
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    
    参数：
        timeout: 缓存超时时间（秒），默认 300
        key_prefix: 缓存键前缀，默认使用视图名称
        exclude_params: 不参与缓存键生成的查询参数列表
    
    返回：
        装饰后的视图函数
    """
    exclude_params = exclude_params or ['page', 'limit']
    
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 只缓存 GET 请求
            if request.method != 'GET':
                return func(self, request, *args, **kwargs)
            
            # 排除指定的查询参数
            filtered_get = request.GET.copy()
            for param in exclude_params:
                filtered_get.pop(param, None)
            request.GET = filtered_get
            
            # 生成缓存键
            cache_key = _get_cache_key_from_request(
                request,
                key_prefix or func.__name__,
                prefix='cache_view'
            )
            
            # 尝试从缓存获取
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f'缓存命中: {cache_key}')
                return cached_response
            
            # 调用原函数
            response = func(self, request, *args, **kwargs)
            
            # 仅缓存成功的响应
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                cache.set(cache_key, response, timeout)
                logger.debug(f'缓存设置: {cache_key} (超时: {timeout}秒)')
            
            return response
        
        return wrapper
    return decorator


def cache_list_view(timeout: int = 300, key_prefix: str = ''):
    """
    列表视图缓存装饰器（支持分页）
    
    为列表类视图缓存响应。与 cache_view 相同，
    但专为列表视图优化，自动处理分页参数。
    
    使用方式：
        @cache_list_view(timeout=300)
        def list(self, request, *args, **kwargs):
            return super().list(request, *args, **kwargs)
    
    参数：
        timeout: 缓存超时时间（秒），默认 300
        key_prefix: 缓存键前缀
    
    返回：
        装饰后的视图函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 只缓存 GET 请求
            if request.method != 'GET':
                return func(self, request, *args, **kwargs)
            
            # 生成缓存键（包含分页信息）
            cache_key = _get_cache_key_from_request(
                request,
                key_prefix or f'{func.__name__}_page_{request.GET.get("page", 1)}',
                prefix='cache_list'
            )
            
            # 尝试从缓存获取
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f'列表缓存命中: {cache_key}')
                return cached_response
            
            # 调用原函数
            response = func(self, request, *args, **kwargs)
            
            # 仅缓存成功的响应
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                cache.set(cache_key, response, timeout)
                logger.debug(f'列表缓存设置: {cache_key} (超时: {timeout}秒)')
            
            return response
        
        return wrapper
    return decorator


def cache_if(condition_func):
    """
    条件缓存装饰器
    
    仅在满足条件时缓存响应。条件函数接收请求对象，
    返回 True 表示应该缓存。
    
    使用方式：
        def should_cache(request):
            return not request.user.is_authenticated or request.user.is_staff
        
        @cache_if(should_cache)
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)
    
    参数：
        condition_func: 条件函数，接收 request，返回 bool
    
    返回：
        装饰后的视图函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 检查是否应该缓存
            if not condition_func(request):
                return func(self, request, *args, **kwargs)
            
            # 生成缓存键
            cache_key = _get_cache_key_from_request(
                request,
                func.__name__,
                prefix='cache_conditional'
            )
            
            # 尝试从缓存获取
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f'条件缓存命中: {cache_key}')
                return cached_response
            
            # 调用原函数
            response = func(self, request, *args, **kwargs)
            
            # 仅缓存成功的响应
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                cache.set(cache_key, response, 300)
                logger.debug(f'条件缓存设置: {cache_key}')
            
            return response
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    缓存失效装饰器
    
    在执行函数后清除匹配模式的缓存。
    用于 POST/PUT/DELETE 操作后清除相关缓存。
    
    使用方式：
        @invalidate_cache(pattern='cache_list:products:*')
        def destroy(self, request, *args, **kwargs):
            return super().destroy(request, *args, **kwargs)
    
    参数：
        pattern: 缓存键模式（支持通配符 *）
    
    返回：
        装饰后的视图函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # 执行原函数
            response = func(self, request, *args, **kwargs)
            
            # 如果操作成功，清除缓存
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                try:
                    from apps.core.cache_manager import CacheManager
                    manager = CacheManager()
                    count = manager.clear_pattern(pattern)
                    logger.info(f'缓存失效: {pattern} (清除 {count} 个键)')
                except Exception as e:
                    logger.warning(f'缓存失效失败: {str(e)}')
            
            return response
        
        return wrapper
    return decorator


def cache_control_header(max_age: int = 300, must_revalidate: bool = False):
    """
    HTTP 缓存控制装饰器
    
    为响应添加 Cache-Control 头。用于控制客户端
    和代理缓存的行为。
    
    使用方式：
        @cache_control_header(max_age=600, must_revalidate=True)
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)
    
    参数：
        max_age: 最大生命周期（秒），默认 300
        must_revalidate: 是否必须重新验证过期缓存
    
    返回：
        装饰后的视图函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            response = func(self, request, *args, **kwargs)
            
            # 添加 Cache-Control 头
            cache_control = f'max-age={max_age}, public'
            if must_revalidate:
                cache_control += ', must-revalidate'
            
            response['Cache-Control'] = cache_control
            
            return response
        
        return wrapper
    return decorator


def with_cache_stats(func):
    """
    记录缓存统计装饰器
    
    在视图执行前后记录缓存统计信息，
    用于性能分析和监控。
    
    使用方式：
        @with_cache_stats
        def retrieve(self, request, *args, **kwargs):
            return super().retrieve(request, *args, **kwargs)
    
    返回：
        装饰后的视图函数
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        from apps.core.cache_manager import _cache_metrics
        import time
        
        # 记录操作前的统计
        metrics_before = _cache_metrics.to_dict()
        start_time = time.time()
        
        # 执行原函数
        response = func(self, request, *args, **kwargs)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 记录操作后的统计
        metrics_after = _cache_metrics.to_dict()
        
        # 计算差异
        cache_operations = {
            'hits_delta': metrics_after['hits'] - metrics_before['hits'],
            'misses_delta': metrics_after['misses'] - metrics_before['misses'],
            'execution_time_ms': round(execution_time * 1000, 2),
        }
        
        logger.debug(f'缓存统计: {cache_operations}')
        
        # 添加到响应头（可选）
        if isinstance(response, Response):
            response['X-Cache-Hits-Delta'] = str(cache_operations['hits_delta'])
            response['X-Cache-Misses-Delta'] = str(cache_operations['misses_delta'])
            response['X-Execution-Time-Ms'] = str(cache_operations['execution_time_ms'])
        
        return response
    
    return wrapper
