from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from apps.store.models import Shop, Contract
from apps.finance.models import FinanceRecord
from apps.user_management.permissions import RoleRequiredMixin
from apps.user_management.models import Role


class DashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    数据总览视图
    用于系统级只读展示，汇总已有 Store + Finance 的业务成果
    """
    template_name = 'dashboard/index.html'
    allowed_roles = ['ADMIN', 'FINANCE']

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        try:
            user_role = request.user.profile.role.role_type
            user_shop = request.user.profile.shop
        except AttributeError:
            return HttpResponseForbidden('Account role not configured')

        if user_role == Role.RoleType.SHOP:
            if user_shop:
                return redirect('store:shop_update', user_shop.id)
            return redirect('core:shop_binding_request')

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        """
        统计并传入模板的数据
        """
        context = super().get_context_data(**kwargs)

        # 统计数据
        # 1. 店铺总数（Shop）- 只统计未删除的店铺
        total_shops = Shop.objects.filter(is_deleted=False).count()

        # 2. 合同总数（Contract）
        total_contracts = Contract.objects.count()

        # 3. 生效合同数（ACTIVE）
        active_contracts = Contract.objects.filter(status=Contract.Status.ACTIVE).count()

        # 4. 已收金额总和（Finance 已收）
        paid_amount = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 5. 未收金额总和（Finance 未收）
        unpaid_amount = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 将统计数据传入模板
        context.update({
            'total_shops': total_shops,
            'total_contracts': total_contracts,
            'active_contracts': active_contracts,
            'paid_amount': paid_amount,
            'unpaid_amount': unpaid_amount,
        })

        return context
