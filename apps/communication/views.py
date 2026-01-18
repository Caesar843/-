from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from apps.communication.models import MaintenanceRequest, ActivityApplication, ProcessLog
from apps.communication.forms import ActivityApplicationForm, MaintenanceRequestForm
from apps.store.models import Shop
from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException

"""
Communication App Views
-----------------------
[架构职责]
1. 处理 HTTP 请求与响应。
2. 组装 DTO 并调用 Service 层。
3. 映射异常与返回视图/重定向。
"""


class MaintenanceRequestListView(LoginRequiredMixin, ListView):
    """维修请求列表视图"""
    model = MaintenanceRequest
    template_name = 'communication/maintenance_list.html'
    context_object_name = 'requests'
    
    def get_queryset(self):
        """获取当前店铺的维修请求"""
        user = self.request.user
        # 如果是店铺用户，只显示与自己相关的维修请求
        if hasattr(user, 'profile') and user.profile.role.role_type == 'SHOP':
            # 假设店铺用户与店铺有某种关联，这里需要根据实际情况调整
            # 暂时返回所有维修请求，后续需要根据用户与店铺的关联进行过滤
            return MaintenanceRequest.objects.filter(shop__is_deleted=False)
        # 其他用户可以看到所有维修请求
        return MaintenanceRequest.objects.filter(shop__is_deleted=False)


