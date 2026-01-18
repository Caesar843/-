import uuid
from typing import Any, Dict, Optional


class BaseBusinessException(Exception):
    """
    业务异常基类 (Traceability Enhanced)

    核心能力：
    1. 自动生成全链路唯一 error_id (UUID4)
    2. 严格区分 User Message (展示) 与 Internal Message (日志)
    3. 携带工程元数据 (Category, LogLevel, Retry)
    """

    # --- 默认契约 (子类可覆盖) ---
    http_status: int = 500
    error_code: str = "SERVER_ERR"

    # --- 工程元数据 ---
    category: str = "system"  # client_error / business_logic / system_failure
    log_level: str = "error"  # info / warning / error
    should_alert: bool = True
    is_retryable: bool = False

    def __init__(
            self,
            message: str,
            internal_message: Optional[str] = None,
            data: Optional[Dict[str, Any]] = None,
            override_error_code: Optional[str] = None
    ):
        """
        :param message: 用户可见的友好提示
        :param internal_message: 内部日志详情 (若为空则同 message)
        :param data: 上下文数据
        :param override_error_code: 仅用于系统异常动态聚合 (如 SYS_KEY_ERROR)，业务异常禁止使用
        """
        # 1. 强制生成唯一追踪ID (不可外部注入，保证唯一性)
        self.error_id = uuid.uuid4().hex

        self.message = message
        self.internal_message = internal_message or message
        self.data = data or {}

        # 允许特定场景下(如包装未知异常)微调 error_code 以利于监控聚合
        if override_error_code:
            self.error_code = override_error_code

        super().__init__(f"[{self.error_code}] {self.message}")

    def __str__(self) -> str:
        """
        日志标准格式: [ID][CATEGORY][CODE] Internal Message
        """
        return f"[{self.error_id}][{self.category.upper()}][{self.error_code}] {self.internal_message}"

    def to_dict(self) -> Dict[str, Any]:
        """
        API 标准响应格式
        """
        return {
            "success": False,
            "error_id": self.error_id,  # 前端可用于 Feedback
            "error_code": self.error_code,
            "message": self.message,
            "data": self.data,
            "category": self.category
        }


# =============================================================================
# 1. 客户端错误 (Client Errors)
# =============================================================================

class BusinessValidationError(BaseBusinessException):
    http_status = 400
    error_code = "INVALID_PARAM"
    category = "client_error"
    log_level = "warning"
    should_alert = False


class ResourceNotFoundException(BaseBusinessException):
    http_status = 404
    error_code = "RESOURCE_NOT_FOUND"
    category = "client_error"
    log_level = "warning"
    should_alert = False


# =============================================================================
# 2. 业务逻辑错误 (Business Logic Errors)
# =============================================================================

class StateConflictException(BaseBusinessException):
    http_status = 409
    error_code = "STATE_CONFLICT"
    category = "business_logic"
    log_level = "warning"
    should_alert = False


class PermissionDeniedException(BaseBusinessException):
    http_status = 403
    error_code = "PERMISSION_DENIED"
    category = "business_logic"
    log_level = "warning"
    should_alert = False


# =============================================================================
# 3. 系统级故障 (System Failures)
# =============================================================================

class SystemFailureException(BaseBusinessException):
    http_status = 500
    error_code = "SYSTEM_INTERNAL_ERROR"
    category = "system_failure"
    log_level = "error"
    should_alert = True


class ExternalServiceTimeoutException(SystemFailureException):
    http_status = 503
    error_code = "EXTERNAL_SERVICE_TIMEOUT"
    category = "system_failure"
    log_level = "error"
    should_alert = True
    is_retryable = True