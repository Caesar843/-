"""
API 限流配置管理

提供：
1. 限流配置管理
2. 限流规则定义
3. 动态配置支持
4. 限流白名单/黑名单
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 限流配置
# ============================================================================

class RateLimitConfig:
    """限流配置管理"""
    
    # 默认限流规则
    DEFAULT_LIMITS = {
        'global': {
            'rate': 10000,  # 10000 req/min
            'period': 60,
            'strategy': 'token_bucket',
            'enabled': True,
        },
        'user': {
            'rate': 100,    # 100 req/min per user
            'period': 60,
            'strategy': 'token_bucket',
            'enabled': True,
        },
        'ip': {
            'rate': 200,    # 200 req/min per IP
            'period': 60,
            'strategy': 'token_bucket',
            'enabled': True,
        },
        'endpoint': {
            'rate': 50,     # 50 req/min per endpoint
            'period': 60,
            'strategy': 'token_bucket',
            'enabled': True,
        },
    }
    
    # 端点级限流规则
    ENDPOINT_LIMITS = {
        '/api/auth/login/': {'rate': 5, 'period': 60},          # 登录: 5/分钟
        '/api/auth/register/': {'rate': 3, 'period': 3600},     # 注册: 3/小时
        '/api/auth/password-reset/': {'rate': 3, 'period': 3600}, # 重置: 3/小时
        '/api/search/': {'rate': 30, 'period': 60},             # 搜索: 30/分钟
        '/api/report/export/': {'rate': 10, 'period': 60},      # 导出: 10/分钟
        '/api/users/': {'rate': 100, 'period': 60},             # 用户: 100/分钟
        '/api/orders/': {'rate': 100, 'period': 60},            # 订单: 100/分钟
    }
    
    # 用户等级限流倍数
    USER_TIER_MULTIPLIERS = {
        'free': 1.0,           # 免费用户: 基础限制
        'basic': 1.5,          # 基础用户: 1.5倍
        'premium': 2.5,        # 高级用户: 2.5倍
        'enterprise': 5.0,     # 企业用户: 5倍
    }
    
    # 限流白名单（绕过限流）
    WHITELIST = {
        'users': [],           # 用户 ID 白名单
        'ips': [
            '127.0.0.1',
            'localhost',
        ],                     # IP 白名单
        'endpoints': [],       # 端点白名单
    }
    
    # 限流黑名单（自动拒绝）
    BLACKLIST = {
        'users': [],           # 用户 ID 黑名单
        'ips': [],             # IP 黑名单
        'endpoints': [],       # 端点黑名单
    }
    
    # 限流告警阈值
    ALERT_THRESHOLDS = {
        'denial_rate': 0.1,    # 拒绝率 > 10%
        'denial_count': 100,   # 连续拒绝 > 100 次
        'burst_window': 10,    # 10 秒内拒绝数
    }
    
    @classmethod
    def get_user_rate(cls, user_id: str, tier: str = 'free') -> int:
        """
        根据用户等级获取限流速率
        
        Args:
            user_id: 用户 ID
            tier: 用户等级 (free/basic/premium/enterprise)
        
        Returns:
            限流速率
        """
        base_rate = cls.DEFAULT_LIMITS['user']['rate']
        multiplier = cls.USER_TIER_MULTIPLIERS.get(tier, 1.0)
        return int(base_rate * multiplier)
    
    @classmethod
    def get_endpoint_limit(cls, endpoint: str) -> Optional[Dict[str, int]]:
        """获取端点级限流规则"""
        return cls.ENDPOINT_LIMITS.get(endpoint)
    
    @classmethod
    def is_whitelisted(cls, key_type: str, value: str) -> bool:
        """
        检查是否在白名单中
        
        Args:
            key_type: 类型 (users/ips/endpoints)
            value: 值
        
        Returns:
            是否在白名单中
        """
        return value in cls.WHITELIST.get(key_type, [])
    
    @classmethod
    def is_blacklisted(cls, key_type: str, value: str) -> bool:
        """
        检查是否在黑名单中
        
        Args:
            key_type: 类型 (users/ips/endpoints)
            value: 值
        
        Returns:
            是否在黑名单中
        """
        return value in cls.BLACKLIST.get(key_type, [])
    
    @classmethod
    def configure_limit(cls, level: str, rate: int, period: int) -> None:
        """动态配置限流规则"""
        if level in cls.DEFAULT_LIMITS:
            cls.DEFAULT_LIMITS[level]['rate'] = rate
            cls.DEFAULT_LIMITS[level]['period'] = period
            logger.info(f'Rate limit configured: {level} = {rate} req/{period}s')
        else:
            logger.warning(f'Unknown rate limit level: {level}')
    
    @classmethod
    def add_whitelist(cls, key_type: str, value: str) -> None:
        """添加白名单"""
        if key_type in cls.WHITELIST:
            if value not in cls.WHITELIST[key_type]:
                cls.WHITELIST[key_type].append(value)
                logger.info(f'Added to whitelist: {key_type}={value}')
    
    @classmethod
    def remove_whitelist(cls, key_type: str, value: str) -> None:
        """移除白名单"""
        if key_type in cls.WHITELIST:
            if value in cls.WHITELIST[key_type]:
                cls.WHITELIST[key_type].remove(value)
                logger.info(f'Removed from whitelist: {key_type}={value}')
    
    @classmethod
    def add_blacklist(cls, key_type: str, value: str) -> None:
        """添加黑名单"""
        if key_type in cls.BLACKLIST:
            if value not in cls.BLACKLIST[key_type]:
                cls.BLACKLIST[key_type].append(value)
                logger.warning(f'Added to blacklist: {key_type}={value}')
    
    @classmethod
    def remove_blacklist(cls, key_type: str, value: str) -> None:
        """移除黑名单"""
        if key_type in cls.BLACKLIST:
            if value in cls.BLACKLIST[key_type]:
                cls.BLACKLIST[key_type].remove(value)
                logger.info(f'Removed from blacklist: {key_type}={value}')


# ============================================================================
# 成本配置（基于请求复杂度的限流）
# ============================================================================

class CostConfig:
    """
    基于成本的限流配置
    
    允许为不同操作分配不同的成本，
    用户消耗的总成本受限，而不仅仅是请求数
    """
    
    # 操作成本定义
    OPERATION_COSTS = {
        # 认证相关
        'login': 1,
        'logout': 1,
        'register': 5,
        'password_reset': 10,
        
        # 查询相关
        'list_items': 1,        # 列表查询
        'get_item': 1,          # 单个查询
        'search': 2,            # 搜索查询
        'advanced_search': 5,   # 高级搜索
        'export': 10,           # 导出数据
        
        # 创建相关
        'create_item': 2,       # 创建单个
        'bulk_create': 10,      # 批量创建
        'import': 20,           # 导入数据
        
        # 修改相关
        'update_item': 2,       # 更新单个
        'bulk_update': 10,      # 批量更新
        'patch_item': 1,        # 部分更新
        
        # 删除相关
        'delete_item': 3,       # 删除单个
        'bulk_delete': 15,      # 批量删除
        
        # 分析相关
        'generate_report': 20,  # 生成报告
        'fetch_analytics': 5,   # 获取分析数据
    }
    
    # 用户成本预算（每小时）
    USER_COST_BUDGET = {
        'free': 100,            # 免费用户: 100 cost/hour
        'basic': 500,           # 基础: 500 cost/hour
        'premium': 2000,        # 高级: 2000 cost/hour
        'enterprise': 10000,    # 企业: 10000 cost/hour
    }
    
    @classmethod
    def get_operation_cost(cls, operation: str) -> int:
        """获取操作成本"""
        return cls.OPERATION_COSTS.get(operation, 1)
    
    @classmethod
    def get_user_budget(cls, tier: str = 'free') -> int:
        """获取用户成本预算"""
        return cls.USER_COST_BUDGET.get(tier, 100)


# ============================================================================
# 限流策略对比
# ============================================================================

STRATEGY_COMPARISON = {
    'leaky_bucket': {
        'name': '漏桶算法',
        'pros': ['流出均匀', '防止突发'],
        'cons': ['不允许突发', '实现复杂'],
        'use_case': '流量平滑转发',
    },
    'token_bucket': {
        'name': '令牌桶算法',
        'pros': ['允许突发', '灵活', '易于实现'],
        'cons': ['突发过大可能超载'],
        'use_case': '大多数 API 限流',
    },
    'sliding_window': {
        'name': '滑动时间窗口',
        'pros': ['精确计数', '无边界问题'],
        'cons': ['内存消耗大', '计算复杂'],
        'use_case': '精确限流需求',
    },
    'fixed_window': {
        'name': '固定时间窗口',
        'pros': ['简单快速', '内存低'],
        'cons': ['边界问题', '可能不准确'],
        'use_case': '简单限流',
    },
}
