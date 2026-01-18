from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.store.models import Shop, Contract
from apps.finance.models import FinanceRecord
from apps.operations.models import DeviceData, ManualOperationData, OperationAnalysis
from apps.communication.models import MaintenanceRequest, ActivityApplication
from apps.query.forms import ShopQueryForm, OperationQueryForm, FinanceQueryForm, AdminQueryForm

"""
Query App Views
----------------
提供多维度查询功能，包括：
1. 店铺端查询：合约详情、缴费记录、运营数据、事务申请进度
2. 运营专员端查询：分管区域店铺信息、运营数据汇总、事务处理情况
3. 财务管理员端查询：费用收缴明细、未缴费用统计
4. 管理层端查询：商场整体运营数据概览
"""


class ShopQueryView(LoginRequiredMixin, TemplateView):
    """店铺端多维度查询视图"""
    template_name = 'query/shop_query.html'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 获取所有店铺（包括已删除的，因为数据库中所有店铺都被标记为删除了）
        shops = Shop.objects.all()
        context['shops'] = shops
        
        # 如果选择了店铺，获取该店铺的详细信息
        shop_id = self.request.GET.get('shop_id')
        if shop_id:
            try:
                shop = get_object_or_404(Shop, id=shop_id)
                context['selected_shop'] = shop
                
                # 获取店铺的合约信息
                contracts = Contract.objects.filter(shop=shop).order_by('-created_at')
                context['contracts'] = contracts
                
                # 获取店铺的缴费记录
                finance_records = FinanceRecord.objects.filter(
                    contract__shop=shop
                ).order_by('-created_at')
                context['finance_records'] = finance_records
                
                # 获取店铺的运营数据
                operation_data = ManualOperationData.objects.filter(
                    shop=shop
                ).order_by('-data_date')[:30]  # 最近30条
                context['operation_data'] = operation_data
                
                # 获取店铺的事务申请进度
                maintenance_requests = MaintenanceRequest.objects.filter(
                    shop=shop
                ).order_by('-created_at')
                activity_applications = ActivityApplication.objects.filter(
                    shop=shop
                ).order_by('-created_at')
                context['maintenance_requests'] = maintenance_requests
                context['activity_applications'] = activity_applications
                
            except Exception as e:
                messages.error(self.request, f'查询失败: {str(e)}')
        
        return context


class OperationQueryView(LoginRequiredMixin, TemplateView):
    """运营专员端多维度查询视图"""
    template_name = 'query/operation_query.html'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 获取查询参数
        business_type = self.request.GET.get('business_type')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        period = self.request.GET.get('period', 'month')  # 默认按月
        
        # 添加布尔值上下文变量用于模板判断
        context.update({
            'is_retail': business_type == 'RETAIL',
            'is_food': business_type == 'FOOD',
            'is_entertainment': business_type == 'ENTERTAINMENT',
            'is_service': business_type == 'SERVICE',
            'is_other': business_type == 'OTHER',
            'is_week': period == 'week',
            'is_month': period == 'month',
            'is_quarter': period == 'quarter',
            'is_year': period == 'year',
            'is_custom': period == 'custom'
        })
        
        context['period'] = period
        
        # 计算时间范围
        current_date = timezone.now().date()
        if not start_date or not end_date:
            if period == 'week':
                start_date = current_date - timedelta(days=7)
                end_date = current_date
            elif period == 'month':
                start_date = current_date - timedelta(days=30)
                end_date = current_date
            elif period == 'quarter':
                start_date = current_date - timedelta(days=90)
                end_date = current_date
            elif period == 'year':
                start_date = current_date - timedelta(days=365)
                end_date = current_date
            else:  # 默认30天
                start_date = current_date - timedelta(days=30)
                end_date = current_date
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except Exception:
                # 处理无效日期格式
                start_date = current_date - timedelta(days=30)
                end_date = current_date
        
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # 构建查询条件
        shop_filter = Q(is_deleted=False)
        if business_type:
            shop_filter &= Q(business_type=business_type)
        
        # 获取店铺信息
        shops = Shop.objects.filter(shop_filter)
        context['shops'] = shops
        
        # 获取运营数据汇总
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # 获取手动运营数据汇总
                manual_data = ManualOperationData.objects.filter(
                    shop__is_deleted=False,
                    data_date__range=[start_date_obj, end_date_obj]
                ).aggregate(
                    total_sales=Sum('sales_amount'),
                    total_foot_traffic=Sum('foot_traffic'),
                    total_transactions=Sum('transaction_count'),
                    avg_transaction_value=Avg('average_transaction_value')
                )
                context['manual_data_summary'] = manual_data
                
                # 获取设备数据汇总
                device_data = DeviceData.objects.filter(
                    shop__is_deleted=False,
                    data_time__date__range=[start_date_obj, end_date_obj]
                ).values('data_type').annotate(
                    total_value=Sum('value'),
                    avg_value=Avg('value'),
                    count=Count('id')
                )
                context['device_data_summary'] = device_data
                
            except Exception as e:
                messages.error(self.request, f'查询失败: {str(e)}')
        
        # 获取事务处理情况
        maintenance_stats = MaintenanceRequest.objects.filter(
            shop__is_deleted=False
        ).values('status').annotate(count=Count('id'))
        activity_stats = ActivityApplication.objects.filter(
            shop__is_deleted=False
        ).values('status').annotate(count=Count('id'))
        
        # 计算维修请求百分比
        total_maintenance = sum(stat['count'] for stat in maintenance_stats)
        for stat in maintenance_stats:
            percentage = (stat['count'] / total_maintenance * 100) if total_maintenance > 0 else 0
            stat['percentage'] = round(percentage, 1)
        
        # 计算活动申请百分比
        total_activity = sum(stat['count'] for stat in activity_stats)
        for stat in activity_stats:
            percentage = (stat['count'] / total_activity * 100) if total_activity > 0 else 0
            stat['percentage'] = round(percentage, 1)
        
        context['maintenance_stats'] = maintenance_stats
        context['activity_stats'] = activity_stats
        
        return context


