from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException, StateConflictException
from apps.store.models import Shop, Contract
from apps.store.forms import ContractForm
from apps.store.services import ContractService, StoreService
from apps.store.dtos import ContractCreateDTO
from apps.finance.services import FinanceService
from apps.user_management.permissions import RoleRequiredMixin, ShopDataAccessMixin

"""
Store App Views
---------------
[架构职责]
1. 处理 HTTP 请求与响应。
2. 组装 DTO 并调用 Service 层。
3. 映射异常与返回视图/重定向。
"""


class ShopListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """店铺列表视图"""
    model = Shop
    template_name = 'store/shop_list.html'
    context_object_name = 'shops'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']  # 添加 SHOP 角色
    
    def get_queryset(self):
        """只显示未删除的店铺，店铺用户只能看到自己的店铺"""
        queryset = Shop.objects.filter(is_deleted=False)
        # 如果是店铺用户，只显示自己的店铺
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                # 店铺用户未关联店铺，返回空集合
                queryset = queryset.none()
        return queryset


class ShopCreateView(RoleRequiredMixin, CreateView):
    """店铺创建视图"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 保存表单
            instance = form.save()
            
            # 如果是店铺用户创建的店铺，关联到用户
            if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
                self.request.user.profile.shop = instance
                self.request.user.profile.save()
            
            # 添加成功消息
            messages.success(self.request, '店铺创建成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'店铺创建失败: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """处理表单验证失败的情况"""
        messages.error(self.request, '表单验证失败，请检查输入信息')
        return super().form_invalid(form)


class ShopUpdateView(RoleRequiredMixin, ShopDataAccessMixin, UpdateView):
    """店铺编辑视图"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']
    
    def get_queryset(self):
        """店铺用户只能更新自己的店铺"""
        queryset = Shop.objects.filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                # 店铺用户未关联店铺，返回空集合
                queryset = queryset.none()
        return queryset
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        # 调用父类的 form_valid 方法，它会自动保存表单并重定向
        response = super().form_valid(form)
        # 添加成功消息
        messages.success(self.request, '店铺信息更新成功')
        return response
    
    def form_invalid(self, form):
        """处理表单验证失败的情况"""
        # 直接调用父类的 form_invalid 方法，它会自动显示字段错误
        return super().form_invalid(form)


class ContractListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """合同列表视图"""
    model = Contract
    template_name = 'store/contract_list.html'
    context_object_name = 'contracts'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']  # 添加 SHOP 角色
    
    def get_queryset(self):
        """店铺用户只能看到自己店铺的合同"""
        queryset = Contract.objects.all()
        # 如果是店铺用户，只显示自己店铺的合同
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(shop=self.request.user.profile.shop)
            else:
                # 店铺用户未关联店铺，返回空集合
                queryset = queryset.none()
        return queryset


