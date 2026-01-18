# apps/core/exception_handlers.py

import logging
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings

from apps.core.exceptions import BaseBusinessException, SystemFailureException

logger = logging.getLogger("apps.core.exceptions")


def _is_ajax(request: HttpRequest) -> bool:
    """
    判断是否为 API/AJAX 请求 (工程级实现)

    优先级:
    1. Content-Type: application/json (明确的 API 请求体)
    2. X-Requested-With: XMLHttpRequest (传统 AJAX)
    3. Accept: application/json (且不包含 html，防止浏览器默认行为误判)
    """
    # 1. 检查 Content-Type (通常用于 POST/PUT)
    content_type = request.content_type or ""
    if "application/json" in content_type.lower():
        return True

    # 2. 检查传统 AJAX 头
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return True

    # 3. 检查 Accept 头 (需谨慎，防止浏览器 */* 或包含 html 的情况)
    accept = request.headers.get("accept", "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return True

    return False


def _log_exception(exc: BaseBusinessException):
    """
    统一日志记录策略
    """
    # 使用 __str__ 格式: [ID][CAT][CODE] Internal Msg
    log_msg = str(exc)

    # 系统级故障强制记录堆栈 (exc_info=True)
    # 业务级警告通常不需要堆栈，除非显式要求
    if exc.log_level == 'error':
        logger.error(log_msg, exc_info=True)
    elif exc.log_level == 'warning':
        logger.warning(log_msg)
    else:
        logger.info(log_msg)


def handle_business_exception(request: HttpRequest, exc: BaseBusinessException) -> HttpResponse:
    """
    【响应终结者】统一异常处理入口

    职责：
    1. 记录标准化日志
    2. 终结请求处理流程
    3. 返回最终响应 (JSON 或 HTML Error Page)

    注意：调用此函数后，View 层应直接 return 结果，禁止再执行其他逻辑。
    """

    # 1. 记录日志
    _log_exception(exc)

    # 2. 处理 AJAX / JSON 请求
    if _is_ajax(request):
        return JsonResponse(exc.to_dict(), status=exc.http_status)

    # 3. 处理 Template 页面请求
    # 策略：对于页面请求，异常意味着当前流程无法继续。
    # 我们添加 Flash 消息，并渲染一个通用的错误页面。
    # (注意：表单校验失败通常由 View 内部处理，不会抛出到这里，除非是 View 未捕获的校验异常)

    level_map = {
        'info': messages.INFO,
        'warning': messages.WARNING,
        'error': messages.ERROR
    }
    messages.add_message(request, level_map.get(exc.log_level, messages.ERROR), exc.message)

    # 渲染通用错误页 (templates/error.html)
    # 包含 error_id 方便用户截图反馈
    context = {
        "exception": exc,
        "error_id": exc.error_id,
        "http_status": exc.http_status
    }

    # 尝试使用特定状态码的模板 (如 404.html, 500.html)，否则使用通用 error.html
    template_name = "error.html"
    if exc.http_status in [403, 404, 500]:
        template_name = f"{exc.http_status}.html"

    return render(request, template_name, context, status=exc.http_status)


def handle_unknown_exception(request: HttpRequest, exc: Exception) -> HttpResponse:
    """
    处理未捕获的 Python 原生异常

    增强点：
    1. 提取原始异常类型 (如 KeyError) 到 error_code，便于监控聚合
    2. 保持异常链 (raise from)
    """
    original_type = type(exc).__name__

    # 构造系统级异常，动态生成 error_code (如 SYS_KEY_ERROR)
    # 这样 Sentry/ELK 可以根据 error_code 自动归类问题
    wrapped_exc = SystemFailureException(
        message="系统内部错误，请联系管理员",
        internal_message=f"Uncaught Exception [{original_type}]: {str(exc)}",
        data={"original_exc_type": original_type},
        override_error_code=f"SYS_{original_type.upper()}"  # 动态聚合键
    )

    # 保持原始堆栈信息
    try:
        raise wrapped_exc from exc
    except SystemFailureException as e:
        return handle_business_exception(request, e)


# ============================================
# 业务异常类扩展
# ============================================

class ContractException(BaseBusinessException):
    """
    合同管理异常
    
    用于处理合同创建、修改、签署、过期等相关业务逻辑错误。
    """
    
    category = 'business_logic'
    error_code = 'CONTRACT_ERROR'
    http_status = 400
    log_level = 'warning'


class FinanceException(BaseBusinessException):
    """
    财务管理异常
    
    用于处理账单、支付、发票、报表等财务相关操作的错误。
    """
    
    category = 'business_logic'
    error_code = 'FINANCE_ERROR'
    http_status = 400
    log_level = 'warning'


class NotificationException(BaseBusinessException):
    """
    通知系统异常
    
    用于处理消息发送、邮件通知、短信等通知系统相关的错误。
    """
    
    category = 'system_failure'
    error_code = 'NOTIFICATION_ERROR'
    http_status = 500
    log_level = 'error'


class StoreException(BaseBusinessException):
    """
    店铺管理异常
    
    用于处理店铺创建、修改、审核、上下架等店铺相关的错误。
    """
    
    category = 'business_logic'
    error_code = 'STORE_ERROR'
    http_status = 400
    log_level = 'warning'


class OperationException(BaseBusinessException):
    """
    运营管理异常
    
    用于处理营销活动、促销、数据统计等运营相关的错误。
    """
    
    category = 'business_logic'
    error_code = 'OPERATION_ERROR'
    http_status = 400
    log_level = 'warning'


class ReportException(BaseBusinessException):
    """
    报表系统异常
    
    用于处理报表生成、导出、分析等报表相关的错误。
    """
    
    category = 'business_logic'
    error_code = 'REPORT_ERROR'
    http_status = 400
    log_level = 'warning'


# ============================================
# 装饰器：自动异常处理
# ============================================

def handle_exceptions(view_func):
    """
    视图函数装饰器：自动捕获和处理异常
    
    使用示例：
        @handle_exceptions
        def my_view(request):
            # 业务代码，可能抛出异常
            raise ContractException('合同创建失败')
    """
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except BaseBusinessException as e:
            return handle_business_exception(request, e)
        except Exception as e:
            return handle_unknown_exception(request, e)
    
    return wrapper


def handle_drf_exceptions(view_func):
    """
    DRF 视图装饰器：自动处理异常并返回统一格式
    
    使用示例：
        @handle_drf_exceptions
        def my_api_view(request):
            # API 代码，可能抛出异常
            raise FinanceException('账单创建失败')
    """
    from functools import wraps
    from rest_framework.response import Response
    from rest_framework import status
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except BaseBusinessException as e:
            logger.log(
                getattr(logging, e.log_level.upper()),
                f'{e.category}[{e.error_code}] {e.message}'
            )
            return Response(e.to_dict(), status=e.http_status)
        except Exception as e:
            logger.error(f'Unhandled Exception: {str(e)}', exc_info=True)
            return Response(
                {
                    'code': 500,
                    'message': '服务器内部错误，请稍后重试',
                    'data': None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return wrapper