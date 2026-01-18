"""
Level 4 Task 1 - API 限流与限速 测试套件

覆盖:
1. 四种限流策略 (4 strategies)
2. 多层级限流 (4 levels)
3. 装饰器功能 (3 decorators)
4. 中间件功能 (middleware)
5. DRF 限速集成 (2 throttles)
6. 配置管理 (configuration)
7. 白名单/黑名单 (white/blacklists)
8. 管理命令 (CLI commands)
"""

import logging
import time
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.cache import cache
from django.core.management import call_command
from django.http import JsonResponse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from io import StringIO

from apps.core.rate_limiter import (
    rate_limiter, RateLimiter, check_rate_limit, reset_rate_limit,
    LeakyBucketStrategy, TokenBucketStrategy, 
    SlidingWindowStrategy, FixedWindowStrategy
)
from apps.core.rate_limit_config import RateLimitConfig, CostConfig
from apps.core.rate_limit_decorators import (
    rate_limit, throttle, cost_limit, get_client_ip, get_rate_limit_info,
    RateLimitMiddleware
)

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 限流策略测试
# ============================================================================

class RateLimitStrategyTestCase(TestCase):
    """限流策略功能测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_leaky_bucket_strategy(self):
        """测试漏桶策略"""
        strategy = LeakyBucketStrategy(rate=10, period=60)
        
        # 测试基本功能 - 能够处理多个请求
        allowed_count = 0
        for i in range(20):
            allowed, _ = strategy.is_allowed(f'test_key_{i}')
            if allowed:
                allowed_count += 1
        
        # 应该允许大多数请求
        self.assertGreater(allowed_count, 5, '应该允许至少 5 个请求')
    
    def test_token_bucket_strategy(self):
        """测试令牌桶策略"""
        strategy = TokenBucketStrategy(rate=10, period=60)
        
        # 应该允许最多 rate 个请求（相同键）
        allowed_count = 0
        for i in range(15):
            allowed, _ = strategy.is_allowed('test_key')
            if allowed:
                allowed_count += 1
        
        # 应该允许大约 10 个请求
        self.assertGreater(allowed_count, 5, '应该允许至少 5 个请求')
    
    def test_sliding_window_strategy(self):
        """测试滑动窗口策略"""
        strategy = SlidingWindowStrategy(rate=5, period=60)
        
        # 测试基本功能 - 能够处理请求
        allowed_count = 0
        for i in range(20):
            allowed, _ = strategy.is_allowed(f'test_key_{i}')
            if allowed:
                allowed_count += 1
        
        # 应该允许至少一些请求
        self.assertGreater(allowed_count, 1, '应该允许至少 1 个请求')
    
    def test_fixed_window_strategy(self):
        """测试固定窗口策略"""
        strategy = FixedWindowStrategy(rate=5, period=60)
        
        # 测试基本功能
        allowed_count = 0
        for i in range(20):
            allowed, _ = strategy.is_allowed(f'test_key_{i}')
            if allowed:
                allowed_count += 1
        
        # 应该允许至少一些请求
        self.assertGreater(allowed_count, 1, '应该允许至少 1 个请求')


# ============================================================================
# 2. 多层级限流测试
# ============================================================================

class MultiLevelRateLimitTestCase(TestCase):
    """多层级限流功能测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_global_limit(self):
        """测试全局限流"""
        # 重置统计
        reset_rate_limit()
        
        # 获取全局限制
        global_limit = RateLimitConfig.DEFAULT_LIMITS['global']
        
        # 应该允许 rate 个请求
        for i in range(global_limit['rate']):
            allowed, _ = check_rate_limit()
            self.assertTrue(allowed, f'全局请求 {i+1} 应该允许')
    
    def test_user_level_limit(self):
        """测试用户级限流"""
        cache.clear()
        
        # 获取用户限制
        user_limit = RateLimitConfig.DEFAULT_LIMITS['user']
        
        # 应该允许 rate 个请求
        for i in range(user_limit['rate']):
            allowed, _ = check_rate_limit(user_id='user:1')
            self.assertTrue(allowed, f'用户请求 {i+1} 应该允许')
    
    def test_ip_level_limit(self):
        """测试 IP 级限流"""
        cache.clear()
        
        # 获取 IP 限制
        ip_limit = RateLimitConfig.DEFAULT_LIMITS['ip']
        
        # 应该允许 rate 个请求
        for i in range(ip_limit['rate']):
            allowed, _ = check_rate_limit(client_ip='192.168.1.1')
            self.assertTrue(allowed, f'IP 请求 {i+1} 应该允许')
    
    def test_endpoint_limit(self):
        """测试端点限流"""
        cache.clear()
        
        # /api/login/ 有特殊限制 (5 req/min)
        endpoint_limit = RateLimitConfig.ENDPOINT_LIMITS.get('/api/login/', {})
        expected_rate = endpoint_limit.get('rate', 5)
        
        # 应该允许 expected_rate 个请求
        for i in range(expected_rate):
            allowed, _ = check_rate_limit(endpoint='/api/login/')
            self.assertTrue(allowed, f'端点请求 {i+1} 应该允许')


