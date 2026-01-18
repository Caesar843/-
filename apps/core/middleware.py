"""
异常处理中间件

捕获所有未被处理的异常，记录到日志并返回适当的错误响应。
"""

import logging
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ExceptionMiddleware:
    """异常处理中间件"""
    
    def __init__(self, get_response):
        """初始化"""
        self.get_response = get_response
    
    def __call__(self, request):
        """处理请求"""
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return self._handle_exception(request, exc)
    
    def _handle_exception(self, request, exception):
        """处理异常"""
        # 记录异常
        logger.error(
            f'未捕获的异常: {type(exception).__name__}: {str(exception)}',
            exc_info=True,
            extra={
                'path': request.path,
                'method': request.method,
                'user': str(request.user),
            }
        )
        
        # 返回错误响应
        if self._is_api_request(request):
            return JsonResponse(
                {
                    'code': 500,
                    'message': '服务器内部错误',
                    'data': None,
                    'error_type': type(exception).__name__,
                },
                status=500
            )
        else:
            # HTML 错误页面
            try:
                from django.shortcuts import render
                return render(
                    request,
                    'errors/500.html',
                    {'error': str(exception)},
                    status=500
                )
            except Exception:
                # 如果模板不存在，返回简单的 HTML
                return JsonResponse(
                    {
                        'code': 500,
                        'message': '服务器内部错误',
                        'error': str(exception),
                    },
                    status=500
                )
    
    @staticmethod
    def _is_api_request(request) -> bool:
        """判断是否是 API 请求"""
        return (
            request.path.startswith('/api/') or
            request.path.startswith('/core/health/') or
            'application/json' in request.headers.get('Accept', '')
        )


def custom_exception_handler(exc, context):
    """
    自定义 DRF 异常处理器
    
    处理所有 Django REST Framework 异常，返回统一格式的响应。
    """
    from rest_framework.views import exception_handler as drf_exception_handler
    
    # 调用 DRF 默认异常处理器
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # 获取错误消息
        error_data = response.data
        
        if isinstance(error_data, dict):
            if 'detail' in error_data:
                message = str(error_data['detail'])
            elif 'non_field_errors' in error_data:
                message = str(error_data['non_field_errors'][0] if error_data['non_field_errors'] else '验证失败')
            else:
                message = '数据验证失败'
        else:
            message = str(error_data)
        
        # 记录错误
        request = context.get('request')
        view = context.get('view')
        
        logger.warning(
            f'API 异常: {type(exc).__name__} - {message}',
            extra={
                'view': view.__class__.__name__ if view else None,
                'status_code': response.status_code,
                'path': request.path if request else None,
            }
        )
        
        # 返回统一格式的响应
        response.data = {
            'code': response.status_code,
            'message': message,
            'data': error_data if isinstance(error_data, dict) and 'detail' not in error_data else None,
            'error_type': type(exc).__name__,
        }
    
    return response