class FinanceQueryView(LoginRequiredMixin, TemplateView):
    """财务管理员端多维度查询视图"""
    template_name = 'query/finance_query.html'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 获取查询参数
        fee_type = self.request.GET.get('fee_type')
        status = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        period = self.request.GET.get('period', 'month')  # 默认按月
        
        # 添加布尔值上下文变量用于模板判断
        context.update({
            'is_rent': fee_type == 'RENT',
            'is_property_fee': fee_type == 'PROPERTY_FEE',
            'is_utility_fee': fee_type == 'UTILITY_FEE',
            'is_other_fee': fee_type == 'OTHER',
            'is_unpaid': status == 'UNPAID',
            'is_paid': status == 'PAID',
            'is_void': status == 'VOID',
            'is_week': period == 'week',
            'is_month': period == 'month',
            'is_quarter': period == 'quarter',
            'is_year': period == 'year',
            'is_custom': period == 'custom'
        })
        
        context['period'] = period
        
        # 计算时间范围
        current_date = timezone.now().date()
        if not start_date or not end_date:
            if period == 'week':
                start_date = current_date - timedelta(days=7)
                end_date = current_date
            elif period == 'month':
                start_date = current_date - timedelta(days=30)
                end_date = current_date
            elif period == 'quarter':
                start_date = current_date - timedelta(days=90)
                end_date = current_date
            elif period == 'year':
                start_date = current_date - timedelta(days=365)
                end_date = current_date
            else:  # 默认30天
                start_date = current_date - timedelta(days=30)
                end_date = current_date
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except Exception:
                # 处理无效日期格式
                start_date = current_date - timedelta(days=30)
                end_date = current_date
        
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # 构建查询条件
        finance_filter = Q()
        
        if fee_type:
            finance_filter &= Q(fee_type=fee_type)
        if status:
            finance_filter &= Q(status=status)
        if start_date and end_date:
            try:
                start_date_obj = start_date
                end_date_obj = end_date
                finance_filter &= Q(billing_period_start__range=[start_date_obj, end_date_obj])
            except Exception as e:
                messages.error(self.request, f'日期格式错误: {str(e)}')
        
        # 获取费用收缴明细
        finance_records = FinanceRecord.objects.filter(finance_filter).order_by('-created_at')
        context['finance_records'] = finance_records
        
        # 获取未缴费用统计
        unpaid_records = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID
        ).aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        context['unpaid_records'] = unpaid_records
        
        # 按店铺统计未缴费用
        shop_unpaid_stats = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID
        ).values('contract__shop__name').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        ).order_by('-total_amount')
        context['shop_unpaid_stats'] = shop_unpaid_stats
        
        # 按费用类型统计
        fee_type_stats = FinanceRecord.objects.filter(
            finance_filter
        ).values('fee_type').annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        context['fee_type_stats'] = fee_type_stats
        
        return context


