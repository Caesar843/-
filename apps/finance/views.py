from django.views.generic import ListView, View, CreateView
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
from apps.finance.models import FinanceRecord
from apps.finance.forms import FinanceRecordCreateForm
from apps.finance.dtos import FinancePayDTO, FinanceRecordCreateDTO
from apps.finance.services import FinanceService
from apps.store.models import Contract
from apps.user_management.permissions import RoleRequiredMixin, ShopDataAccessMixin
from apps.core.exceptions import BusinessValidationError, StateConflictException, ResourceNotFoundException

"""
Finance App Views
-----------------
[架构职责]
1. 处理 HTTP 请求与响应。
2. 组装 DTO 并调用 Service 层。
3. 映射异常与返回视图/重定向。
"""

class FinanceListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """财务记录列表视图"""
    model = FinanceRecord
    template_name = 'finance/finance_list.html'
    context_object_name = 'finance_records'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'FINANCE', 'SHOP']
    
    def get_queryset(self):
        """重写 get_queryset 方法，支持通过 contract_id 过滤财务记录，店铺用户只能看到自己店铺的财务记录"""
        queryset = super().get_queryset()
        contract_id = self.request.GET.get('contract_id')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
        # 如果是店铺用户，只显示自己店铺的财务记录
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(contract__shop=self.request.user.profile.shop)
            else:
                queryset = queryset.none()
        return queryset

class FinancePayView(RoleRequiredMixin, View):
    """财务记录支付视图"""
    allowed_roles = ['ADMIN', 'FINANCE']
    
    def post(self, request, pk):
        try:
            # 获取缴费方式
            payment_method = request.POST.get('payment_method', 'WECHAT')
            transaction_id = request.POST.get('transaction_id', '')
            
            # 验证支付方式
            if not payment_method:
                messages.error(request, '请选择支付方式')
                return HttpResponseRedirect(reverse('finance:finance_list'))
            
            # 组装 DTO，确保record_id是整数
            dto = FinancePayDTO(record_id=int(pk), payment_method=payment_method, transaction_id=transaction_id)
            
            # 调用 Service 处理支付
            idempotency_key = (
                request.headers.get('Idempotency-Key')
                or request.POST.get('idempotency_key')
            )
            FinanceService.mark_as_paid(dto, request.user.id, idempotency_key)
            
            # 添加成功消息
            messages.success(request, '支付成功！缴费状态已更新为已支付')
            
            # 重定向回列表页
            return HttpResponseRedirect(reverse('finance:finance_list'))
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            # 添加错误消息
            messages.error(request, f'支付失败: {e.message}')
            # 重定向回列表页
            return HttpResponseRedirect(reverse('finance:finance_list'))
        except ValueError as e:
            # 处理类型转换错误（如pk不是有效整数）
            messages.error(request, '无效的记录ID')
            return HttpResponseRedirect(reverse('finance:finance_list'))
        except Exception as e:
            # 捕获其他未预期的异常
            messages.error(request, f'支付失败: {str(e)}')
            return HttpResponseRedirect(reverse('finance:finance_list'))

class FinanceCreateView(RoleRequiredMixin, CreateView):
    """财务记录创建视图"""
    model = FinanceRecord
    template_name = 'finance/finance_form.html'
    form_class = FinanceRecordCreateForm
    success_url = '/finance/records/'
    allowed_roles = ['ADMIN', 'FINANCE']
    
    def get_context_data(self, **kwargs):
        """添加合同列表到上下文"""
        context = super().get_context_data(**kwargs)
        context['contracts'] = Contract.objects.for_tenant(self.request.tenant).all()
        return context
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            cleaned_data = form.cleaned_data
            
            # 组装 DTO
            dto = FinanceRecordCreateDTO(
                contract_id=cleaned_data['contract'].id,
                amount=cleaned_data['amount'],
                fee_type=cleaned_data['fee_type'],
                billing_period_start=str(cleaned_data['billing_period_start']),
                billing_period_end=str(cleaned_data['billing_period_end'])
            )
            
            # 调用 Service
            FinanceService.generate_fee_record(dto, self.request.user.id)
            
            messages.success(self.request, '财务记录创建成功')
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'创建财务记录失败: {str(e)}')
            return self.form_invalid(form)

