#!/usr/bin/env python
"""
Level 3 Task 1 - 缓存系统快速验证脚本

运行方式：
    python verify_cache_system.py

验证项目：
    1. 文件完整性检查
    2. 导入可用性检查
    3. 缓存管理器功能检查
    4. 装饰器可用性检查
    5. 配置完整性检查
"""

import os
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.cache import cache
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def verify_files_exist():
    """验证所有必需的文件都存在"""
    print("\n" + "="*60)
    print("1. 文件完整性检查")
    print("="*60)
    
    required_files = [
        'apps/core/cache_manager.py',
        'apps/core/cache_config.py',
        'apps/core/decorators.py',
        'apps/core/management/commands/cache_manage.py',
        'test_level3_cache.py',
        'LEVEL_3_CACHE_GUIDE.md',
        'LEVEL_3_TASK_1_REPORT.md',
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        exists = full_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
        if not exists:
            all_exist = False
    
    return all_exist


def verify_imports():
    """验证所有模块可以成功导入"""
    print("\n" + "="*60)
    print("2. 导入可用性检查")
    print("="*60)
    
    try:
        from apps.core.cache_manager import (
            CacheManager, CacheConfig, CacheMetrics, CacheWarmup,
            cached, method_cached, get_cache_stats
        )
        print("  ✅ cache_manager 模块导入成功")
    except Exception as e:
        print(f"  ❌ cache_manager 导入失败: {e}")
        return False
    
    try:
        from apps.core.cache_config import CacheOptimization, get_cache_config
        print("  ✅ cache_config 模块导入成功")
    except Exception as e:
        print(f"  ❌ cache_config 导入失败: {e}")
        return False
    
    try:
        from apps.core.decorators import (
            cache_view, cache_list_view, cache_if, 
            invalidate_cache, cache_control_header, with_cache_stats
        )
        print("  ✅ decorators 模块导入成功")
    except Exception as e:
        print(f"  ❌ decorators 导入失败: {e}")
        return False
    
    try:
        from apps.core.views import (
            CacheStatsView, CacheHealthView, 
            CacheClearView, CacheWarmupView
        )
        print("  ✅ cache views 导入成功")
    except Exception as e:
        print(f"  ❌ cache views 导入失败: {e}")
        return False
    
    return True


def verify_cache_manager():
    """验证缓存管理器功能"""
    print("\n" + "="*60)
    print("3. 缓存管理器功能检查")
    print("="*60)
    
    try:
        from apps.core.cache_manager import CacheManager, _cache_metrics
        
        manager = CacheManager()
        
        # 清空统计
        _cache_metrics.reset()
        cache.clear()
        
        # 测试 set/get
        manager.set('test_key', 'test_value', 300)
        value = manager.get('test_key')
        assert value == 'test_value', "get/set 功能异常"
        print("  ✅ set/get 操作正常")
        
        # 测试 delete
        manager.delete('test_key')
        value = manager.get('test_key')
        assert value is None, "delete 功能异常"
        print("  ✅ delete 操作正常")
        
        # 测试 get_or_set
        def get_data():
            return 'computed_value'
        
        result = manager.get_or_set('computed_key', get_data, 300)
        assert result == 'computed_value', "get_or_set 功能异常"
        print("  ✅ get_or_set 操作正常")
        
        # 测试统计
        stats = _cache_metrics.to_dict()
        assert 'hits' in stats, "统计数据缺失"
        assert 'misses' in stats, "统计数据缺失"
        print("  ✅ 缓存统计正常")
        
        return True
    except Exception as e:
        print(f"  ❌ 缓存管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_decorators():
    """验证装饰器可用性"""
    print("\n" + "="*60)
    print("4. 装饰器可用性检查")
    print("="*60)
    
    try:
        from apps.core.cache_manager import cached, method_cached
        
        # 测试 @cached
        @cached(timeout=300)
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        assert result == 10, "@cached 装饰器功能异常"
        print("  ✅ @cached 装饰器正常")
        
        # 测试 @method_cached
        class TestClass:
            @method_cached(timeout=300)
            def test_method(self, x):
                return x * 3
        
        obj = TestClass()
        result = obj.test_method(5)
        assert result == 15, "@method_cached 装饰器功能异常"
        print("  ✅ @method_cached 装饰器正常")
        
        return True
    except Exception as e:
        print(f"  ❌ 装饰器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_config():
    """验证配置完整性"""
    print("\n" + "="*60)
    print("5. 配置完整性检查")
    print("="*60)
    
    try:
        from apps.core.cache_config import CacheOptimization, get_cache_config
        
        # 测试健康检查
        health = CacheOptimization.check_cache_health()
        assert 'status' in health, "健康检查数据缺失"
        print(f"  ✅ 缓存健康状态: {health['status']}")
        
        # 测试 TTL 推荐
        ttl = CacheOptimization.get_optimal_ttl('user_profile')
        assert ttl > 0, "TTL 推荐失败"
        print(f"  ✅ TTL 推荐正常 (user_profile: {ttl}s)")
        
        # 测试配置生成
        config = get_cache_config('dev')
        assert 'backend' in config, "配置生成失败"
        print("  ✅ 缓存配置生成正常")
        
        return True
    except Exception as e:
        print(f"  ❌ 配置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """打印验证总结"""
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results if r)
    
    for i, (name, result) in enumerate(zip([
        "文件完整性",
        "导入可用性",
        "缓存管理器",
        "装饰器功能",
        "配置完整性"
    ], results), 1):
        status = "✅" if result else "❌"
        print(f"  {status} {i}. {name}")
    
    print("\n" + "-"*60)
    if passed == total:
        print(f"✅ 所有检查通过！({passed}/{total})")
        return True
    else:
        print(f"❌ 有 {total - passed} 个检查失败 ({passed}/{total})")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Level 3 Task 1 - 缓存系统验证")
    print("="*60)
    print(f"项目路径: {PROJECT_ROOT}")
    
    results = [
        verify_files_exist(),
        verify_imports(),
        verify_cache_manager(),
        verify_decorators(),
        verify_config(),
    ]
    
    success = print_summary(results)
    
    print("\n" + "="*60)
    print("快速开始")
    print("="*60)
    print("""
  1. 查看缓存命令帮助：
     python manage.py cache_manage --help
  
  2. 检查缓存状态：
     python manage.py cache_manage --health-check
  
  3. 查看缓存统计：
     python manage.py cache_manage --stats
  
  4. 运行单元测试：
     python manage.py test test_level3_cache -v 2
  
  5. 查看文档：
     cat LEVEL_3_CACHE_GUIDE.md
    """)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
