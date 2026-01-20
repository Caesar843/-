from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
import hashlib

from apps.user_management.models import Role, ObjectPermissionGrant, ApprovalRecord


def _get_user_role(user):
    try:
        return user.profile.role
    except AttributeError:
        return None


def has_object_permission(user, action, obj, *, allowed_roles=None, allow_shop_owner=False):
    """
    Unified object-level permission check with RBAC fallback.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
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
        user_shop_id = getattr(getattr(user, "profile", None), "shop_id", None)
        obj_shop_id = getattr(getattr(obj, "shop", None), "id", None)
        if user_shop_id and obj_shop_id and user_shop_id == obj_shop_id:
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
    messages.error(request, "鎮ㄦ病鏈夋潈闄愭搷浣滆璧勬簮")
    return HttpResponseForbidden("鎮ㄦ病鏈夋潈闄愭搷浣滆璧勬簮")


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
    角色访问控制装饰器
    ----------------
    用于函数视图，检查用户是否拥有指定角色
    
    Args:
        *allowed_roles: 允许访问的角色类型列表
    """
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            # 获取用户角色
            try:
                user_role = request.user.profile.role.role_type
            except AttributeError:
                messages.error(request, '您的账号未配置角色，请联系管理员')
                return HttpResponseForbidden('您的账号未配置角色，请联系管理员')
            
            # 检查角色是否在允许列表中
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, '您没有权限访问该页面')
                return HttpResponseForbidden('您没有权限访问该页面')
        return wrapper
    return decorator


def shop_data_access_required():
    """
    店铺数据访问控制装饰器
    ----------------------
    确保店铺用户只能访问自己店铺的数据
    """
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            # 获取用户角色
            try:
                user_role = request.user.profile.role.role_type
                user_shop = request.user.profile.shop
            except AttributeError:
                messages.error(request, '您的账号未配置完整，请联系管理员')
                return HttpResponseForbidden('您的账号未配置完整，请联系管理员')
            
            # 非店铺角色可以直接访问
            if user_role != Role.RoleType.SHOP:
                return view_func(request, *args, **kwargs)
            
            # 店铺角色需要检查数据访问权限
            # 这里可以根据具体业务逻辑扩展，例如检查kwargs中的shop_id
            # 示例：如果视图使用shop_id参数，则检查是否匹配用户的shop_id
            if 'shop_id' in kwargs:
                if str(kwargs['shop_id']) != str(user_shop.id):
                    messages.error(request, '您没有权限访问其他店铺的数据')
                    return redirect('dashboard:index')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RoleRequiredMixin:
    """
    角色访问控制混入类
    ----------------
    用于类视图，检查用户是否拥有指定角色
    """
    allowed_roles = []
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        # 获取用户角色
        try:
            user_role = request.user.profile.role.role_type
        except AttributeError:
            messages.error(request, '您的账号未配置角色，请联系管理员')
            # 对于已登录但角色配置不完整的用户，不应重定向到登录页
            # 而应显示错误消息并停留在当前页或返回403
            return HttpResponseForbidden('您的账号未配置角色，请联系管理员')
        
        # 检查角色是否在允许列表中
        if user_role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.error(request, '您没有权限访问该页面')
            return HttpResponseForbidden('您没有权限访问该页面')


class ShopDataAccessMixin:
    """
    店铺数据访问控制混入类
    ----------------------
    确保店铺用户只能访问自己店铺的数据
    """
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        # 获取用户角色
        try:
            user_role = request.user.profile.role.role_type
            user_shop = request.user.profile.shop
        except AttributeError:
            messages.error(request, '您的账号未配置完整，请联系管理员')
            # 对于已登录但配置不完整的用户，不应重定向到登录页
            return HttpResponseForbidden('您的账号未配置完整，请联系管理员')
        
        # 非店铺角色可以直接访问
        if user_role != Role.RoleType.SHOP:
            return super().dispatch(request, *args, **kwargs)
        
        # 店铺角色需要检查数据访问权限
        # 如果是店铺角色但未关联店铺，拒绝访问
        if not user_shop:
            messages.error(request, '您的账号未关联店铺，请联系管理员')
            return HttpResponseForbidden('您的账号未关联店铺，请联系管理员')
        
        # 这里可以根据具体业务逻辑扩展
        if 'shop_id' in kwargs:
            if str(kwargs['shop_id']) != str(user_shop.id):
                messages.error(request, '您没有权限访问其他店铺的数据')
                return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


class PermissionDeniedView:
    """
    权限拒绝视图
    """
    def get(self, request):
        return HttpResponseForbidden("您没有权限访问该资源")
