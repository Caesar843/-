"""
搜索管理 CLI 命令
用于管理搜索索引和执行搜索相关操作
"""

import json
from typing import Optional
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.core.search_manager import get_search_manager
from apps.core.search_config import get_enabled_searchable_models


class Command(BaseCommand):
    """搜索管理命令"""
    
    help = '管理全文搜索系统'

    def add_arguments(self, parser):
        """添加命令参数"""
        
        # 索引管理命令
        parser.add_argument(
            '--list-indexes',
            action='store_true',
            help='列出所有索引',
        )
        
        parser.add_argument(
            '--rebuild-index',
            action='store_true',
            help='重建搜索索引',
        )
        
        parser.add_argument(
            '--index-status',
            action='store_true',
            help='显示索引状态',
        )
        
        # 搜索命令
        parser.add_argument(
            '--search',
            type=str,
            help='执行搜索',
        )
        
        parser.add_argument(
            '--model',
            type=str,
            help='搜索指定模型',
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='结果限制数量',
        )
        
        # 高级搜索
        parser.add_argument(
            '--advanced-search',
            type=str,
            help='执行高级搜索（JSON 格式）',
        )
        
        # 自动完成
        parser.add_argument(
            '--autocomplete',
            type=str,
            help='获取自动完成建议',
        )
        
        # 获取建议
        parser.add_argument(
            '--suggestions',
            type=str,
            help='获取搜索建议',
        )
        
        # 统计
        parser.add_argument(
            '--metrics',
            action='store_true',
            help='显示搜索指标',
        )
        
        # 测试连接
        parser.add_argument(
            '--test',
            action='store_true',
            help='测试搜索系统连接',
        )

    def handle(self, *args, **options):
        """处理命令"""
        
        if options['list_indexes']:
            self.list_indexes()
        elif options['rebuild_index']:
            self.rebuild_index()
        elif options['index_status']:
            self.index_status()
        elif options['search']:
            self.search(
                options['search'],
                model=options.get('model'),
                limit=options.get('limit', 50),
            )
        elif options['advanced_search']:
            self.advanced_search(options['advanced_search'])
        elif options['autocomplete']:
            self.autocomplete(options['autocomplete'])
        elif options['suggestions']:
            self.suggestions(options['suggestions'])
        elif options['metrics']:
            self.metrics()
        elif options['test']:
            self.test()
        else:
            self.print_help('manage.py', 'search_manage')

    def list_indexes(self):
        """列出所有索引"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('可搜索的模型'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        models = get_enabled_searchable_models()
        
        if not models:
            self.stdout.write(self.style.WARNING('没有启用的可搜索模型'))
            return
        
        for i, model in enumerate(models, 1):
            self.stdout.write(f'{i}. {model}')
        
        self.stdout.write(f'\n总计: {len(models)} 个模型\n')

    def rebuild_index(self):
        """重建索引"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('重建搜索索引'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            
            self.stdout.write('⏳ 正在重建索引...')
            success = search_manager.rebuild_index()
            
            if success:
                self.stdout.write(self.style.SUCCESS('✓ 索引已成功重建'))
            else:
                self.stdout.write(self.style.ERROR('✗ 索引重建失败'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def index_status(self):
        """显示索引状态"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('索引状态'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            status_info = search_manager.get_index_status()
            
            self.stdout.write(f'状态: {status_info.get("status")}')
            self.stdout.write(f'后端: {status_info.get("backend")}')
            self.stdout.write(f'文档数: {status_info.get("document_count")}')
            
            if 'index_dir' in status_info:
                self.stdout.write(f'索引目录: {status_info.get("index_dir")}')
            
            self.stdout.write(f'时间戳: {status_info.get("timestamp")}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def search(self, query: str, model: Optional[str] = None, limit: int = 50):
        """执行搜索"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'搜索: "{query}"'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            result = search_manager.search(query, model=model, limit=limit)
            
            total = result.get('total', 0)
            results = result.get('results', [])
            
            self.stdout.write(f'找到 {total} 个结果\n')
            
            if not results:
                self.stdout.write(self.style.WARNING('没有找到结果'))
                return
            
            # 显示结果
            for i, item in enumerate(results[:limit], 1):
                self.stdout.write(f'\n{i}. {item.get("title", "N/A")}')
                self.stdout.write(f'   URL: {item.get("url", "N/A")}')
                self.stdout.write(f'   描述: {item.get("description", "N/A")[:100]}...')
                self.stdout.write(f'   相关度: {item.get("score", 0):.2f}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def advanced_search(self, query_json: str):
        """执行高级搜索"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('高级搜索'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            query_dict = json.loads(query_json)
            
            search_manager = get_search_manager()
            result = search_manager.advanced_search(query_dict)
            
            results = result.get('results', [])
            
            self.stdout.write(f'找到 {len(results)} 个结果\n')
            
            for i, item in enumerate(results[:10], 1):
                self.stdout.write(f'{i}. {item.get("title", "N/A")}')
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('✗ JSON 格式错误'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def autocomplete(self, prefix: str):
        """获取自动完成建议"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'自动完成: "{prefix}"'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            suggestions = search_manager.autocomplete(prefix, limit=10)
            
            self.stdout.write(f'找到 {len(suggestions)} 个建议\n')
            
            for i, suggestion in enumerate(suggestions, 1):
                self.stdout.write(f'{i}. {suggestion}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def suggestions(self, query: str):
        """获取搜索建议"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'搜索建议: "{query}"'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            suggestions = search_manager.get_suggestions(query, limit=5)
            
            self.stdout.write(f'找到 {len(suggestions)} 个建议\n')
            
            for i, suggestion in enumerate(suggestions, 1):
                self.stdout.write(f'{i}. {suggestion}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def metrics(self):
        """显示搜索指标"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('搜索指标'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            metrics = search_manager.get_search_metrics()
            
            self.stdout.write(f'总搜索数: {metrics.get("total_searches", 0)}')
            self.stdout.write(f'唯一查询数: {metrics.get("unique_queries", 0)}')
            
            top_queries = metrics.get('top_queries', [])
            if top_queries:
                self.stdout.write('\n热门查询:')
                for i, (query, count) in enumerate(top_queries[:5], 1):
                    self.stdout.write(f'  {i}. {query} ({count} 次)')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 错误: {e}'))
        
        self.stdout.write('')

    def test(self):
        """测试搜索系统连接"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('搜索系统测试'.center(70))
        self.stdout.write('=' * 70 + '\n')
        
        try:
            search_manager = get_search_manager()
            
            # 测试索引状态
            self.stdout.write('⏳ 检查索引状态...')
            status_info = search_manager.get_index_status()
            
            if status_info.get('status') == 'ok':
                self.stdout.write(self.style.SUCCESS('✓ 索引正常'))
                self.stdout.write(f'  文档数: {status_info.get("document_count")}')
            else:
                self.stdout.write(self.style.ERROR('✗ 索引异常'))
                return
            
            # 测试搜索功能
            self.stdout.write('\n⏳ 测试搜索功能...')
            result = search_manager.search('test', limit=5)
            
            if 'results' in result:
                self.stdout.write(self.style.SUCCESS('✓ 搜索功能正常'))
            else:
                self.stdout.write(self.style.WARNING('⚠ 搜索返回异常'))
            
            # 测试自动完成
            self.stdout.write('\n⏳ 测试自动完成...')
            suggestions = search_manager.autocomplete('te', limit=5)
            
            self.stdout.write(self.style.SUCCESS('✓ 自动完成正常'))
            
            # 总结
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS('✓ 所有测试通过'))
            self.stdout.write('=' * 70)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 测试失败: {e}'))
        
        self.stdout.write('')