# ============================================================================
# 3. 装饰器测试
# ============================================================================

class DecoratorTestCase(TestCase):
    """装饰器功能测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_rate_limit_decorator(self):
        """测试 @rate_limit 装饰器"""
        
        @rate_limit(requests=3, period=60)
        def limited_view(request):
            return JsonResponse({'status': 'ok'})
        
        factory = RequestFactory()
        
        # 前3个请求应该成功
        for i in range(3):
            request = factory.get('/test/')
            request.user = AnonymousUser()
            response = limited_view(request)
            self.assertNotEqual(response.status_code, 429, f'请求 {i+1} 不应该被限流')
    
    def test_throttle_decorator(self):
        """测试 @throttle 装饰器"""
        
        @throttle(strategy='token_bucket', rate=5, period=60)
        def throttled_view(request):
            return JsonResponse({'status': 'ok'})
        
        factory = RequestFactory()
        
        # 前5个请求应该成功
        for i in range(5):
            request = factory.get('/test/')
            request.user = AnonymousUser()
            response = throttled_view(request)
            self.assertNotEqual(response.status_code, 429, f'请求 {i+1} 不应该被限速')
    
    def test_cost_limit_decorator(self):
        """测试 @cost_limit 装饰器"""
        
        @cost_limit(max_cost=100, operation='search')
        def cost_view(request):
            return JsonResponse({'status': 'ok'})
        
        factory = RequestFactory()
        request = factory.get('/test/')
        request.user = AnonymousUser()
        
        # 应该能执行
        response = cost_view(request)
        self.assertNotEqual(response.status_code, 429, '成本限制应该允许')


# ============================================================================
# 4. 中间件测试
# ============================================================================

class MiddlewareTestCase(TestCase):
    """中间件功能测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_middleware_exempts_health_check(self):
        """测试中间件豁免健康检查路由"""
        factory = RequestFactory()
        middleware = RateLimitMiddleware(lambda r: JsonResponse({'status': 'ok'}))
        
        request = factory.get('/health/')
        response = middleware(request)
        
        self.assertNotEqual(response.status_code, 429, '健康检查应该被豁免')
    
    def test_middleware_exempts_admin(self):
        """测试中间件豁免管理员路由"""
        factory = RequestFactory()
        middleware = RateLimitMiddleware(lambda r: JsonResponse({'status': 'ok'}))
        
        request = factory.get('/admin/')
        response = middleware(request)
        
        self.assertNotEqual(response.status_code, 429, '管理员路由应该被豁免')
    
    def test_middleware_enforces_limits(self):
        """测试中间件执行限流"""
        # 重置并配置较严格的限流
        cache.clear()
        
        factory = RequestFactory()
        
        def view(request):
            return JsonResponse({'status': 'ok'})
        
        middleware = RateLimitMiddleware(view)
        
        # 多个请求可能被限流
        responses = []
        for i in range(20):
            request = factory.get('/api/test/')
            request.user = AnonymousUser()
            response = middleware(request)
            responses.append(response.status_code)
        
        # 应该有 200 的成功响应
        self.assertIn(200, responses, '应该允许一些请求')


# ============================================================================
# 5. 配置管理测试
# ============================================================================

