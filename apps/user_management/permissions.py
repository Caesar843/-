from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from apps.user_management.models import Role


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