class MaintenanceRequestCreateView(LoginRequiredMixin, CreateView):
    """维修请求创建视图"""
    model = MaintenanceRequest
    template_name = 'communication/maintenance_form.html'
    fields = ['shop', 'title', 'description', 'request_type', 'priority']
    success_url = '/communication/maintenance/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 保存表单
            instance = form.save()
            
            # 记录流程日志
            ProcessLog.objects.create(
                content_type='MaintenanceRequest',
                object_id=instance.id,
                action='CREATE',
                description=f'创建维修请求: {instance.title}',
                operator=self.request.user.username
            )
            
            messages.success(self.request, '维修请求提交成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'提交失败: {str(e)}')
            return self.form_invalid(form)


class MaintenanceRequestDetailView(LoginRequiredMixin, DetailView):
    """维修请求详情视图"""
    model = MaintenanceRequest
    template_name = 'communication/maintenance_detail.html'
    context_object_name = 'request'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        # 获取相关的流程日志
        logs = ProcessLog.objects.filter(
            content_type='MaintenanceRequest',
            object_id=self.object.id
        ).order_by('-created_at')
        context['logs'] = logs
        return context


class MaintenanceRequestUpdateView(LoginRequiredMixin, UpdateView):
    """维修请求更新视图"""
    model = MaintenanceRequest
    template_name = 'communication/maintenance_form.html'
    fields = ['title', 'description', 'request_type', 'priority', 'status', 'assigned_to', 'estimated_cost', 'actual_cost', 'completion_date']
    success_url = '/communication/maintenance/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 获取原始对象
            original = self.get_object()
            # 保存表单
            instance = form.save()
            
            # 记录状态变更
            if original.status != instance.status:
                ProcessLog.objects.create(
                    content_type='MaintenanceRequest',
                    object_id=instance.id,
                    action='UPDATE',
                    description=f'状态变更: {original.get_status_display()} → {instance.get_status_display()}',
                    operator=self.request.user.username
                )
            
            # 记录指派变更
            if original.assigned_to != instance.assigned_to and instance.assigned_to:
                ProcessLog.objects.create(
                    content_type='MaintenanceRequest',
                    object_id=instance.id,
                    action='ASSIGN',
                    description=f'指派处理人员: {instance.assigned_to}',
                    operator=self.request.user.username
                )
            
            messages.success(self.request, '维修请求更新成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'更新失败: {str(e)}')
            return self.form_invalid(form)


class ActivityApplicationListView(LoginRequiredMixin, ListView):
    """活动申请列表视图"""
    model = ActivityApplication
    template_name = 'communication/activity_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        """获取当前店铺的活动申请"""
        user = self.request.user
        # 如果是店铺用户，只显示与自己相关的活动申请
        if hasattr(user, 'profile') and user.profile.role.role_type == 'SHOP':
            # 假设店铺用户与店铺有某种关联，这里需要根据实际情况调整
            # 暂时返回所有活动申请，后续需要根据用户与店铺的关联进行过滤
            return ActivityApplication.objects.filter(shop__is_deleted=False)
        # 其他用户可以看到所有活动申请
        return ActivityApplication.objects.filter(shop__is_deleted=False)


class ActivityApplicationCreateView(LoginRequiredMixin, CreateView):
    """活动申请创建视图"""
    model = ActivityApplication
    form_class = ActivityApplicationForm
    template_name = 'communication/activity_form.html'
    success_url = '/communication/activities/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 保存表单
            instance = form.save()
            
            # 记录流程日志
            ProcessLog.objects.create(
                content_type='ActivityApplication',
                object_id=instance.id,
                action='CREATE',
                description=f'创建活动申请: {instance.title}',
                operator=self.request.user.username
            )
            
            messages.success(self.request, '活动申请提交成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'提交失败: {str(e)}')
            return self.form_invalid(form)


class ActivityApplicationDetailView(LoginRequiredMixin, DetailView):
    """活动申请详情视图"""
    model = ActivityApplication
    template_name = 'communication/activity_detail.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        """获取上下文数据"""
        context = super().get_context_data(**kwargs)
        # 获取相关的流程日志
        logs = ProcessLog.objects.filter(
            content_type='ActivityApplication',
            object_id=self.object.id
        ).order_by('-created_at')
        context['logs'] = logs
        return context


class ActivityApplicationReviewView(LoginRequiredMixin, UpdateView):
    """活动申请审核视图"""
    model = ActivityApplication
    template_name = 'communication/activity_review.html'
    fields = ['status', 'reviewer', 'review_comments']
    success_url = '/communication/activities/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 获取原始对象
            original = self.get_object()
            # 保存表单
            instance = form.save()
            
            # 记录审核结果
            action = 'APPROVE' if instance.status == ActivityApplication.Status.APPROVED else 'REJECT'
            ProcessLog.objects.create(
                content_type='ActivityApplication',
                object_id=instance.id,
                action=action,
                description=f'审核{instance.get_status_display()}: {instance.review_comments or "无备注"}',
                operator=self.request.user.username
            )
            
            messages.success(self.request, '活动申请审核成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'审核失败: {str(e)}')
            return self.form_invalid(form)


class AdminMaintenanceRequestListView(LoginRequiredMixin, ListView):
    """运营专员维修请求管理视图"""
    model = MaintenanceRequest
    template_name = 'communication/admin_maintenance_list.html'
    context_object_name = 'requests'
    
    def get_queryset(self):
        """获取所有维修请求"""
        return MaintenanceRequest.objects.all().order_by('-created_at')


class AdminActivityApplicationListView(LoginRequiredMixin, ListView):
    """运营专员活动申请管理视图"""
    model = ActivityApplication
    template_name = 'communication/admin_activity_list.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        """获取所有活动申请"""
        return ActivityApplication.objects.all().order_by('-created_at')


class MaintenanceRequestCompleteView(LoginRequiredMixin, UpdateView):
    """维修请求完成视图"""
    model = MaintenanceRequest
    template_name = 'communication/maintenance_complete.html'
    fields = ['actual_cost', 'completion_date']
    success_url = '/communication/maintenance/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 保存表单
            instance = form.save(commit=False)
            instance.status = MaintenanceRequest.Status.COMPLETED
            instance.save()
            
            # 记录完成日志
            ProcessLog.objects.create(
                content_type='MaintenanceRequest',
                object_id=instance.id,
                action='COMPLETE',
                description=f'完成维修请求，实际费用: ¥{instance.actual_cost}',
                operator=self.request.user.username
            )
            
            messages.success(self.request, '维修请求已完成')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'操作失败: {str(e)}')
            return self.form_invalid(form)


class ActivityApplicationCancelView(LoginRequiredMixin, UpdateView):
    """活动申请取消视图"""
    model = ActivityApplication
    template_name = 'communication/activity_cancel.html'
    fields = []
    success_url = '/communication/activities/'
    
    def form_valid(self, form):
        """处理表单验证成功的情况"""
        try:
            # 保存表单
            instance = form.save(commit=False)
            instance.status = ActivityApplication.Status.CANCELLED
            instance.save()
            
            # 记录取消日志
            ProcessLog.objects.create(
                content_type='ActivityApplication',
                object_id=instance.id,
                action='CANCEL',
                description='取消活动申请',
                operator=self.request.user.username
            )
            
            messages.success(self.request, '活动申请已取消')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'操作失败: {str(e)}')
            return self.form_invalid(form)
