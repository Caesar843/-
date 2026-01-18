
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.core.exceptions import BaseBusinessException
from apps.core.exception_handlers import handle_business_exception, handle_unknown_exception

class StandardViewMixin:
    """
    核心 View Mixin，所有业务 View 都应继承此类
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except BaseBusinessException as e:
            # 捕获业务异常 -> 交给 handler -> 直接返回 Response
            return handle_business_exception(request, e)
        except Exception as e:
            # 捕获未知异常 -> 交给 handler -> 直接返回 Response
            return handle_unknown_exception(request, e)