from django.shortcuts import render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
import hashlib

from apps.user_management.models import Role, ObjectPermissionGrant, ApprovalRecord
from apps.store.models import Shop


def _get_user_role(user):
    try:
        return user.profile.role
    except AttributeError:
        return None


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = _get_user_role(user)
    return bool(role and role.role_type == "ADMIN")


def is_shop_member(user, shop):
    if not user or not user.is_authenticated or not shop:
        return False
    if getattr(shop, "owner_id", None) == user.id:
        return True
    user_shops = getattr(user, "shops", None)
    if user_shops is not None:
        try:
            if shop in user_shops.all():
                return True
        except Exception:
            pass
    profile_shop_id = getattr(getattr(user, "profile", None), "shop_id", None)
    if profile_shop_id and getattr(shop, "id", None) == profile_shop_id:
        return True
    return False


def forbidden_response(request, message="Access denied"):
    messages.error(request, message)
    return render(request, "errors/403.html", status=403)


def has_object_permission(user, action, obj, *, allowed_roles=None, allow_shop_owner=False):
    """
    Unified object-level permission check with RBAC fallback.
    """
    if not user or not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True

    role = _get_user_role(user)
    role_type = role.role_type if role else None

    obj_tenant_id = getattr(obj, "tenant_id", None)
    if obj_tenant_id is not None:
        user_tenant_id = getattr(getattr(user, "profile", None), "tenant_id", None)
        if user_tenant_id is None or obj_tenant_id != user_tenant_id:
            return False

    if allowed_roles and role_type in allowed_roles:
        return True

    if allow_shop_owner and role_type == Role.RoleType.SHOP:
        obj_shop = getattr(obj, "shop", None)
        if is_shop_member(user, obj_shop):
            return True

    if not obj:
        return False

    content_type = ContentType.objects.get_for_model(obj.__class__)
    now = timezone.now()

    grant_query = ObjectPermissionGrant.objects.filter(
        content_type=content_type,
        object_id=obj.id,
        action=action,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))

    if role:
        grant_query = grant_query.filter(Q(grantee_user=user) | Q(grantee_role=role))
    else:
        grant_query = grant_query.filter(grantee_user=user)

    return grant_query.exists()


def require_object_permission(request, action, obj, *, allowed_roles=None, allow_shop_owner=False):
    if has_object_permission(
        request.user,
        action,
        obj,
        allowed_roles=allowed_roles,
        allow_shop_owner=allow_shop_owner,
    ):
        return None
    return forbidden_response(request, "Access denied")


def record_approval(*, action, obj, approved_by, comment=None, request_snapshot=None):
    """
    Create an approval record with a lightweight signature hash.
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    approved_at = timezone.now()
    signature_payload = f"{action}|{content_type.id}|{obj.id}|{approved_by.id}|{approved_at.isoformat()}"
    signature_hash = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()

    return ApprovalRecord.objects.create(
        content_type=content_type,
        object_id=obj.id,
        action=action,
        approved_by=approved_by,
        approved_at=approved_at,
        comment=comment or "",
        signature_hash=signature_hash,
        request_snapshot=request_snapshot or {},
    )


def role_required(*allowed_roles):
    """
    Function-based role access decorator.
    """
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                user_role = request.user.profile.role.role_type
            except AttributeError:
                return forbidden_response(request, 'Role not configured')

            if is_admin_user(request.user) or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return forbidden_response(request, 'Access denied')
        return wrapper
    return decorator


class RoleRequiredMixin:
    """
    Role access control mixin.
    """
    allowed_roles = []

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        try:
            user_role = request.user.profile.role.role_type
        except AttributeError:
            return forbidden_response(request, 'Role not configured')

        if is_admin_user(request.user):
            return super().dispatch(request, *args, **kwargs)
        if user_role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        return forbidden_response(request, 'Access denied')


class ShopDataAccessMixin:

    """
    Shop data access control mixin.
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        try:
            user_role = request.user.profile.role.role_type
            user_shop = request.user.profile.shop
        except AttributeError:
            return forbidden_response(request, 'Account configuration incomplete')

        if user_role != Role.RoleType.SHOP:
            return super().dispatch(request, *args, **kwargs)

        if not user_shop:
            return forbidden_response(request, 'No shop bound')

        if 'shop_id' in kwargs:
            shop = Shop.objects.filter(id=kwargs['shop_id']).first()
            if not is_shop_member(request.user, shop):
                return forbidden_response(request, 'Access denied')

        return super().dispatch(request, *args, **kwargs)


class PermissionDeniedView:
    """
    Permission denied view.
    """
    def get(self, request):
        return forbidden_response(request, 'Access denied')
