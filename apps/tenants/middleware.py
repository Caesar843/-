from apps.tenants.context import set_current_tenant, reset_current_tenant


class TenantMiddleware:
    """
    Resolve the current tenant from the authenticated user and store it
    on the request + context var for queryset scoping.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            if user.is_superuser:
                tenant = None
            else:
                tenant = getattr(user, "tenant", None) or getattr(getattr(user, "profile", None), "tenant", None)

        request.tenant = tenant
        token = set_current_tenant(tenant)
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant(token)