class AdminQueryView(LoginRequiredMixin, TemplateView):
    """管理层端多维度查询视图"""
    template_name = 'query/admin_query.html'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 获取查询参数
        period = self.request.GET.get('period', 'month')  # 默认按月
        business_type = self.request.GET.get('business_type')
        
        # 计算时间范围
        end_date = timezone.now().date()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        # 添加布尔值上下文变量用于模板判断
        context.update({
            'is_retail': business_type == 'RETAIL',
            'is_food': business_type == 'FOOD',
            'is_entertainment': business_type == 'ENTERTAINMENT',
            'is_service': business_type == 'SERVICE',
            'is_other': business_type == 'OTHER'
        })
        
        context['period'] = period
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # 获取商场整体运营数据概览
        try:
            # 店铺统计
            total_shops = Shop.objects.filter(is_deleted=False).count()
            context['total_shops'] = total_shops
            
            # 合约统计
            active_contracts = Contract.objects.filter(status=Contract.Status.ACTIVE).count()
            context['active_contracts'] = active_contracts
            
            # 财务统计
            total_revenue = FinanceRecord.objects.filter(
                status=FinanceRecord.Status.PAID,
                paid_at__date__range=[start_date, end_date]
            ).aggregate(total=Sum('amount'))['total'] or 0
            context['total_revenue'] = total_revenue
            
            unpaid_amount = FinanceRecord.objects.filter(
                status=FinanceRecord.Status.UNPAID
            ).aggregate(total=Sum('amount'))['total'] or 0
            context['unpaid_amount'] = unpaid_amount
            
            # 运营数据统计
            operation_summary = ManualOperationData.objects.filter(
                data_date__range=[start_date, end_date]
            ).aggregate(
                total_sales=Sum('sales_amount'),
                total_foot_traffic=Sum('foot_traffic'),
                avg_transaction_value=Avg('average_transaction_value')
            )
            context['operation_summary'] = operation_summary
            
            # 事务处理统计
            maintenance_total = MaintenanceRequest.objects.count()
            maintenance_completed = MaintenanceRequest.objects.filter(
                status=MaintenanceRequest.Status.COMPLETED
            ).count()
            context['maintenance_total'] = maintenance_total
            context['maintenance_completed'] = maintenance_completed
            
            activity_total = ActivityApplication.objects.count()
            activity_approved = ActivityApplication.objects.filter(
                status=ActivityApplication.Status.APPROVED
            ).count()
            context['activity_total'] = activity_total
            context['activity_approved'] = activity_approved
            
            # 按业态类型统计店铺
            business_type_stats = Shop.objects.filter(
                is_deleted=False
            ).values('business_type').annotate(count=Count('id'))
            context['business_type_stats'] = business_type_stats
            
            # 获取事务处理情况统计
            maintenance_stats = MaintenanceRequest.objects.filter(
                shop__is_deleted=False
            ).values('status').annotate(count=Count('id'))
            activity_stats = ActivityApplication.objects.filter(
                shop__is_deleted=False
            ).values('status').annotate(count=Count('id'))
            
            # 计算维修请求百分比
            total_maintenance = sum(stat['count'] for stat in maintenance_stats)
            for stat in maintenance_stats:
                percentage = (stat['count'] / total_maintenance * 100) if total_maintenance > 0 else 0
                stat['percentage'] = round(percentage, 1)
            
            # 计算活动申请百分比
            total_activity = sum(stat['count'] for stat in activity_stats)
            for stat in activity_stats:
                percentage = (stat['count'] / total_activity * 100) if total_activity > 0 else 0
                stat['percentage'] = round(percentage, 1)
            
            context['maintenance_stats'] = maintenance_stats
            context['activity_stats'] = activity_stats
            
        except Exception as e:
            messages.error(self.request, f'查询失败: {str(e)}')
        
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    """查询功能仪表盘"""
    template_name = 'query/dashboard.html'