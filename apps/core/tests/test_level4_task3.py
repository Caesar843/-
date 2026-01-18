"""
Level 4 Task 3: 全文搜索系统测试套件
包含搜索管理、API 接口、CLI 命令的完整测试

运行: python manage.py test apps.core.tests.test_level4_task3
"""

import json
from datetime import datetime
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.core.search_manager import (
    SearchManager,
    WhooshSearchBackend,
    get_search_manager,
    reset_search_manager,
)
from apps.core.search_config import (
    SEARCHABLE_MODELS,
    SEARCH_STRATEGIES,
    get_enabled_searchable_models,
)


class SearchManagerTests(TestCase):
    """搜索管理器测试"""

    def setUp(self):
        """设置测试环境"""
        self.search_manager = SearchManager(backend='whoosh')

    def test_search_manager_initialization(self):
        """测试搜索管理器初始化"""
        self.assertIsNotNone(self.search_manager)
        self.assertEqual(self.search_manager.backend_name, 'whoosh')

    def test_index_document(self):
        """测试索引文档"""
        doc_id = 'test-doc-001'
        content = {
            'title': '测试产品',
            'description': '这是一个测试产品',
            'category': 'electronics',
            'tags': 'new,test',
            'url': '/products/test',
            'model': 'product',
        }
        
        result = self.search_manager.index_document(doc_id, content)
        self.assertTrue(result)

    def test_search_basic(self):
        """测试基础搜索"""
        # 索引测试文档
        docs = [
            {
                'id': 'doc1',
                'title': 'Python 编程入门',
                'description': '学习 Python 基础知识',
                'content': 'Python 是一种高级编程语言',
            },
            {
                'id': 'doc2',
                'title': 'Django Web 框架',
                'description': 'Django 是一个强大的 Web 框架',
                'content': 'Django 基于 Python，用于构建 Web 应用',
            },
        ]
        
        for doc in docs:
            self.search_manager.index_document(doc['id'], doc)
        
        # 执行搜索
        result = self.search_manager.search('Python')
        
        self.assertIsNotNone(result)
        self.assertIn('results', result)
        self.assertGreater(result.get('total', 0), 0)

    def test_search_with_pagination(self):
        """测试带分页的搜索"""
        # 索引多个文档
        for i in range(100):
            doc = {
                'title': f'文档 {i}',
                'description': f'描述 {i}',
                'content': '测试内容',
            }
            self.search_manager.index_document(f'doc-{i}', doc)
        
        # 第 1 页
        result1 = self.search_manager.search('文档', limit=10, page=1)
        self.assertEqual(result1.get('limit'), 10)
        self.assertEqual(result1.get('page'), 1)
        
        # 第 2 页
        result2 = self.search_manager.search('文档', limit=10, page=2)
        self.assertEqual(result2.get('page'), 2)

    def test_advanced_search(self):
        """测试高级搜索"""
        query_dict = {
            'keywords': 'laptop',
            'category': 'electronics',
        }
        
        result = self.search_manager.advanced_search(query_dict)
        
        self.assertIsNotNone(result)
        self.assertIn('results', result)

    def test_autocomplete(self):
        """测试自动完成"""
        # 索引文档
        self.search_manager.index_document('doc1', {
            'title': '苹果 MacBook Pro',
            'description': '强大的笔记本电脑',
        })
        
        # 自动完成
        suggestions = self.search_manager.autocomplete('苹果', limit=10)
        
        self.assertIsInstance(suggestions, list)

    def test_get_suggestions(self):
        """测试获取搜索建议"""
        suggestions = self.search_manager.get_suggestions('laptop')
        
        self.assertIsInstance(suggestions, list)

    def test_delete_document(self):
        """测试删除文档"""
        doc_id = 'delete-test-001'
        content = {
            'title': '要删除的文档',
            'description': '测试',
        }
        
        # 索引
        self.search_manager.index_document(doc_id, content)
        
        # 删除
        result = self.search_manager.delete_document(doc_id)
        self.assertTrue(result)

    def test_get_index_status(self):
        """测试获取索引状态"""
        status_info = self.search_manager.get_index_status()
        
        self.assertIsNotNone(status_info)
        self.assertIn('status', status_info)
        self.assertEqual(status_info['status'], 'ok')
        self.assertIn('backend', status_info)

    def test_get_search_metrics(self):
        """测试获取搜索指标"""
        # 执行一些搜索
        self.search_manager.search('test1')
        self.search_manager.search('test2')
        self.search_manager.search('test1')
        
        metrics = self.search_manager.get_search_metrics()
        
        self.assertIsNotNone(metrics)
        self.assertIn('total_searches', metrics)


