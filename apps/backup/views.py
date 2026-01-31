import os
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import FileResponse, HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.db.models import Q

from apps.backup.models import BackupRecord, BackupLog
from apps.backup.services import BackupService, RestoreService
from apps.core.mixins import StandardViewMixin
from apps.core.exceptions import BusinessValidationError, StateConflictException


def _get_allowed_backup_roots():
    allowed = getattr(settings, 'BACKUP_ALLOWED_DIRS', None)
    if not allowed:
        allowed = [getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))]
    roots = []
    for entry in allowed:
        expanded = os.path.expanduser(str(entry))
        path = Path(expanded)
        if not path.is_absolute():
            path = Path(settings.BASE_DIR) / path
        roots.append(path)
    return roots


def _is_within_allowed(path, roots):
    target = os.path.normcase(os.path.abspath(str(path)))
    for base in roots:
        base_str = os.path.normcase(os.path.abspath(str(base)))
        try:
            if os.path.commonpath([target, base_str]) == base_str:
                return True
        except ValueError:
            continue
    return False


class AdminRequiredMixin(UserPassesTestMixin):
    """
    管理员权限检查混入类
    
    验证用户是否为管理员，仅管理员可以访问备份管理功能
    """
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff
    
    def handle_no_permission(self):
        messages.error(self.request, '您没有权限访问备份管理功能')
        return redirect('dashboard:index')