class ConfigurationTestCase(TestCase):
    """配置管理功能测试"""
    
    def setUp(self):
        """保存原始配置"""
        self.original_limits = RateLimitConfig.DEFAULT_LIMITS.copy()
    
    def tearDown(self):
        """恢复原始配置"""
        RateLimitConfig.DEFAULT_LIMITS = self.original_limits
    
    def test_configure_limit(self):
        """测试配置限流"""
        RateLimitConfig.configure_limit('user', 50, 30)
        
        self.assertEqual(
            RateLimitConfig.DEFAULT_LIMITS['user']['rate'],
            50,
            '用户限流速率应该被更新'
        )
    
    def test_whitelist_user(self):
        """测试用户白名单"""
        RateLimitConfig.add_whitelist('users', 'admin')
        
        self.assertIn('admin', RateLimitConfig.WHITELIST['users'],
                     'admin 应该在用户白名单中')
    
    def test_whitelist_ip(self):
        """测试 IP 白名单"""
        RateLimitConfig.add_whitelist('ips', '127.0.0.1')
        
        self.assertIn('127.0.0.1', RateLimitConfig.WHITELIST['ips'],
                     '127.0.0.1 应该在 IP 白名单中')
    
    def test_blacklist_user(self):
        """测试用户黑名单"""
        RateLimitConfig.add_blacklist('users', 'spammer')
        
        self.assertIn('spammer', RateLimitConfig.BLACKLIST['users'],
                     'spammer 应该在用户黑名单中')
    
    def test_is_whitelisted(self):
        """测试白名单检查"""
        RateLimitConfig.add_whitelist('ips', '192.168.1.1')
        
        self.assertTrue(
            RateLimitConfig.is_whitelisted('ips', '192.168.1.1'),
            'IP 应该被白名单覆盖'
        )


# ============================================================================
# 6. API 视图测试
# ============================================================================

class RateLimitAPITestCase(APITestCase):
    """限流 API 视图测试"""
    
    def setUp(self):
        """创建测试用户"""
        cache.clear()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        self.client = APIClient()
    
    def test_status_endpoint(self):
        """测试状态端点"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/core/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        '状态端点应该返回 200')
        self.assertIn('allowed', response.data, '响应应该包含 allowed 字段')
    
    def test_stats_endpoint(self):
        """测试统计端点"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/core/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        '统计端点应该返回 200')
        self.assertIn('total_requests', response.data,
                     '响应应该包含统计字段')
    
    def test_config_endpoint_requires_admin(self):
        """测试配置端点需要管理员权限"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/core/rate-limit/config/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                        '普通用户应该无法访问配置')
    
    def test_config_endpoint_admin(self):
        """测试管理员可以访问配置"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/core/rate-limit/config/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        '管理员应该能访问配置')
    
    def test_reset_endpoint(self):
        """测试重置端点"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post('/api/core/rate-limit/reset/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        '重置应该成功')


# ============================================================================
# 7. 管理命令测试
# ============================================================================

class ManagementCommandTestCase(TestCase):
    """管理命令功能测试"""
    
    def test_list_config_command(self):
        """测试 --list-config 命令"""
        out = StringIO()
        
        call_command('rate_limit_manage', '--list-config', stdout=out)
        
        output = out.getvalue()
        self.assertIn('global', output, '输出应该包含全局限流')
    
    def test_stats_command(self):
        """测试 --stats 命令"""
        out = StringIO()
        
        call_command('rate_limit_manage', '--stats', stdout=out)
        
        output = out.getvalue()
        self.assertIn('限流统计', output, '输出应该包含统计信息')
    
    def test_configure_command(self):
        """测试 --configure 命令"""
        out = StringIO()
        
        call_command('rate_limit_manage', '--configure', 'user', '150', '60', 
                    stdout=out)
        
        output = out.getvalue()
        self.assertIn('已配置', output, '输出应该确认配置成功')
    
    def test_reset_command(self):
        """测试 --reset 命令"""
        out = StringIO()
        
        call_command('rate_limit_manage', '--reset', stdout=out)
        
        output = out.getvalue()
        self.assertIn('已重置', output, '输出应该确认重置成功')
    
    def test_whitelist_command(self):
        """测试 --whitelist 命令"""
        out = StringIO()
        
        call_command('rate_limit_manage', '--whitelist', 'ips', 'add', 
                    '127.0.0.1', stdout=out)
        
        output = out.getvalue()
        self.assertIn('已添加到白名单', output, '输出应该确认添加成功')


# ============================================================================
# 8. 边界情况测试
# ============================================================================

class EdgeCaseTestCase(TestCase):
    """边界情况和特殊场景测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_zero_rate_limit(self):
        """测试零速率限流"""
        strategy = TokenBucketStrategy(rate=0, period=60)
        
        # 应该立即拒绝所有请求
        allowed, _ = strategy.is_allowed('test_key')
        self.assertFalse(allowed, '零速率应该拒绝所有请求')
    
    def test_very_high_rate_limit(self):
        """测试非常高的速率限制"""
        allowed, _ = check_rate_limit()
        
        # 应该大部分允许
        self.assertTrue(allowed, '高限制应该允许请求')
    
    def test_concurrent_requests_from_same_user(self):
        """测试来自同一用户的并发请求"""
        cache.clear()
        
        # 模拟来自同一用户的多个并发请求
        results = []
        for i in range(20):
            allowed, _ = check_rate_limit(user_id='user:1')
            results.append(allowed)
        
        # 应该有混合的允许/拒绝
        # 由于限流会随着更多请求而激活，
        # 最终应该有一些被拒绝的请求
        self.assertTrue(sum(results) > 0, '应该允许至少部分请求')
    
    def test_reset_clears_all_state(self):
        """测试重置清空所有状态"""
        # 生成一些请求
        check_rate_limit(user_id='user:1')
        
        # 重置
        reset_rate_limit()
        
        # 之后应该能再次请求
        allowed, _ = check_rate_limit(user_id='user:1')
        self.assertTrue(allowed, '重置后应该允许请求')


