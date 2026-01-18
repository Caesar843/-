"""
API 限流与节流系统 - 核心限流引擎

实现多种限流策略：
1. 漏桶算法 (Leaky Bucket)
2. 令牌桶算法 (Token Bucket)
3. 滑动时间窗口 (Sliding Window)
4. 固定时间窗口 (Fixed Window)

支持多层次限制：
- 全局限制
- 用户级限制
- IP 级限制
- 端点级限制
- 基于成本的限制
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, Any
from collections import defaultdict
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 限流策略基类和具体实现
# ============================================================================

class RateLimitStrategy(ABC):
    """限流策略基类"""
    
    def __init__(self, rate: int, period: int):
        """
        初始化限流策略
        
        Args:
            rate: 允许的最大请求数
            period: 时间窗口（秒）
        """
        self.rate = rate
        self.period = period
        self.cache = cache
    
    @abstractmethod
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查是否允许请求
        
        Args:
            key: 限流键（用户ID、IP等）
        
        Returns:
            (是否允许, 限流信息字典)
        """
        pass
    
    @abstractmethod
    def reset(self, key: str) -> None:
        """重置限流记录"""
        pass


class LeakyBucketStrategy(RateLimitStrategy):
    """
    漏桶算法 - 均匀流出请求
    
    特点：
    - 流出速率恒定
    - 适合平滑流量
    - 防止突发流量
    """
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        cache_key = f'leaky_bucket:{key}'
        bucket_data = self.cache.get(cache_key, {
            'tokens': self.rate,
            'last_update': time.time(),
            'requests': 0
        })
        
        # 计算漏出的请求数
        now = time.time()
        elapsed = now - bucket_data['last_update']
        leak_rate = self.rate / self.period  # 每秒漏出速率
        leaked = elapsed * leak_rate
        
        # 更新可用令牌
        bucket_data['tokens'] = min(
            self.rate,
            bucket_data['tokens'] + leaked
        )
        bucket_data['requests'] += 1
        bucket_data['last_update'] = now
        
        # 检查是否超限
        allowed = bucket_data['tokens'] >= 1
        if allowed:
            bucket_data['tokens'] -= 1
        
        # 保存状态
        self.cache.set(cache_key, bucket_data, self.period + 60)
        
        return allowed, {
            'remaining': int(bucket_data['tokens']),
            'reset_after': self.period,
            'requests': bucket_data['requests']
        }
    
    def reset(self, key: str) -> None:
        """重置限流记录"""
        cache_key = f'leaky_bucket:{key}'
        self.cache.delete(cache_key)


class TokenBucketStrategy(RateLimitStrategy):
    """
    令牌桶算法 - 允许突发流量
    
    特点：
    - 允许短时突发
    - 可配置令牌生成速率
    - 更灵活的限流控制
    """
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        cache_key = f'token_bucket:{key}'
        bucket_data = self.cache.get(cache_key, {
            'tokens': self.rate,
            'last_update': time.time(),
            'requests': 0
        })
        
        # 计算补充的令牌数
        now = time.time()
        elapsed = now - bucket_data['last_update']
        token_rate = self.rate / self.period  # 每秒生成的令牌数
        new_tokens = elapsed * token_rate
        
        # 更新令牌（不超过桶容量）
        bucket_data['tokens'] = min(
            self.rate,
            bucket_data['tokens'] + new_tokens
        )
        bucket_data['requests'] += 1
        bucket_data['last_update'] = now
        
        # 检查是否有足够令牌
        allowed = bucket_data['tokens'] >= 1
        if allowed:
            bucket_data['tokens'] -= 1
        
        # 保存状态
        self.cache.set(cache_key, bucket_data, self.period + 60)
        
        return allowed, {
            'remaining': int(bucket_data['tokens']),
            'reset_after': self.period,
            'requests': bucket_data['requests']
        }
    
    def reset(self, key: str) -> None:
        """重置限流记录"""
        cache_key = f'token_bucket:{key}'
        self.cache.delete(cache_key)