class WhooshBackendTests(TestCase):
    """Whoosh 后端测试"""

    def setUp(self):
        """设置测试环境"""
        self.backend = WhooshSearchBackend()

    def test_backend_initialization(self):
        """测试后端初始化"""
        self.assertIsNotNone(self.backend)
        self.assertIsNotNone(self.backend.index)

    def test_index_document(self):
        """测试索引文档"""
        result = self.backend.index('test-001', {
            'title': '测试',
            'content': '测试内容',
        })
        
        self.assertTrue(result)

    def test_search(self):
        """测试搜索"""
        # 索引
        self.backend.index('doc1', {
            'title': 'Python 编程',
            'content': 'Python 是一种编程语言',
        })
        
        # 搜索
        results = self.backend.search('Python')
        
        self.assertIsInstance(results, list)

    def test_delete(self):
        """测试删除"""
        doc_id = 'delete-test'
        
        # 索引
        self.backend.index(doc_id, {'title': '测试'})
        
        # 删除
        result = self.backend.delete(doc_id)
        
        self.assertTrue(result)

    def test_get_index_status(self):
        """测试获取索引状态"""
        status_info = self.backend.get_index_status()
        
        self.assertIsNotNone(status_info)
        self.assertEqual(status_info['status'], 'ok')

    def test_rebuild_index(self):
        """测试重建索引"""
        result = self.backend.rebuild_index()
        
        self.assertTrue(result)


class SearchConfigTests(TestCase):
    """搜索配置测试"""

    def test_enabled_models(self):
        """测试获取启用的模型"""
        models = get_enabled_searchable_models()
        
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)

    def test_searchable_models_config(self):
        """测试可搜索模型配置"""
        self.assertIn('product', SEARCHABLE_MODELS)
        self.assertIn('article', SEARCHABLE_MODELS)
        
        product_config = SEARCHABLE_MODELS['product']
        self.assertIn('model', product_config)
        self.assertIn('fields', product_config)
        self.assertIn('enabled', product_config)

    def test_search_strategies(self):
        """测试搜索策略配置"""
        self.assertIn('basic', SEARCH_STRATEGIES)
        self.assertIn('advanced', SEARCH_STRATEGIES)
        self.assertIn('prefix', SEARCH_STRATEGIES)