class FinanceDetailView(RoleRequiredMixin, ShopDataAccessMixin, View):
    """财务记录详情视图"""
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'FINANCE', 'SHOP']
    
    def get(self, request, pk):
        try:
            # 查找财务记录
            record = FinanceRecord.objects.for_tenant(request.tenant).get(id=pk)
            
            # 检查店铺用户是否有权限查看该记录
            if hasattr(request.user, 'profile') and request.user.profile.role.role_type == 'SHOP':
                if not request.user.profile.shop or record.contract.shop != request.user.profile.shop:
                    messages.error(request, '您没有权限访问该财务记录')
                    return HttpResponseRedirect(reverse('finance:finance_list'))
            
            # 渲染详情页面
            context = {'record': record}
            html_content = render_to_string('finance/finance_detail.html', context, request=request)
            return HttpResponse(html_content)
        except Exception as e:
            messages.error(request, f'获取财务记录详情失败: {str(e)}')
            return HttpResponseRedirect(reverse('finance:finance_list'))

class FinanceStatementView(RoleRequiredMixin, ShopDataAccessMixin, View):
    """费用明细单生成视图"""
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'FINANCE', 'SHOP']
    
    def get(self, request, contract_id):
        try:
            # 查找合同
            contract = Contract.objects.for_tenant(request.tenant).get(id=contract_id)
            
            # 检查店铺用户是否有权限查看该合同的明细单
            if hasattr(request.user, 'profile') and request.user.profile.role.role_type == 'SHOP':
                if not request.user.profile.shop or contract.shop != request.user.profile.shop:
                    messages.error(request, '您没有权限访问该合同的费用明细单')
                    return HttpResponseRedirect(reverse('finance:finance_list'))
            
            # 获取合同的所有财务记录
            records = FinanceRecord.objects.for_tenant(request.tenant).filter(contract_id=contract_id)
            
            # 计算汇总信息
            total_amount = sum(record.amount for record in records)
            paid_amount = sum(record.amount for record in records if record.status == FinanceRecord.Status.PAID)
            unpaid_amount = sum(record.amount for record in records if record.status == FinanceRecord.Status.UNPAID)
            
            # 计算支付率
            payment_rate = (paid_amount / total_amount * 100) if total_amount > 0 else 0
            
            # 渲染明细单
            context = {
                'contract': contract,
                'records': records,
                'summary': {
                    'total_amount': total_amount,
                    'paid_amount': paid_amount,
                    'unpaid_amount': unpaid_amount,
                    'payment_rate': round(payment_rate, 2)
                },
                'current_date': timezone.now().date()
            }
            
            # 生成HTML响应
            html_content = render_to_string('finance/finance_statement.html', context, request=request)
            
            # 如果请求PDF格式，可以在这里添加PDF生成逻辑
            if request.GET.get('format') == 'pdf':
                # 这里可以集成PDF生成库，如weasyprint
                pass
            
            return HttpResponse(html_content)
        except Exception as e:
            messages.error(request, f'生成费用明细单失败: {str(e)}')
            return HttpResponseRedirect(reverse('finance:finance_list'))

class FinanceReminderView(RoleRequiredMixin, View):
    """缴费提醒视图"""
    allowed_roles = ['ADMIN', 'FINANCE']
    
    def get(self, request):
        try:
            # 生成缴费提醒
            days_ahead = int(request.GET.get('days_ahead', 7))
            reminders = FinanceService.generate_payment_reminders(days_ahead)
            
            # 渲染提醒页面
            context = {
                'reminders': reminders,
                'days_ahead': days_ahead,
                'current_date': timezone.now().date()
            }
            
            html_content = render_to_string('finance/finance_reminders.html', context, request=request)
            return HttpResponse(html_content)
        except Exception as e:
            messages.error(request, f'生成缴费提醒失败: {str(e)}')
            return HttpResponseRedirect(reverse('finance:finance_list'))

class FinanceHistoryView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """缴费历史视图"""
    model = FinanceRecord
    template_name = 'finance/finance_history.html'
    context_object_name = 'records'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'FINANCE', 'SHOP']
    
    def get_queryset(self):
        """获取已支付的财务记录，店铺用户只能看到自己店铺的缴费历史"""
        queryset = FinanceRecord.objects.filter(status=FinanceRecord.Status.PAID)
        
        # 支持按合同过滤
        contract_id = self.request.GET.get('contract_id')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
        
        # 支持按缴费方式过滤
        payment_method = self.request.GET.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # 支持按日期范围过滤
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
        
        # 如果是店铺用户，只显示自己店铺的缴费历史
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(contract__shop=self.request.user.profile.shop)
            else:
                queryset = queryset.none()
        
        return queryset.order_by('-paid_at')
    
    def get_context_data(self, **kwargs):
        """添加合同列表到上下文"""
        context = super().get_context_data(**kwargs)
        context['contracts'] = Contract.objects.for_tenant(self.request.tenant).all()
        context['contract_id'] = self.request.GET.get('contract_id', '')
        context['payment_method'] = self.request.GET.get('payment_method', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        return context
