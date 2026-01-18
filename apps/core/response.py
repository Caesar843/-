"""
统一 API 响应格式模块

本模块定义了统一的 API 响应结构，所有 API 端点都应使用本模块提供的响应类来确保
返回格式的一致性，便于前端统一处理。

格式示例:
    成功响应:
    {
        "code": 0,
        "message": "操作成功",
        "data": {...}
    }
    
    错误响应:
    {
        "code": -1,
        "message": "操作失败",
        "data": null
    }
"""

import logging
from typing import Any, Dict, Optional, List
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class APIResponse:
    """
    统一 API 响应类
    
    提供各种常见的 API 响应方法，确保返回格式的一致性。
    所有响应都包含以下字段：
    - code: 响应代码（0 表示成功，其他表示失败）
    - message: 响应消息
    - data: 响应数据（可选）
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = '操作成功',
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        返回成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            status_code: HTTP 状态码，默认 200
            
        Returns:
            Response: DRF 响应对象
            
        Example:
            >>> return APIResponse.success(
            ...     data={'id': 1, 'name': 'Test'},
            ...     message='数据获取成功'
            ... )
        """
        return Response(
            {
                'code': 0,
                'message': message,
                'data': data,
            },
            status=status_code
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = '创建成功'
    ) -> Response:
        """
        返回创建成功响应 (201 Created)
        
        Args:
            data: 响应数据
            message: 响应消息
            
        Returns:
            Response: DRF 响应对象
            
        Example:
            >>> return APIResponse.created(
            ...     data={'id': 1, 'name': 'New Item'},
            ...     message='项目创建成功'
            ... )
        """
        return APIResponse.success(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def error(
        message: str = '操作失败',
        code: int = 1,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: Any = None
    ) -> Response:
        """
        返回错误响应
        
        Args:
            message: 错误消息
            code: 错误代码（非 0 值）
            status_code: HTTP 状态码，默认 400
            data: 错误详情数据（可选）
            
        Returns:
            Response: DRF 响应对象
            
        Example:
            >>> return APIResponse.error(
            ...     message='参数校验失败',
            ...     code=1001,
            ...     data={'field': ['必须填写']}
            ... )
        """
        return Response(
            {
                'code': code,
                'message': message,
                'data': data,
            },
            status=status_code
        )
    
    @staticmethod
    def bad_request(
        message: str = '请求参数错误',
        data: Any = None
    ) -> Response:
        """
        返回 400 Bad Request 错误
        
        Args:
            message: 错误消息
            data: 错误详情
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=400,
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data
        )
    
    @staticmethod
    def unauthorized(message: str = '未授权或登录已过期') -> Response:
        """
        返回 401 Unauthorized 错误
        
        Args:
            message: 错误消息
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=401,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(message: str = '无权限访问') -> Response:
        """
        返回 403 Forbidden 错误
        
        Args:
            message: 错误消息
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=403,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def not_found(message: str = '资源不存在') -> Response:
        """
        返回 404 Not Found 错误
        
        Args:
            message: 错误消息
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=404,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def conflict(message: str = '资源冲突') -> Response:
        """
        返回 409 Conflict 错误
        
        Args:
            message: 错误消息
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=409,
            status_code=status.HTTP_409_CONFLICT
        )
    
    @staticmethod
    def server_error(message: str = '服务器内部错误') -> Response:
        """
        返回 500 Server Error 错误
        
        Args:
            message: 错误消息
            
        Returns:
            Response: DRF 响应对象
        """
        return APIResponse.error(
            message=message,
            code=500,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @staticmethod
    def paginated(
        queryset_or_items: Any,
        page_number: int = 1,
        page_size: int = 20,
        serializer_class: Optional[Any] = None,
        many: bool = True
    ) -> Response:
        """
        返回分页响应
        
        Args:
            queryset_or_items: 数据库查询集或项目列表
            page_number: 页码
            page_size: 每页数量
            serializer_class: 序列化器类（如果需要序列化）
            many: 是否序列化多个对象
            
        Returns:
            Response: 包含分页信息的响应对象
            
        Example:
            >>> return APIResponse.paginated(
            ...     queryset=Contract.objects.all(),
            ...     page_number=request.query_params.get('page', 1),
            ...     page_size=20,
            ...     serializer_class=ContractSerializer
            ... )
        """
        from django.core.paginator import Paginator, EmptyPage
        
        try:
            paginator = Paginator(queryset_or_items, page_size)
            page = paginator.get_page(page_number)
            
            # 序列化数据
            if serializer_class:
                serializer = serializer_class(
                    page.object_list,
                    many=many
                )
                items = serializer.data
            else:
                items = list(page.object_list) if hasattr(page.object_list, '__iter__') else page.object_list
            
            return Response(
                {
                    'code': 0,
                    'message': '获取成功',
                    'data': {
                        'items': items,
                        'pagination': {
                            'total': paginator.count,
                            'page': page_number,
                            'page_size': page_size,
                            'total_pages': paginator.num_pages,
                            'has_next': page.has_next(),
                            'has_previous': page.has_previous(),
                        }
                    }
                },
                status=status.HTTP_200_OK
            )
        except EmptyPage:
            return Response(
                {
                    'code': 0,
                    'message': '获取成功',
                    'data': {
                        'items': [],
                        'pagination': {
                            'total': 0,
                            'page': page_number,
                            'page_size': page_size,
                            'total_pages': 0,
                            'has_next': False,
                            'has_previous': False,
                        }
                    }
                },
                status=status.HTTP_200_OK
            )
    
    @staticmethod
    def list_response(
        items: List[Any],
        message: str = '获取成功',
        total: Optional[int] = None
    ) -> Response:
        """
        返回列表响应
        
        Args:
            items: 项目列表
            message: 响应消息
            total: 总数（可选）
            
        Returns:
            Response: 包含列表的响应对象
            
        Example:
            >>> contracts = Contract.objects.all()
            >>> return APIResponse.list_response(
            ...     items=contracts,
            ...     message='合同列表获取成功'
            ... )
        """
        data = {
            'items': items,
            'total': total or len(items)
        }
        
        return APIResponse.success(
            data=data,
            message=message
        )
    
    @staticmethod
    def validation_error(
        errors: Dict[str, List[str]],
        message: str = '参数校验失败'
    ) -> Response:
        """
        返回数据验证错误响应
        
        Args:
            errors: 错误字典 {字段名: [错误消息]}
            message: 错误消息
            
        Returns:
            Response: 包含验证错误的响应对象
            
        Example:
            >>> return APIResponse.validation_error(
            ...     errors={
            ...         'contract_number': ['合同号已存在'],
            ...         'rent_amount': ['租金必须为正数']
            ...     }
            ... )
        """
        return APIResponse.bad_request(
            message=message,
            data={'errors': errors}
        )
    
    @staticmethod
    def handle_serializer_errors(serializer) -> Response:
        """
        自动处理序列化器验证错误
        
        Args:
            serializer: DRF 序列化器对象
            
        Returns:
            Response: 包含验证错误的响应对象
            
        Example:
            >>> serializer = ContractSerializer(data=request.data)
            >>> if not serializer.is_valid():
            ...     return APIResponse.handle_serializer_errors(serializer)
        """
        return APIResponse.validation_error(
            errors=serializer.errors
        )


# 使用示例
"""
在视图中使用 APIResponse：

from rest_framework.views import APIView
from apps.core.response import APIResponse

class ContractListView(APIView):
    def get(self, request):
        contracts = Contract.objects.all()
        serializer = ContractSerializer(contracts, many=True)
        return APIResponse.success(
            data=serializer.data,
            message='合同列表获取成功'
        )
    
    def post(self, request):
        serializer = ContractSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.handle_serializer_errors(serializer)
        
        serializer.save()
        return APIResponse.created(
            data=serializer.data,
            message='合同创建成功'
        )

class ContractDetailView(APIView):
    def get(self, request, pk):
        try:
            contract = Contract.objects.get(pk=pk)
            serializer = ContractSerializer(contract)
            return APIResponse.success(data=serializer.data)
        except Contract.DoesNotExist:
            return APIResponse.not_found('合同不存在')
    
    def patch(self, request, pk):
        try:
            contract = Contract.objects.get(pk=pk)
            serializer = ContractSerializer(
                contract,
                data=request.data,
                partial=True
            )
            if not serializer.is_valid():
                return APIResponse.handle_serializer_errors(serializer)
            
            serializer.save()
            return APIResponse.success(
                data=serializer.data,
                message='合同更新成功'
            )
        except Contract.DoesNotExist:
            return APIResponse.not_found('合同不存在')
    
    def delete(self, request, pk):
        try:
            contract = Contract.objects.get(pk=pk)
            contract.delete()
            return APIResponse.success(message='合同删除成功')
        except Contract.DoesNotExist:
            return APIResponse.not_found('合同不存在')

# 分页示例
class ContractListPaginatedView(APIView):
    def get(self, request):
        contracts = Contract.objects.all().order_by('-created_at')
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        return APIResponse.paginated(
            queryset_or_items=contracts,
            page_number=page,
            page_size=int(page_size),
            serializer_class=ContractSerializer
        )
"""