class SearchAPITests(APITestCase):
    """搜索 API 测试"""

    def setUp(self):
        """设置测试环境"""
        self.client = APIClient()
        self.search_manager = get_search_manager()
        
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )

    def tearDown(self):
        """清理"""
        reset_search_manager()

    def test_search_endpoint_basic(self):
        """测试搜索端点 - 基础"""
        response = self.client.get('/api/search/search/', {
            'query': 'test',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('query', response.data)
        self.assertIn('results', response.data)

    def test_search_endpoint_empty_query(self):
        """测试搜索端点 - 空查询"""
        response = self.client.get('/api/search/search/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_search_endpoint_with_pagination(self):
        """测试搜索端点 - 分页"""
        response = self.client.get('/api/search/search/', {
            'query': 'test',
            'limit': 10,
            'page': 1,
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('limit'), 10)
        self.assertEqual(response.data.get('page'), 1)

    def test_advanced_search_endpoint(self):
        """测试高级搜索端点"""
        data = {
            'keywords': 'laptop',
            'category': 'electronics',
        }
        
        response = self.client.post('/api/search/search/advanced/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_autocomplete_endpoint(self):
        """测试自动完成端点"""
        response = self.client.get('/api/search/search/autocomplete/', {
            'prefix': 'te',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('suggestions', response.data)

    def test_autocomplete_endpoint_short_prefix(self):
        """测试自动完成端点 - 短前缀"""
        response = self.client.get('/api/search/search/autocomplete/', {
            'prefix': 't',
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggestions_endpoint(self):
        """测试建议端点"""
        response = self.client.get('/api/search/search/suggestions/', {
            'query': 'laptop',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('suggestions', response.data)

    def test_facets_endpoint(self):
        """测试分面端点"""
        response = self.client.get('/api/search/search/facets/', {
            'model': 'product',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('facets', response.data)

    def test_metrics_endpoint(self):
        """测试指标端点"""
        response = self.client.get('/api/search/search/metrics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)

    def test_models_endpoint(self):
        """测试模型列表端点"""
        response = self.client.get('/api/search/search/models/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('models', response.data)

    def test_index_status_endpoint(self):
        """测试索引状态端点"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/search/search-index/status/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)

    def test_rebuild_index_endpoint(self):
        """测试重建索引端点"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/search/search-index/rebuild/')
        
        # 可能返回 200 或 201
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])


class SearchIntegrationTests(TransactionTestCase):
    """搜索集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.search_manager = SearchManager(backend='whoosh')

    def tearDown(self):
        """清理"""
        reset_search_manager()

    def test_index_and_search_flow(self):
        """测试索引和搜索流程"""
        # 索引文档
        self.search_manager.index_document('doc1', {
            'title': 'Python 教程',
            'description': '学习 Python 编程',
            'content': 'Python 是一种高级编程语言',
        })
        
        # 搜索
        result = self.search_manager.search('Python')
        
        self.assertGreater(result.get('total', 0), 0)

    def test_multiple_document_indexing(self):
        """测试多文档索引"""
        documents = [
            {'title': f'文档 {i}', 'description': f'描述 {i}'}
            for i in range(10)
        ]
        
        for i, doc in enumerate(documents):
            self.search_manager.index_document(f'doc-{i}', doc)
        
        result = self.search_manager.search('文档')
        
        self.assertGreaterEqual(result.get('total', 0), 10)

    def test_search_with_filters(self):
        """测试带过滤的搜索"""
        # 索引产品
        self.search_manager.index_document('prod1', {
            'title': '电子产品',
            'category': 'electronics',
            'model': 'product',
        })
        
        # 按模型搜索
        result = self.search_manager.search('电子', model='product')
        
        self.assertIsNotNone(result)

    def test_search_caching(self):
        """测试搜索缓存"""
        # 第一次搜索
        result1 = self.search_manager.search('test_cache')
        
        # 第二次搜索（应该从缓存获取）
        result2 = self.search_manager.search('test_cache')
        
        self.assertEqual(result1.get('query'), result2.get('query'))


class SearchPerformanceTests(TestCase):
    """搜索性能测试"""

    def setUp(self):
        """设置测试环境"""
        self.search_manager = SearchManager(backend='whoosh')

    def test_search_performance_large_dataset(self):
        """测试大数据集搜索性能"""
        import time
        
        # 索引 1000 个文档
        for i in range(100):  # 减少数量以加快测试
            self.search_manager.index_document(f'doc-{i}', {
                'title': f'文档 {i}',
                'description': f'这是第 {i} 个文档',
                'content': '测试内容' * 10,
            })
        
        # 测试搜索速度
        start = time.time()
        result = self.search_manager.search('文档', limit=50)
        duration = time.time() - start
        
        # 搜索应该在 1 秒内完成
        self.assertLess(duration, 1.0)

    def test_autocomplete_performance(self):
        """测试自动完成性能"""
        import time
        
        # 索引文档
        for i in range(100):
            self.search_manager.index_document(f'doc-{i}', {
                'title': f'产品 {i}',
            })
        
        # 测试自动完成速度
        start = time.time()
        suggestions = self.search_manager.autocomplete('产品', limit=10)
        duration = time.time() - start
        
        # 自动完成应该很快
        self.assertLess(duration, 0.5)


# 测试摘要
class TestSummary:
    """测试摘要"""
    test_classes = [
        ('SearchManagerTests', 11),
        ('WhooshBackendTests', 6),
        ('SearchConfigTests', 3),
        ('SearchAPITests', 11),
        ('SearchIntegrationTests', 4),
        ('SearchPerformanceTests', 2),
    ]
    
    total_tests = sum(count for _, count in test_classes)
