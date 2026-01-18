"""
全文搜索 REST API 视图
提供搜索、高级查询、分面导航等接口
"""

import logging
from typing import Dict, Any, Optional

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from apps.core.search_manager import get_search_manager
from apps.core.search_config import (
    get_enabled_searchable_models,
    get_facets_for_model,
    SEARCH_RESULT_FILTERS,
)

logger = logging.getLogger(__name__)


class SearchViewSet(viewsets.ViewSet):
    """搜索 ViewSet"""
    
    permission_classes = [AllowAny]

    def list(self, request):
        """
        基础搜索
        
        Query Parameters:
            - query: 搜索查询 (必需)
            - model: 模型过滤 (可选)
            - limit: 结果数量 (默认 50)
            - page: 分页页码 (默认 1)
        """
        try:
            # 获取查询参数
            query = request.query_params.get('query', '').strip()
            model = request.query_params.get('model')
            limit = int(request.query_params.get('limit', 50))
            page = int(request.query_params.get('page', 1))
            
            # 验证查询
            if not query:
                return Response({
                    'error': '查询参数不能为空',
                    'code': 'empty_query',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(query) > 500:
                return Response({
                    'error': '查询过长，最多 500 个字符',
                    'code': 'query_too_long',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 限制结果数量
            limit = min(limit, 100)
            page = max(page, 1)
            
            # 执行搜索
            search_manager = get_search_manager()
            result = search_manager.search(query, model=model, limit=limit, page=page)
            
            logger.info(f"搜索: {query} (模型: {model}, 分页: {page}/{limit})")
            
            return Response({
                'query': query,
                'model': model,
                'page': page,
                'limit': limit,
                'total': result.get('total', 0),
                'count': result.get('count', 0),
                'results': result.get('results', []),
            })
        except ValueError as e:
            return Response({
                'error': '参数格式错误',
                'code': 'invalid_parameters',
                'details': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return Response({
                'error': '搜索失败',
                'code': 'search_error',
                'details': str(e) if settings.DEBUG else None,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def advanced(self, request):
        """
        高级搜索
        
        Request Body:
            {
                "keywords": "laptop",
                "category": "electronics",
                "tags": "new",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "min_price": 500,
                "max_price": 2000,
            }
        """
        try:
            query_dict = request.data
            
            # 验证查询
            if not query_dict.get('keywords') and not any(k in query_dict for k in ['category', 'tags']):
                return Response({
                    'error': '必须提供搜索条件',
                    'code': 'empty_query',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 执行高级搜索
            search_manager = get_search_manager()
            result = search_manager.advanced_search(query_dict)
            
            logger.info(f"高级搜索: {query_dict}")
            
            return Response({
                'query': query_dict,
                'results': result.get('results', []),
                'count': result.get('count', 0),
            })
        except Exception as e:
            logger.error(f"高级搜索失败: {e}")
            return Response({
                'error': '搜索失败',
                'code': 'search_error',
                'details': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        自动完成
        
        Query Parameters:
            - prefix: 搜索前缀 (必需)
            - model: 模型过滤 (可选)
            - limit: 返回建议数 (默认 10)
        """
        try:
            prefix = request.query_params.get('prefix', '').strip()
            model = request.query_params.get('model')
            limit = int(request.query_params.get('limit', 10))
            
            if not prefix:
                return Response({
                    'error': '前缀参数不能为空',
                    'code': 'empty_prefix',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(prefix) < 2:
                return Response({
                    'error': '前缀至少 2 个字符',
                    'code': 'prefix_too_short',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取建议
            search_manager = get_search_manager()
            suggestions = search_manager.autocomplete(prefix, model=model, limit=limit)
            
            logger.debug(f"自动完成: {prefix} (模型: {model})")
            
            return Response({
                'prefix': prefix,
                'model': model,
                'suggestions': suggestions,
                'count': len(suggestions),
            })
        except Exception as e:
            logger.error(f"自动完成失败: {e}")
            return Response({
                'error': '自动完成失败',
                'code': 'autocomplete_error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """
        搜索建议
        
        Query Parameters:
            - query: 搜索查询 (必需)
            - limit: 建议数 (默认 5)
        """
        try:
            query = request.query_params.get('query', '').strip()
            limit = int(request.query_params.get('limit', 5))
            
            if not query:
                return Response({
                    'error': '查询参数不能为空',
                    'code': 'empty_query',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取建议
            search_manager = get_search_manager()
            suggestions = search_manager.get_suggestions(query, limit=limit)
            
            logger.debug(f"搜索建议: {query}")
            
            return Response({
                'query': query,
                'suggestions': suggestions,
                'count': len(suggestions),
            })
        except Exception as e:
            logger.error(f"获取建议失败: {e}")
            return Response({
                'error': '获取建议失败',
                'code': 'suggestions_error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def facets(self, request):
        """
        分面导航
        
        Query Parameters:
            - model: 模型名称 (必需)
            - query: 搜索查询 (可选)
        """
        try:
            model = request.query_params.get('model')
            query = request.query_params.get('query')
            
            if not model:
                return Response({
                    'error': '模型参数不能为空',
                    'code': 'empty_model',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取分面配置
            facets = get_facets_for_model(model)
            
            if not facets:
                return Response({
                    'error': f'模型 {model} 不支持分面',
                    'code': 'facets_not_supported',
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.debug(f"分面导航: {model} (查询: {query})")
            
            return Response({
                'model': model,
                'query': query,
                'facets': facets,
            })
        except Exception as e:
            logger.error(f"获取分面失败: {e}")
            return Response({
                'error': '获取分面失败',
                'code': 'facets_error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        搜索指标
        
        返回搜索统计信息和热门查询
        """
        try:
            search_manager = get_search_manager()
            metrics = search_manager.get_search_metrics()
            
            logger.debug("获取搜索指标")
            
            return Response({
                'metrics': metrics,
            })
        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return Response({
                'error': '获取指标失败',
                'code': 'metrics_error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        获取可搜索的模型列表
        """
        try:
            models = get_enabled_searchable_models()
            
            logger.debug("获取可搜索模型列表")
            
            return Response({
                'models': models,
                'count': len(models),
            })
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return Response({
                'error': '获取模型列表失败',
                'code': 'models_error',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchIndexViewSet(viewsets.ViewSet):
    """搜索索引管理 ViewSet"""
    
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """管理操作需要超级用户权限"""
        if self.action in ['rebuild', 'reset', 'status']:
            return [IsAuthenticated(), ]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def status(self, request):
        """获取索引状态"""
        try:
            search_manager = get_search_manager()
            status_info = search_manager.get_index_status()
            
            logger.info("获取索引状态")
            
            return Response({
                'status': status_info,
            })
        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return Response({
                'error': '获取索引状态失败',
                'code': 'status_error',
                'details': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def rebuild(self, request):
        """重建索引"""
        try:
            search_manager = get_search_manager()
            success = search_manager.rebuild_index()
            
            if success:
                logger.warning(f"索引已重建 by {request.user}")
                return Response({
                    'message': '索引正在重建',
                    'code': 'rebuild_started',
                })
            else:
                return Response({
                    'error': '索引重建失败',
                    'code': 'rebuild_failed',
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return Response({
                'error': '重建索引失败',
                'code': 'rebuild_error',
                'details': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# 简单视图函数
# ============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def search_view(request):
    """简单搜索视图 - 快速访问"""
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'error': '查询参数为空'}, status=400)
        
        search_manager = get_search_manager()
        result = search_manager.search(query, limit=20)
        
        return JsonResponse({
            'query': query,
            'results': result.get('results', []),
            'total': result.get('total', 0),
        })
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return JsonResponse({'error': '搜索失败'}, status=500)


@require_http_methods(["GET"])
def autocomplete_view(request):
    """自动完成视图 - 快速访问"""
    try:
        prefix = request.GET.get('prefix', '').strip()
        if not prefix or len(prefix) < 2:
            return JsonResponse({'suggestions': []})
        
        search_manager = get_search_manager()
        suggestions = search_manager.autocomplete(prefix, limit=10)
        
        return JsonResponse({
            'prefix': prefix,
            'suggestions': suggestions,
        })
    except Exception as e:
        logger.error(f"自动完成失败: {e}")
        return JsonResponse({'suggestions': []}, status=500)


@require_http_methods(["GET"])
def metrics_view(request):
    """搜索指标视图"""
    try:
        search_manager = get_search_manager()
        metrics = search_manager.get_search_metrics()
        
        return JsonResponse({
            'metrics': metrics,
        })
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        return JsonResponse({'error': '获取指标失败'}, status=500)
