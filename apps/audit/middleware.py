import uuid

from django.utils.deprecation import MiddlewareMixin

from apps.audit.context import clear_request_context, set_request_context


class AuditRequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        ip_address = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        request.request_id = request_id
        set_request_context(
            user=getattr(request, "user", None),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        clear_request_context()
        return response

    def process_exception(self, request, exception):
        clear_request_context()
        return None


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