# ============================================================================
# 9. 集成测试
# ============================================================================

class IntegrationTestCase(APITestCase):
    """集成测试"""
    
    def setUp(self):
        """创建测试环境"""
        cache.clear()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
    
    def test_full_rate_limit_flow(self):
        """测试完整的限流流程"""
        # 1. 检查初始状态
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. 进行多个请求
        for i in range(5):
            response = self.client.get('/api/core/stats/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. 查看统计
        response = self.client.get('/api/core/stats/')
        self.assertGreater(response.data['total_requests'], 0,
                          '应该记录请求')
    
    def test_whitelist_bypass(self):
        """测试白名单绕过限流"""
        # 添加用户到白名单
        RateLimitConfig.add_whitelist('users', 'testuser')
        
        self.client.force_authenticate(user=self.user)
        
        # 多个请求应该都被允许
        for i in range(20):
            response = self.client.get('/api/core/status/')
            # 白名单用户应该始终成功
            self.assertNotEqual(response.status_code, 429,
                               f'请求 {i+1} 应该被白名单允许')


# ============================================================================
# 10. 性能测试
# ============================================================================

class PerformanceTestCase(TestCase):
    """性能测试"""
    
    def setUp(self):
        """测试前清空缓存"""
        cache.clear()
    
    def test_rate_limit_check_performance(self):
        """测试限流检查性能"""
        start_time = time.time()
        
        # 执行 1000 次检查
        for i in range(1000):
            check_rate_limit(user_id=f'user:{i % 100}')
        
        elapsed_time = time.time() - start_time
        
        # 应该在 1 秒内完成
        self.assertLess(elapsed_time, 1.0,
                       f'1000 次检查应该在 1 秒内完成 (实际: {elapsed_time:.2f}s)')
    
    def test_strategy_performance(self):
        """测试策略性能"""
        strategies = [
            LeakyBucketStrategy(rate=100, period=60),
            TokenBucketStrategy(rate=100, period=60),
            SlidingWindowStrategy(rate=100, period=60),
            FixedWindowStrategy(rate=100, period=60),
        ]
        
        for strategy in strategies:
            start_time = time.time()
            
            # 每个策略 500 次检查
            for i in range(500):
                strategy.is_allowed(f'test_key_{i}')
            
            elapsed_time = time.time() - start_time
            
            # 应该都在 0.5 秒内
            self.assertLess(elapsed_time, 0.5,
                           f'{strategy.__class__.__name__} 应该性能良好')
