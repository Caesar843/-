from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException, StateConflictException
from apps.store.models import Shop, Contract
from apps.store.forms import ContractForm
from apps.store.services import ContractService, StoreService
from apps.store.dtos import ContractCreateDTO, ContractActivateDTO
from apps.finance.services import FinanceService
from apps.user_management.permissions import (
    RoleRequiredMixin,
    ShopDataAccessMixin,
    require_object_permission,
)

"""
Store App Views
---------------
[说明]
1. 处理 HTTP 请求
2. ?? DTO ??? Service ??
3. 业务异常处理/提示
"""


class ShopListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    context_object_name = 'shops'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """根据租户与角色过滤数据"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset


class ContractDetailView(LoginRequiredMixin, TemplateView):
    """Contract detail view with object-level permission checks."""
    template_name = "store/contract_detail.html"
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        denied = require_object_permission(
            request,
            "view",
            contract,
            allowed_roles=self.allowed_roles,
            allow_shop_owner=True,
        )
        if denied:
            return denied
        return render(request, self.template_name, {"contract": contract})


class ShopCreateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['ADMIN', 'OPERATION']

    def form_valid(self, form):
        """处理表单"""
        try:
            instance = form.save(commit=False)
            if not instance.tenant_id:
                tenant = getattr(self.request.user, "tenant", None) or getattr(getattr(self.request.user, "profile", None), "tenant", None)
                if tenant is None and self.request.user.is_superuser:
                    from apps.tenants.models import Tenant
                    try:
                        tenant = Tenant.objects.get(code="default")
                    except Tenant.DoesNotExist:
                        tenant = None
                if tenant is not None:
                    instance.tenant = tenant
            instance.save()

            if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
                self.request.user.profile.shop = instance
                self.request.user.profile.save()

            messages.success(self.request, '店铺创建成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'创建失败: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """处理表单"""
        messages.error(self.request, '表单提交失败，请检查输入')
        return super().form_invalid(form)


class ShopUpdateView(RoleRequiredMixin, ShopDataAccessMixin, UpdateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['ADMIN', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """过滤可编辑数据"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset

    def form_valid(self, form):
        """处理表单"""
        response = super().form_valid(form)
        messages.success(self.request, '店铺创建成功')
        return response

    def form_invalid(self, form):
        """处理表单"""
        return super().form_invalid(form)


class ContractListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    context_object_name = 'contracts'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """过滤合同列表"""
        queryset = Contract.objects.for_tenant(self.request.tenant).all()
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(shop=self.request.user.profile.shop)
            else:
                queryset = queryset.none()
        return queryset


class ContractCreateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    form_class = ContractForm
    template_name = 'store/contract_form.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION', 'SHOP']

    def get_form(self, form_class=None):
        """重写 get_form，使用 DTO 表单"""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """重写 get_form_kwargs，移除 instance"""
        kwargs = super().get_form_kwargs()
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs

    def form_valid(self, form):
        """处理表单"""
        try:
            cleaned_data = form.cleaned_data
            dto = ContractCreateDTO(
                shop_id=int(cleaned_data['shop']),
                start_date=cleaned_data['start_date'],
                end_date=cleaned_data['end_date'],
                monthly_rent=Decimal(cleaned_data['monthly_rent']),
                deposit=Decimal(cleaned_data['deposit']),
                payment_cycle=cleaned_data['payment_cycle']
            )
            contract_service = ContractService()
            contract_service.create_draft_contract(dto, self.request.user.id)
            messages.success(self.request, '店铺创建成功')
            return redirect(self.success_url)
        except BusinessValidationError as e:
            form.add_error(e.field, e.message)
            messages.error(self.request, f'创建失败: {e.message}')
            return self.form_invalid(form)
        except ResourceNotFoundException as e:
            messages.error(self.request, f'资源不存在: {e.message}')
            return self.form_invalid(form)
        except StateConflictException as e:
            messages.error(self.request, f'创建失败: {e.message}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'创建失败: {str(e)}')
            return self.form_invalid(form)


class ContractActivateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """处理请求"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        try:
            dto = ContractActivateDTO(contract_id=contract.id)
            ContractService().activate_contract(dto, request.user.id)
            messages.success(request, '合同已激活')
            try:
                FinanceService.generate_records_for_contract(contract.id)
                messages.success(request, '财务记录生成成功')
            except Exception as e:
                messages.warning(request, f'财务记录生成失败: {str(e)}')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'激活失败: {e.message}')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
        return redirect('store:contract_list')


class ContractTerminateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """处理请求"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        try:
            ContractService().terminate_contract(contract.id, request.user.id)
            messages.success(request, '合同已激活')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'激活失败: {e.message}')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
        return redirect('store:contract_list')


