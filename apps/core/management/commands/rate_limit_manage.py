"""
限流管理命令

使用:
    python manage.py rate_limit_manage --list-config
    python manage.py rate_limit_manage --configure user 100 60
    python manage.py rate_limit_manage --reset
    python manage.py rate_limit_manage --whitelist users add user:123
    python manage.py rate_limit_manage --whitelist ips add 127.0.0.1
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from apps.core.rate_limiter import rate_limiter, reset_rate_limit
from apps.core.rate_limit_config import RateLimitConfig, CostConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """限流管理命令"""
    
    help = '管理 API 限流配置和状态'
    
    def add_arguments(self, parser):
        """添加命令参数"""
        
        # 配置相关
        parser.add_argument(
            '--list-config',
            action='store_true',
            help='显示当前限流配置'
        )
        
        parser.add_argument(
            '--configure',
            nargs=3,
            metavar=('LEVEL', 'RATE', 'PERIOD'),
            help='配置限流: level rate period (e.g., user 100 60)'
        )
        
        # 重置
        parser.add_argument(
            '--reset',
            action='store_true',
            help='重置所有限流记录'
        )
        
        parser.add_argument(
            '--reset-key',
            metavar='KEY',
            help='重置特定键的限流记录'
        )
        
        # 白名单管理
        parser.add_argument(
            '--whitelist',
            nargs=3,
            metavar=('TYPE', 'OPERATION', 'VALUE'),
            help='白名单操作: type (users/ips/endpoints) operation (add/remove) value'
        )
        
        # 黑名单管理
        parser.add_argument(
            '--blacklist',
            nargs=3,
            metavar=('TYPE', 'OPERATION', 'VALUE'),
            help='黑名单操作: type operation value'
        )
        
        # 统计信息
        parser.add_argument(
            '--stats',
            action='store_true',
            help='显示限流统计信息'
        )
        
        # 策略比较
        parser.add_argument(
            '--strategies',
            action='store_true',
            help='显示可用的限流策略'
        )
    
    def handle(self, *args, **options):
        """处理命令"""
        
        # 显示配置
        if options['list_config']:
            self.show_config()
        
        # 配置限流
        elif options['configure']:
            level, rate, period = options['configure']
            self.configure_limit(level, int(rate), int(period))
        
        # 重置限流
        elif options['reset']:
            self.reset_all()
        
        # 重置特定键
        elif options['reset_key']:
            self.reset_key(options['reset_key'])
        
        # 白名单操作
        elif options['whitelist']:
            key_type, operation, value = options['whitelist']
            self.manage_whitelist(key_type, operation, value)
        
        # 黑名单操作
        elif options['blacklist']:
            key_type, operation, value = options['blacklist']
            self.manage_blacklist(key_type, operation, value)
        
        # 统计信息
        elif options['stats']:
            self.show_stats()
        
        # 策略信息
        elif options['strategies']:
            self.show_strategies()
        
        else:
            self.stdout.write(self.style.WARNING('请指定一个操作'))
            self.print_help()
    
    def show_config(self):
        """显示配置"""
        self.stdout.write(self.style.SUCCESS('\n=== 限流配置 ===\n'))
        
        # 默认限流
        self.stdout.write(self.style.WARNING('默认限流:'))
        for level, limit in RateLimitConfig.DEFAULT_LIMITS.items():
            rate = limit.get('rate', 'N/A')
            period = limit.get('period', 'N/A')
            self.stdout.write(f'  {level}: {rate} req/{period}s')
        
        # 端点限流
        self.stdout.write(self.style.WARNING('\n端点限流:'))
        for endpoint, limit in RateLimitConfig.ENDPOINT_LIMITS.items():
            rate = limit.get('rate', 'N/A')
            period = limit.get('period', 'N/A')
            self.stdout.write(f'  {endpoint}: {rate} req/{period}s')
        
        # 用户层级倍数
        self.stdout.write(self.style.WARNING('\n用户层级倍数:'))
        for tier, multiplier in RateLimitConfig.USER_TIER_MULTIPLIERS.items():
            self.stdout.write(f'  {tier}: {multiplier}x')
        
        # 成本预算
        self.stdout.write(self.style.WARNING('\n成本预算:'))
        for tier, budget in CostConfig.USER_COST_BUDGET.items():
            self.stdout.write(f'  {tier}: {budget} unit/hour')
    
    def configure_limit(self, level, rate, period):
        """配置限流"""
        try:
            RateLimitConfig.configure_limit(level, rate, period)
            rate_limiter.configure(level, rate, period)
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ 已配置 {level} 限流: {rate} req/{period}s'
            ))
            logger.info(f'Rate limit configured: {level}={rate}/{period}s')
        except Exception as e:
            raise CommandError(f'配置失败: {str(e)}')
    
    def reset_all(self):
        """重置所有限流"""
        try:
            reset_rate_limit()
            self.stdout.write(self.style.SUCCESS('✓ 已重置所有限流记录'))
            logger.info('Rate limit records reset')
        except Exception as e:
            raise CommandError(f'重置失败: {str(e)}')
    
    def reset_key(self, key):
        """重置特定键"""
        try:
            reset_rate_limit(key)
            self.stdout.write(self.style.SUCCESS(f'✓ 已重置限流记录: {key}'))
            logger.info(f'Rate limit record reset: {key}')
        except Exception as e:
            raise CommandError(f'重置失败: {str(e)}')
    
    def manage_whitelist(self, key_type, operation, value):
        """管理白名单"""
        try:
            if operation.lower() == 'add':
                RateLimitConfig.add_whitelist(key_type, value)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 已添加到白名单: {key_type}={value}'
                ))
                logger.info(f'Added to whitelist: {key_type}={value}')
            elif operation.lower() == 'remove':
                RateLimitConfig.remove_whitelist(key_type, value)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 已从白名单移除: {key_type}={value}'
                ))
                logger.info(f'Removed from whitelist: {key_type}={value}')
            else:
                raise CommandError(f'未知操作: {operation}')
        except Exception as e:
            raise CommandError(f'操作失败: {str(e)}')
    
    def manage_blacklist(self, key_type, operation, value):
        """管理黑名单"""
        try:
            if operation.lower() == 'add':
                RateLimitConfig.add_blacklist(key_type, value)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 已添加到黑名单: {key_type}={value}'
                ))
                logger.info(f'Added to blacklist: {key_type}={value}')
            elif operation.lower() == 'remove':
                RateLimitConfig.remove_blacklist(key_type, value)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 已从黑名单移除: {key_type}={value}'
                ))
                logger.info(f'Removed from blacklist: {key_type}={value}')
            else:
                raise CommandError(f'未知操作: {operation}')
        except Exception as e:
            raise CommandError(f'操作失败: {str(e)}')
    
    def show_stats(self):
        """显示统计信息"""
        self.stdout.write(self.style.SUCCESS('\n=== 限流统计 ===\n'))
        
        stats = rate_limiter.get_status()
        
        self.stdout.write(f'总请求数: {stats.get("total_requests", 0)}')
        self.stdout.write(f'允许: {stats.get("allowed", 0)}')
        self.stdout.write(f'拒绝: {stats.get("denied", 0)}')
        
        denial_rate = stats.get('denial_rate', 0.0)
        self.stdout.write(f'拒绝率: {denial_rate:.2%}')
    
    def show_strategies(self):
        """显示可用策略"""
        self.stdout.write(self.style.SUCCESS('\n=== 可用限流策略 ===\n'))
        
        strategies = RateLimitConfig.STRATEGY_COMPARISON
        
        for strategy, info in strategies.items():
            self.stdout.write(self.style.WARNING(f'\n{strategy}:'))
            self.stdout.write(f'  说明: {info.get("description", "N/A")}')
            self.stdout.write(f'  优点: {info.get("pros", "N/A")}')
            self.stdout.write(f'  缺点: {info.get("cons", "N/A")}')
            self.stdout.write(f'  使用场景: {info.get("use_case", "N/A")}')