class ContractCreateView(RoleRequiredMixin, CreateView):
    """合同创建视图"""
    model = Contract
    form_class = ContractForm
    template_name = 'store/contract_form.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']  # 添加 SHOP 角色
    
    def get_form(self, form_class=None):
        """重写 get_form 方法，确保不传递 instance 参数给 DTOForm"""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())
    
    def get_form_kwargs(self):
        """重写 get_form_kwargs 方法，移除 instance 参数"""
        kwargs = super().get_form_kwargs()
        # 移除 instance 参数，因为 DTOForm 不接受它
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            cleaned_data = form.cleaned_data
            # 创建DTO
            dto = ContractCreateDTO(
                shop_id=int(cleaned_data['shop']),
                start_date=cleaned_data['start_date'],
                end_date=cleaned_data['end_date'],
                monthly_rent=Decimal(cleaned_data['monthly_rent']),
                deposit=Decimal(cleaned_data['deposit']),
                payment_cycle=cleaned_data['payment_cycle']
            )
            # 调用Service层创建合同
            contract_service = ContractService()
            contract_service.create_draft_contract(dto, self.request.user.id)
            messages.success(self.request, '合同创建成功')
            return redirect(self.success_url)
        except BusinessValidationError as e:
            # 将错误添加到表单中
            form.add_error(e.field, e.message)
            messages.error(self.request, f'验证失败: {e.message}')
            return self.form_invalid(form)
        except ResourceNotFoundException as e:
            messages.error(self.request, f'资源不存在: {e.message}')
            return self.form_invalid(form)
        except StateConflictException as e:
            messages.error(self.request, f'状态冲突: {e.message}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'创建合同失败: {str(e)}')
            return self.form_invalid(form)


class ContractActivateView(RoleRequiredMixin, CreateView):
    """合同激活视图"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']
    
    def get(self, request, *args, **kwargs):
        """处理激活请求"""
        contract = get_object_or_404(Contract, pk=kwargs['pk'])
        if contract.status == Contract.Status.DRAFT:
            contract.status = Contract.Status.ACTIVE
            contract.save()
            messages.success(request, '合同激活成功')
            
            # 合同激活后自动生成财务记录
            try:
                FinanceService.generate_records_for_contract(contract.id)
                messages.success(request, '财务记录已自动生成')
            except Exception as e:
                messages.warning(request, f'财务记录生成失败: {str(e)}')
        else:
            messages.error(request, '只有草稿状态的合同才能被激活')
        return redirect('store:contract_list')


class ContractTerminateView(RoleRequiredMixin, CreateView):
    """合同终止视图"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']
    
    def get(self, request, *args, **kwargs):
        """处理终止请求"""
        contract = get_object_or_404(Contract, pk=kwargs['pk'])
        if contract.status == Contract.Status.ACTIVE:
            contract.status = Contract.Status.TERMINATED
            contract.save()
            messages.success(request, '合同终止成功')
        else:
            messages.error(request, '只有激活状态的合同才能被终止')
        return redirect('store:contract_list')


class ShopDeleteView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    """店铺删除视图"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']
    
    def get(self, request, *args, **kwargs):
        """处理删除请求"""
        try:
            shop_id = kwargs['pk']
            # 调用Service层删除店铺
            store_service = StoreService()
            store_service.delete_shop(shop_id, request.user.id)
            messages.success(request, '店铺删除成功')
            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'验证失败: {e.message}')
            return redirect('store:shop_list')
        except ResourceNotFoundException as e:
            messages.error(request, f'资源不存在: {e.message}')
            return redirect('store:shop_list')
        except Exception as e:
            messages.error(request, f'删除店铺失败: {str(e)}')
            return redirect('store:shop_list')


class ContractDeleteView(RoleRequiredMixin, CreateView):
    """合同删除视图"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']
    
    def get(self, request, *args, **kwargs):
        """处理删除请求"""
        contract = get_object_or_404(Contract, pk=kwargs['pk'])
        if contract.status in [Contract.Status.TERMINATED, Contract.Status.EXPIRED]:
            # 先删除关联的财务记录
            from apps.finance.models import FinanceRecord
            FinanceRecord.objects.filter(contract=contract).delete()
            contract.delete()
            messages.success(request, '合同删除成功')
        else:
            messages.error(request, '只能删除已终止或已过期的合同')
        return redirect('store:contract_list')


class ShopExportView(RoleRequiredMixin, CreateView):
    """店铺导出视图"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']  # 添加 SHOP 角色
    
    def get(self, request, *args, **kwargs):
        """处理导出请求"""
        try:
            # 调用Service层导出店铺
            store_service = StoreService()
            csv_content = store_service.export_shops()
            
            # 设置响应头
            from django.http import HttpResponse
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="shops.csv"'
            return response
        except Exception as e:
            messages.error(request, f'导出失败: {str(e)}')
            return redirect('store:shop_list')


class ShopImportView(RoleRequiredMixin, TemplateView):
    """店铺导入视图"""
    template_name = 'store/shop_import.html'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']
    
    def get(self, request, *args, **kwargs):
        """显示导入表单"""
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """处理导入请求"""
        try:
            if 'csv_file' not in request.FILES:
                messages.error(request, '请选择要导入的CSV文件')
                return redirect('store:shop_import')
            
            csv_file = request.FILES['csv_file']
            file_content = csv_file.read().decode('utf-8')
            
            # 调用Service层导入店铺
            store_service = StoreService()
            result = store_service.import_shops(file_content, request.user.id)
            
            # 显示导入结果
            messages.success(request, f'导入完成：成功 {result["success_count"]} 条，失败 {result["error_count"]} 条')
            
            if result['errors']:
                error_message = '导入失败的记录：\n' + '\n'.join(result['errors'])
                messages.error(request, error_message)
            
            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'验证失败: {e.message}')
            return redirect('store:shop_import')
        except Exception as e:
            messages.error(request, f'导入失败: {str(e)}')
            return redirect('store:shop_import')


class ContractExpiryView(RoleRequiredMixin, TemplateView):
    """合同到期提醒视图"""
    template_name = 'store/contract_expiry.html'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']  # 添加 SHOP 角色
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        # 检查30天内到期的合同
        thirty_days_later = today + timezone.timedelta(days=30)
        
        # 查找即将到期的活跃合同
        expiring_contracts = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=thirty_days_later
        )
        
        # 如果是店铺用户，只显示自己店铺的合同
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                expiring_contracts = expiring_contracts.filter(shop=self.request.user.profile.shop)
            else:
                expiring_contracts = expiring_contracts.none()
        
        expiring_contracts = expiring_contracts.order_by('end_date')
        
        # 查找已过期但状态仍为ACTIVE的合同
        expired_contracts = Contract.objects.filter(
            status=Contract.Status.ACTIVE,
            end_date__lt=today
        )
        
        # 如果是店铺用户，只显示自己店铺的合同
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