class BackupListView(LoginRequiredMixin, AdminRequiredMixin, StandardViewMixin, ListView):
    """
    备份列表视图
    
    显示所有备份记录，支持按状态、类型筛选
    """
    model = BackupRecord
    template_name = 'backup/backup_list.html'
    context_object_name = 'backups'
    paginate_by = 20
    
    def get_queryset(self):
        """获取备份列表，支持筛选"""
        queryset = BackupRecord.objects.all()
        
        # 按状态筛选
        status = self.request.GET.get('status')
        if status and status in ['PENDING', 'RUNNING', 'SUCCESS', 'FAILED']:
            queryset = queryset.filter(status=status)
        
        # 按备份类型筛选
        backup_type = self.request.GET.get('type')
        if backup_type and backup_type in ['FULL', 'INCREMENTAL']:
            queryset = queryset.filter(backup_type=backup_type)
        
        # 按自动/手动筛选
        auto = self.request.GET.get('auto')
        if auto == 'true':
            queryset = queryset.filter(is_automatic=True)
        elif auto == 'false':
            queryset = queryset.filter(is_automatic=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """添加额外的上下文数据"""
        context = super().get_context_data(**kwargs)
        
        # 备份统计信息
        context['total_backups'] = BackupRecord.objects.count()
        context['success_count'] = BackupRecord.objects.filter(status='SUCCESS').count()
        context['failed_count'] = BackupRecord.objects.filter(status='FAILED').count()
        context['total_size'] = sum(b.file_size for b in BackupRecord.objects.filter(status='SUCCESS'))
        
        # 筛选参数
        context['status_filter'] = self.request.GET.get('status', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['auto_filter'] = self.request.GET.get('auto', '')

        # 为模板中的 select option 预计算 selected 属性，避免在模板中做比较
        status = context['status_filter']
        t = context['type_filter']
        a = context['auto_filter']

        context['status_selected_SUCCESS'] = 'selected' if status == 'SUCCESS' else ''
        context['status_selected_FAILED'] = 'selected' if status == 'FAILED' else ''
        context['status_selected_RUNNING'] = 'selected' if status == 'RUNNING' else ''
        context['status_selected_PENDING'] = 'selected' if status == 'PENDING' else ''

        context['type_selected_FULL'] = 'selected' if t == 'FULL' else ''
        context['type_selected_INCREMENTAL'] = 'selected' if t == 'INCREMENTAL' else ''

        context['auto_selected_true'] = 'selected' if a == 'true' else ''
        context['auto_selected_false'] = 'selected' if a == 'false' else ''
        
        return context


class BackupDetailView(LoginRequiredMixin, AdminRequiredMixin, StandardViewMixin, DetailView):
    """
    备份详情视图
    
    显示单个备份的详细信息和操作日志
    """
    model = BackupRecord
    template_name = 'backup/backup_detail.html'
    context_object_name = 'backup'
    
    def get_context_data(self, **kwargs):
        """添加备份日志信息"""
        context = super().get_context_data(**kwargs)
        context['logs'] = self.object.logs.all()[:50]  # 最近50条日志
        return context


class BackupCreateView(LoginRequiredMixin, AdminRequiredMixin, StandardViewMixin, View):
    """
    创建备份视图
    
    支持手动创建全量或增量备份
    """
    
    def get(self, request):
        """显示备份创建表单"""
        default_backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
        return render(request, 'backup/backup_create.html', {
            'default_backup_dir': default_backup_dir
        })
    
    def post(self, request):
        """执行备份操作"""
        try:
            backup_type = request.POST.get('backup_type', 'FULL')
            data_types = request.POST.getlist('data_types')
            description = request.POST.get('description', '')
            backup_name = request.POST.get('backup_name', '').strip()
            backup_dir = request.POST.get('backup_dir', '').strip()
            
            if not data_types:
                data_types = ['SHOP', 'CONTRACT', 'OPERATION', 'FINANCE', 'LOG']
            
            # 创建备份
            service = BackupService()
            backup_record = service.create_backup(
                data_types=data_types,
                backup_type=backup_type,
                user=request.user,
                description=description,
                backup_name=backup_name or None,
                backup_dir=backup_dir or None
            )
            
            download_after = request.POST.get('download_after') == 'on'
            if download_after and backup_record.file_path and os.path.exists(backup_record.file_path):
                BackupLog.objects.create(
                    backup_record=backup_record,
                    operation='DOWNLOAD',
                    log_level='INFO',
                    message='创建备份后下载文件',
                    operated_by=request.user
                )
                return FileResponse(
                    open(backup_record.file_path, 'rb'),
                    as_attachment=True,
                    filename=f'{backup_record.backup_name}.tar.gz'
                )

            messages.success(
                request,
                f'备份 {backup_record.backup_name} 创建成功，'
                f'文件大小: {self._format_size(backup_record.file_size)}'
            )
            
            return redirect('backup:backup_detail', pk=backup_record.pk)
            
        except BusinessValidationError as e:
            messages.error(request, f'备份失败: {str(e)}')
            return redirect('backup:backup_list')
    
    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{size:.2f} TB'


class BackupDirectoryBrowseView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    备份目录选择视图
    """

    def get(self, request):
        roots = _get_allowed_backup_roots()
        if not roots:
            return JsonResponse({'error': '未配置允许的备份目录'}, status=500)

        requested = request.GET.get('path')
        if requested:
            path = Path(os.path.expanduser(requested))
            if not path.is_absolute():
                path = Path(settings.BASE_DIR) / path
        else:
            path = roots[0]

        if not _is_within_allowed(path, roots):
            return JsonResponse({'error': '路径不在允许范围内'}, status=403)
        if not path.exists():
            return JsonResponse({'error': '目录不存在'}, status=404)
        if not path.is_dir():
            return JsonResponse({'error': '路径不是目录'}, status=400)

        entries = []
        try:
            with os.scandir(path) as iterator:
                for entry in iterator:
                    if entry.is_dir():
                        entries.append({
                            'name': entry.name,
                            'path': str(Path(entry.path))
                        })
        except PermissionError:
            return JsonResponse({'error': '无权限访问该目录'}, status=403)

        entries.sort(key=lambda item: item['name'].lower())
        parent = path.parent
        parent_path = str(parent) if _is_within_allowed(parent, roots) else ''

        return JsonResponse({
            'current': str(path),
            'parent': parent_path,
            'entries': entries,
            'roots': [str(root) for root in roots]
        })


class BackupDownloadView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    备份文件下载视图
    
    支持下载备份文件
    """
    
    def get(self, request, pk):
        """下载备份文件"""
        backup = get_object_or_404(BackupRecord, pk=pk)
        
        if backup.status != 'SUCCESS':
            messages.error(request, '该备份未成功完成，无法下载')
            return redirect('backup:backup_detail', pk=backup.pk)
        
        if not os.path.exists(backup.file_path):
            messages.error(request, '备份文件不存在或已删除')
            return redirect('backup:backup_detail', pk=backup.pk)
        
        try:
            # 记录下载日志
            BackupLog.objects.create(
                backup_record=backup,
                operation='DOWNLOAD',
                log_level='INFO',
                message='用户下载备份文件',
                operated_by=request.user
            )
            
            # 返回文件
            response = FileResponse(
                open(backup.file_path, 'rb'),
                as_attachment=True,
                filename=f'{backup.backup_name}.tar.gz'
            )
            return response
            
        except Exception as e:
            messages.error(request, f'下载失败: {str(e)}')
            return redirect('backup:backup_detail', pk=backup.pk)


class BackupRestoreView(LoginRequiredMixin, AdminRequiredMixin, StandardViewMixin, View):
    """
    备份恢复视图
    
    支持从选定的备份文件恢复数据，需要管理员确认
    """
    
    def get(self, request, pk):
        """显示恢复确认页面"""
        backup = get_object_or_404(BackupRecord, pk=pk)
        
        if backup.status != 'SUCCESS':
            messages.error(request, '只能从成功的备份进行恢复')
            return redirect('backup:backup_detail', pk=backup.pk)
        
        return render(request, 'backup/backup_restore_confirm.html', {
            'backup': backup
        })
    
    def post(self, request, pk):
        """执行恢复操作"""
        backup = get_object_or_404(BackupRecord, pk=pk)
        
        # 获取确认信息
        confirm = request.POST.get('confirm') == 'on'
        if not confirm:
            messages.warning(request, '未确认恢复操作，已取消')
            return redirect('backup:backup_detail', pk=backup.pk)
        
        try:
            # 执行恢复
            service = RestoreService()
            restore_stats = service.restore_from_backup(backup, user=request.user)
            
            messages.success(
                request,
                f'数据恢复成功！恢复统计: {restore_stats}'
            )
            
            return redirect('backup:backup_detail', pk=backup.pk)
            
        except (BusinessValidationError, StateConflictException, FileNotFoundError) as e:
            messages.error(request, f'恢复失败: {str(e)}')
            return redirect('backup:backup_detail', pk=backup.pk)


class BackupDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    备份删除视图
    
    支持删除历史备份文件（仅删除已完成的备份）
    """
    
    def post(self, request, pk):
        """删除备份"""
        backup = get_object_or_404(BackupRecord, pk=pk)
        
        # 检查是否可以删除
        if backup.status in ['PENDING', 'RUNNING']:
            messages.error(request, '进行中的备份无法删除')
            return redirect('backup:backup_detail', pk=backup.pk)
        
        try:
            # 删除物理文件
            if os.path.exists(backup.file_path):
                os.remove(backup.file_path)
            
            # 记录日志
            BackupLog.objects.create(
                backup_record=backup,
                operation='DELETE',
                log_level='SUCCESS',
                message='管理员删除备份',
                operated_by=request.user
            )
            
            # 删除数据库记录
            backup_name = backup.backup_name
            backup.delete()
            
            messages.success(request, f'备份 {backup_name} 已删除')
            return redirect('backup:backup_list')
            
        except Exception as e:
            messages.error(request, f'删除失败: {str(e)}')
            return redirect('backup:backup_detail', pk=backup.pk)


class BackupVerifyView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    备份验证视图
    
    验证备份文件的完整性
    """
    
    def post(self, request, pk):
        """验证备份文件"""
        backup = get_object_or_404(BackupRecord, pk=pk)
        
        try:
            # 验证文件是否存在
            if not os.path.exists(backup.file_path):
                raise FileNotFoundError('备份文件不存在')
            
            # 验证文件大小
            actual_size = os.path.getsize(backup.file_path)
            if actual_size != backup.file_size:
                raise StateConflictException(
                    f'文件大小不匹配: 记录{backup.file_size}, 实际{actual_size}'
                )
            
            # 验证文件哈希值
            import hashlib
            file_hash = hashlib.sha256()
            with open(backup.file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    file_hash.update(byte_block)
            
            if file_hash.hexdigest() != backup.file_hash:
                raise StateConflictException('文件哈希值不匹配，文件可能已损坏')
            
            # 记录日志
            BackupLog.objects.create(
                backup_record=backup,
                operation='VERIFY',
                log_level='SUCCESS',
                message='备份文件验证成功',
                operated_by=request.user,
                details={
                    'file_size': backup.file_size,
                    'file_hash': backup.file_hash
                }
            )
            
            messages.success(request, '备份文件验证成功，文件完整无损')
            return JsonResponse({'status': 'success', 'message': '验证成功'})
            
        except (FileNotFoundError, StateConflictException) as e:
            # 记录错误日志
            BackupLog.objects.create(
                backup_record=backup,
                operation='VERIFY',
                log_level='ERROR',
                message=f'备份文件验证失败: {str(e)}',
                operated_by=request.user
            )
            
            messages.error(request, f'验证失败: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class BackupStatsView(LoginRequiredMixin, AdminRequiredMixin, View):
    """
    备份统计视图
    
    返回备份统计数据的JSON响应，用于仪表板展示
    """
    
    def get(self, request):
        """获取备份统计数据"""
        backups = BackupRecord.objects.all()
        
        stats = {
            'total': backups.count(),
            'success': backups.filter(status='SUCCESS').count(),
            'failed': backups.filter(status='FAILED').count(),
            'pending': backups.filter(status='PENDING').count(),
            'running': backups.filter(status='RUNNING').count(),
            'total_size': sum(b.file_size for b in backups.filter(status='SUCCESS')),
            'automatic': backups.filter(is_automatic=True).count(),
            'manual': backups.filter(is_automatic=False).count(),
        }
        
        # 计算平均备份时间
        success_backups = backups.filter(status='SUCCESS')
        if success_backups.exists():
            from django.db.models import F
            total_duration = 0
            for b in success_backups:
                if b.backup_end_time and b.backup_start_time:
                    total_duration += (b.backup_end_time - b.backup_start_time).total_seconds()
            stats['avg_duration'] = total_duration / success_backups.count()
        else:
            stats['avg_duration'] = 0
        
        wants_json = (
            request.GET.get('format') == 'json' or
            'application/json' in request.headers.get('Accept', '')
        )
        if wants_json:
            return JsonResponse(stats)

        return render(request, 'backup/backup_stats.html', {'stats': stats})