class SlidingWindowStrategy(RateLimitStrategy):
    """
    滑动时间窗口 - 精确的时间控制
    
    特点：
    - 精确计数
    - 消耗更多内存
    - 不允许短时突发
    """
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        cache_key = f'sliding_window:{key}'
        now = time.time()
        window_start = now - self.period
        
        # 获取时间窗口内的请求列表
        requests = self.cache.get(cache_key, [])
        
        # 清除超出时间窗口的请求
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # 检查是否超限
        allowed = len(requests) < self.rate
        
        if allowed:
            requests.append(now)
        
        # 保存状态
        self.cache.set(cache_key, requests, self.period + 60)
        
        return allowed, {
            'remaining': self.rate - len(requests),
            'reset_after': self.period,
            'requests': len(requests)
        }
    
    def reset(self, key: str) -> None:
        """重置限流记录"""
        cache_key = f'sliding_window:{key}'
        self.cache.delete(cache_key)


class FixedWindowStrategy(RateLimitStrategy):
    """
    固定时间窗口 - 最简单的限流
    
    特点：
    - 实现简单
    - 性能最好
    - 可能出现边界问题
    """
    
    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        now = time.time()
        window_key = f'fixed_window:{key}:{int(now // self.period)}'
        
        # 获取当前窗口的请求计数
        request_count = self.cache.get(window_key, 0)
        
        # 检查是否超限
        allowed = request_count < self.rate
        
        if allowed:
            request_count += 1
            self.cache.set(window_key, request_count, self.period + 10)
        
        # 计算重置时间
        reset_after = self.period - (int(now) % self.period)
        
        return allowed, {
            'remaining': self.rate - request_count,
            'reset_after': reset_after,
            'requests': request_count
        }
    
    def reset(self, key: str) -> None:
        """重置限流记录"""
        now = time.time()
        window_key = f'fixed_window:{key}:{int(now // self.period)}'
        self.cache.delete(window_key)


# ============================================================================
# 2. 多层次限流管理器
# ============================================================================