class ShopDeleteView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """功能说明"""
        try:
            shop_id = kwargs['pk']
            store_service = StoreService()
            store_service.delete_shop(shop_id, request.user.id)
            messages.success(request, '店铺删除成功')
            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'激活失败: {e.message}')
            return redirect('store:shop_list')
        except ResourceNotFoundException as e:
            messages.error(request, f'资源不存在: {e.message}')
            return redirect('store:shop_list')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_list')


class ContractDeleteView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """功能说明"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        if contract.status in [Contract.Status.TERMINATED, Contract.Status.EXPIRED]:
            from apps.finance.models import FinanceRecord
            FinanceRecord.objects.filter(contract=contract).delete()
            contract.delete()
            messages.success(request, '店铺删除成功')
        else:
            messages.error(request, '合同状态不允许删除')
        return redirect('store:contract_list')


class ShopExportView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get(self, request, *args, **kwargs):
        """功能说明"""
        try:
            store_service = StoreService()
            csv_content = store_service.export_shops()

            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="shops.csv"'
            return response
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_list')


class ShopImportView(RoleRequiredMixin, TemplateView):
    """功能说明"""
    template_name = 'store/shop_import.html'
    allowed_roles = ['ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """功能说明"""
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """功能说明"""
        try:
            if 'csv_file' not in request.FILES:
                messages.error(request, '??? CSV ??')
                return redirect('store:shop_import')

            csv_file = request.FILES['csv_file']
            # 文件大小与类型校验（2MB）
            max_size = 2 * 1024 * 1024
            if csv_file.size > max_size:
                messages.error(request, 'CSV 文件过大（最大 2MB）')
                return redirect('store:shop_import')
            filename = (csv_file.name or '').lower()
            if not filename.endswith('.csv'):
                messages.error(request, '仅支持 .csv 文件')
                return redirect('store:shop_import')
            content_type = (csv_file.content_type or '').lower()
            allowed_types = {'text/csv', 'application/vnd.ms-excel', 'text/plain'}
            if content_type and content_type not in allowed_types:
                messages.error(request, 'CSV 文件类型不受支持')
                return redirect('store:shop_import')
            file_content = csv_file.read().decode('utf-8')

            store_service = StoreService()
            result = store_service.import_shops(file_content, request.user.id)

            messages.success(request, f'Import done: {result["success_count"]} ok, {result["error_count"]} failed')

            if result['errors']:
                error_message = 'Import errors:\n' + '\n'.join(result['errors'])
                messages.error(request, error_message)

            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'激活失败: {e.message}')
            return redirect('store:shop_import')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_import')


class ContractExpiryView(RoleRequiredMixin, TemplateView):
    """合同到期提醒"""
    template_name = 'store/contract_expiry.html'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_context_data(self, **kwargs):
        """获取到期数据"""
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        thirty_days_later = today + timezone.timedelta(days=30)

        expiring_contracts = Contract.objects.for_tenant(self.request.tenant).filter(
            status=Contract.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=thirty_days_later
        )

        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                expiring_contracts = expiring_contracts.filter(shop=self.request.user.profile.shop)
            else:
                expiring_contracts = expiring_contracts.none()

        expiring_contracts = expiring_contracts.order_by('end_date')

        expired_contracts = Contract.objects.for_tenant(self.request.tenant).filter(
            status=Contract.Status.ACTIVE,
            end_date__lt=today
        )

        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                expired_contracts = expired_contracts.filter(shop=self.request.user.profile.shop)
            else:
                expired_contracts = expired_contracts.none()

        expired_contracts = expired_contracts.order_by('end_date')

        context['expiring_contracts'] = expiring_contracts
        context['expired_contracts'] = expired_contracts
        context['today'] = today

        return context
