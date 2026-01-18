"""
Django 管理命令：缓存管理

用法：
    python manage.py cache_manage --list          # 列出所有缓存键
    python manage.py cache_manage --clear         # 清空所有缓存
    python manage.py cache_manage --stats         # 显示缓存统计
    python manage.py cache_manage --health-check  # 检查缓存健康状况
    python manage.py cache_manage --warmup        # 预热缓存
    python manage.py cache_manage --clear-pattern "user:*"  # 清除匹配模式的缓存
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from apps.core.cache_manager import CacheManager, _cache_metrics
from apps.core.cache_config import CacheOptimization
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '缓存管理命令（查看、清理、统计、预热等）'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='列出所有缓存键',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清空所有缓存',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='显示缓存统计信息',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='检查缓存健康状况',
        )
        parser.add_argument(
            '--warmup',
            action='store_true',
            help='预热缓存（热门产品等）',
        )
        parser.add_argument(
            '--clear-pattern',
            type=str,
            help='清除匹配模式的缓存（如 "user:*"）',
        )
        parser.add_argument(
            '--config',
            action='store_true',
            help='显示推荐的缓存配置',
        )
    
    def handle(self, *args, **options):
        try:
            if options['list']:
                self.list_cache_keys()
            elif options['clear']:
                self.clear_cache()
            elif options['stats']:
                self.show_stats()
            elif options['health_check']:
                self.health_check()
            elif options['warmup']:
                self.warmup_cache()
            elif options['clear_pattern']:
                self.clear_pattern(options['clear_pattern'])
            elif options['config']:
                self.show_config()
            else:
                self.stdout.write(self.style.WARNING('请指定一个操作命令'))
                self.print_help('manage.py', 'cache_manage')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'错误: {str(e)}'))
            logger.exception('缓存管理命令执行失败')
    
    def list_cache_keys(self):
        """列出所有缓存键"""
        self.stdout.write(self.style.SUCCESS('正在列出缓存键...'))
        
        try:
            keys = cache.keys('*')
            
            if not keys:
                self.stdout.write(self.style.WARNING('缓存为空'))
                return
            
            self.stdout.write(f'\n共有 {len(keys)} 个缓存键：\n')
            
            for key in sorted(keys)[:100]:  # 限制显示 100 个
                value = cache.get(key)
                value_type = type(value).__name__
                value_size = len(str(value))
                self.stdout.write(f'  {key}: {value_type} ({value_size} bytes)')
            
            if len(keys) > 100:
                self.stdout.write(f'\n... 还有 {len(keys) - 100} 个键')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'列出缓存键失败: {str(e)}'))
    
    def clear_cache(self):
        """清空所有缓存"""
        self.stdout.write(self.style.WARNING('正在清空缓存...'))
        
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS('缓存已清空'))
            logger.info('所有缓存已清空')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'清空缓存失败: {str(e)}'))
    
    def show_stats(self):
        """显示缓存统计"""
        self.stdout.write(self.style.SUCCESS('\n缓存统计信息：\n'))
        
        stats = _cache_metrics.to_dict()
        
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')
        
        self.stdout.write('')
    
    def health_check(self):
        """检查缓存健康状况"""
        self.stdout.write(self.style.SUCCESS('\n缓存健康检查：\n'))
        
        health = CacheOptimization.check_cache_health()
        
        status_style = self.style.SUCCESS if health['status'] == 'healthy' else self.style.ERROR
        
        self.stdout.write(f'状态: {status_style(health["status"])}')
        self.stdout.write(f'后端: {health.get("backend", "N/A")}')
        self.stdout.write(f'位置: {health.get("location", "N/A")}')
        self.stdout.write(f'消息: {health["message"]}\n')
    
    def warmup_cache(self):
        """预热缓存"""
        self.stdout.write(self.style.SUCCESS('正在预热缓存...'))
        
        try:
            from apps.core.cache_manager import CacheWarmup
            
            manager = CacheManager()
            
            # 预热热销产品
            CacheWarmup.warmup_popular_products(manager, limit=50)
            
            self.stdout.write(self.style.SUCCESS('缓存预热完成'))
            logger.info('缓存已预热')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'缓存预热失败: {str(e)}'))
    
    def clear_pattern(self, pattern: str):
        """清除匹配模式的缓存"""
        self.stdout.write(f'正在清除匹配 "{pattern}" 的缓存...')
        
        try:
            manager = CacheManager()
            count = manager.clear_pattern(pattern)
            
            self.stdout.write(self.style.SUCCESS(f'已清除 {count} 个缓存键'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'清除缓存失败: {str(e)}'))
    
    def show_config(self):
        """显示推荐的缓存配置"""
        self.stdout.write(self.style.SUCCESS('\n推荐的缓存配置（用于 settings.py）：\n'))
        
        from apps.core.cache_config import get_cache_config
        
        config = get_cache_config()
        
        self.stdout.write(self.style.SUCCESS('# 开发环境配置'))
        self.stdout.write('CACHES = {')
        self.stdout.write("    'default': {")
        self.stdout.write("        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',")
        self.stdout.write("        'LOCATION': 'unique-snowflake',")
        self.stdout.write("        'TIMEOUT': 300,")
        self.stdout.write("    }")
        self.stdout.write("}\n")
        
        self.stdout.write(self.style.SUCCESS('# 生产环境配置（需安装 django-redis）'))
        self.stdout.write("# pip install django-redis")
        self.stdout.write("CACHES = {")
        self.stdout.write("    'default': {")
        self.stdout.write("        'BACKEND': 'django_redis.cache.RedisCache',")
        self.stdout.write("        'LOCATION': 'redis://127.0.0.1:6379/1',")
        self.stdout.write("        'TIMEOUT': 300,")
        self.stdout.write("    }")
        self.stdout.write("}\n")