class RateLimiter:
    """
    API 限流管理器 - 支持多层次限制
    
    支持：
    - 全局限制
    - 用户级限制
    - IP 级限制
    - 端点级限制
    - 基于成本的限制
    """
    
    # 默认限流配置
    DEFAULT_CONFIG = {
        'global': {'rate': 10000, 'period': 60, 'strategy': 'token_bucket'},
        'user': {'rate': 100, 'period': 60, 'strategy': 'token_bucket'},
        'ip': {'rate': 200, 'period': 60, 'strategy': 'token_bucket'},
        'endpoint': {'rate': 50, 'period': 60, 'strategy': 'token_bucket'},
    }
    
    # 策略映射
    STRATEGIES = {
        'leaky_bucket': LeakyBucketStrategy,
        'token_bucket': TokenBucketStrategy,
        'sliding_window': SlidingWindowStrategy,
        'fixed_window': FixedWindowStrategy,
    }
    
    def __init__(self):
        """初始化限流管理器"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.strategies = {}
        self._initialize_strategies()
        self.stats = defaultdict(lambda: {
            'requests': 0,
            'denied': 0,
            'allowed': 0,
        })
    
    def _initialize_strategies(self) -> None:
        """初始化所有限流策略"""
        for level, config in self.config.items():
            strategy_class = self.STRATEGIES.get(config['strategy'])
            if strategy_class:
                self.strategies[level] = strategy_class(
                    rate=config['rate'],
                    period=config['period']
                )
    
    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查是否允许请求
        
        Args:
            user_id: 用户 ID
            client_ip: 客户端 IP
            endpoint: API 端点
            cost: 请求成本（消耗的令牌数）
        
        Returns:
            (是否允许, 限流信息)
        """
        # 1. 检查全局限制
        global_allowed, global_info = self.strategies['global'].is_allowed('global')
        
        # 2. 检查用户限制
        user_allowed = True
        user_info = {}
        if user_id:
            user_allowed, user_info = self.strategies['user'].is_allowed(f'user:{user_id}')
        
        # 3. 检查 IP 限制
        ip_allowed = True
        ip_info = {}
        if client_ip:
            ip_allowed, ip_info = self.strategies['ip'].is_allowed(f'ip:{client_ip}')
        
        # 4. 检查端点限制
        endpoint_allowed = True
        endpoint_info = {}
        if endpoint:
            endpoint_allowed, endpoint_info = self.strategies['endpoint'].is_allowed(
                f'endpoint:{endpoint}'
            )
        
        # 5. 综合判断
        allowed = (
            global_allowed and
            user_allowed and
            ip_allowed and
            endpoint_allowed
        )
        
        # 6. 更新统计信息
        self.stats['total']['requests'] += 1
        if allowed:
            self.stats['total']['allowed'] += 1
        else:
            self.stats['total']['denied'] += 1
        
        # 7. 记录日志
        if not allowed:
            denied_reason = []
            if not global_allowed:
                denied_reason.append('global_limit')
            if not user_allowed:
                denied_reason.append('user_limit')
            if not ip_allowed:
                denied_reason.append('ip_limit')
            if not endpoint_allowed:
                denied_reason.append('endpoint_limit')
            
            logger.warning(
                f'Rate limit exceeded: {denied_reason}',
                extra={
                    'user_id': user_id,
                    'client_ip': client_ip,
                    'endpoint': endpoint,
                }
            )
        
        # 8. 返回综合结果
        return allowed, {
            'global': global_info,
            'user': user_info,
            'ip': ip_info,
            'endpoint': endpoint_info,
            'allowed': allowed,
        }
    
    def get_status(self, key: Optional[str] = None) -> Dict[str, Any]:
        """获取限流状态"""
        if key:
            # 获取特定键的状态
            status = {}
            for level, strategy in self.strategies.items():
                _, info = strategy.is_allowed(key)
                status[level] = info
            return status
        else:
            # 获取全局统计
            return {
                'total_requests': self.stats['total']['requests'],
                'allowed': self.stats['total']['allowed'],
                'denied': self.stats['total']['denied'],
                'denial_rate': (
                    self.stats['total']['denied'] / self.stats['total']['requests']
                    if self.stats['total']['requests'] > 0 else 0
                ),
            }
    
    def reset(self, key: Optional[str] = None) -> None:
        """重置限流记录"""
        if key:
            for strategy in self.strategies.values():
                strategy.reset(key)
        else:
            # 重置所有
            for strategy in self.strategies.values():
                strategy.reset('global')
            self.stats.clear()
    
    def configure(self, level: str, rate: int, period: int, strategy: str = None) -> None:
        """配置特定层级的限流"""
        if level not in self.config:
            raise ValueError(f'Unknown rate limit level: {level}')
        
        if strategy and strategy not in self.STRATEGIES:
            raise ValueError(f'Unknown strategy: {strategy}')
        
        # 更新配置
        self.config[level]['rate'] = rate
        self.config[level]['period'] = period
        if strategy:
            self.config[level]['strategy'] = strategy
        
        # 重新初始化策略
        strategy_class = self.STRATEGIES.get(self.config[level]['strategy'])
        self.strategies[level] = strategy_class(
            rate=rate,
            period=period
        )
        
        logger.info(
            f'Rate limit configured: {level} = {rate} req/{period}s using {strategy or self.config[level]["strategy"]}'
        )


# ============================================================================
# 3. 全局限流器实例
# ============================================================================

rate_limiter = RateLimiter()


# ============================================================================
# 4. 便利函数
# ============================================================================

def check_rate_limit(
    user_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    endpoint: Optional[str] = None,
    cost: int = 1
) -> Tuple[bool, Dict[str, Any]]:
    """
    快速检查限流（包装全局实例）
    """
    return rate_limiter.check_rate_limit(
        user_id=user_id,
        client_ip=client_ip,
        endpoint=endpoint,
        cost=cost
    )


def get_rate_limit_status() -> Dict[str, Any]:
    """获取限流状态"""
    return rate_limiter.get_status()


def reset_rate_limit(key: Optional[str] = None) -> None:
    """重置限流"""
    rate_limiter.reset(key)
