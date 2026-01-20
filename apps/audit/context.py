from contextvars import ContextVar


_request_context = ContextVar("audit_request_context", default=None)


def set_request_context(user=None, request_id=None, ip_address=None, user_agent=None):
    _request_context.set(
        {
            "user": user,
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
    )


def clear_request_context():
    _request_context.set(None)


def get_request_context():
    return _request_context.get() or {}
