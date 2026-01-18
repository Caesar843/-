from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from apps.backup.models import BackupRecord, BackupLog


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    """
    备份记录管理类
    
    提供备份记录的管理界面，包括查看、编辑、删除等操作
    """
    
    list_display = [
        'backup_name',
        'backup_type_badge',
        'status_badge',
        'file_size_display',
        'data_types_display',
        'created_at_display',
        'actions_display'
    ]
    
    list_filter = [
        'status',
        'backup_type',
        'is_automatic',
        'created_at'
    ]
    
    search_fields = [
        'backup_name',
        'description',
    ]
    
    readonly_fields = [
        'backup_name',
        'created_at',
        'backup_start_time',
        'backup_end_time',
        'file_size',
        'file_hash',
        'recovery_records',
        'last_recovered_at',
        'file_path_display',
        'duration_display'
    ]
    
    fieldsets = (
        ('基本信息', {
            'fields': (
                'backup_name',
                'backup_type',
                'status',
                'created_by',
                'is_automatic'
            )
        }),
        ('数据内容', {
            'fields': ('data_types',)
        }),
        ('文件信息', {
            'fields': (
                'file_path_display',
                'file_size',
                'file_hash',
                'is_encrypted',
                'encryption_key_id'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': (
                'created_at',
                'backup_start_time',
                'backup_end_time',
                'duration_display'
            ),
            'classes': ('collapse',)
        }),
        ('恢复信息', {
            'fields': (
                'recovery_records',
                'last_recovered_at'
            ),
            'classes': ('collapse',)
        }),
        ('说明与错误', {
            'fields': (
                'description',
                'error_message'
            ),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """不允许直接添加备份记录，必须通过命令或视图"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """只有超级用户可以删除"""
        return request.user.is_superuser
    
    def backup_type_badge(self, obj):
        """备份类型徽章"""
        colors = {
            'FULL': '#2E86AB',
            'INCREMENTAL': '#A23B72'
        }
        color = colors.get(obj.backup_type, '#666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_backup_type_display()
        )
    backup_type_badge.short_description = '类型'
    
    def status_badge(self, obj):
        """状态徽章"""
        colors = {
            'SUCCESS': '#06A77D',
            'FAILED': '#D62828',
            'RUNNING': '#F77F00',
            'PENDING': '#999'
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    
    def file_size_display(self, obj):
        """文件大小显示"""
        return self._format_size(obj.file_size)
    file_size_display.short_description = '文件大小'
    
    def data_types_display(self, obj):
        """数据类型显示"""
        if not obj.data_types:
            return '-'
        return ', '.join(obj.data_types)
    data_types_display.short_description = '数据类型'
    
    def created_at_display(self, obj):
        """创建时间显示"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = '创建时间'
    
    def file_path_display(self, obj):
        """文件路径显示"""
        return obj.file_path or '-'
    file_path_display.short_description = '文件路径'
    
    def duration_display(self, obj):
        """备份耗时显示"""
        if obj.backup_start_time and obj.backup_end_time:
            duration = obj.backup_end_time - obj.backup_start_time
            return f'{duration.total_seconds():.0f} 秒'
        return '-'
    duration_display.short_description = '耗时'
    
    def actions_display(self, obj):
        """操作链接"""
        if obj.status == 'SUCCESS':
            download_url = reverse('admin:backup_backuprecord_change', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">查看详情</a>',
                download_url
            )
        return '-'
    actions_display.short_description = '操作'
    
    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{size:.2f} TB'


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    """
    备份日志管理类
    
    提供备份操作日志的管理界面
    """
    
    list_display = [
        'backup_record',
        'operation_badge',
        'log_level_badge',
        'message_preview',
        'operated_by',
        'created_at_display'
    ]
    
    list_filter = [
        'operation',
        'log_level',
        'created_at'
    ]
    
    search_fields = [
        'message',
        'backup_record__backup_name'
    ]
    
    readonly_fields = [
        'backup_record',
        'operation',
        'log_level',
        'message',
        'details',
        'operated_by',
        'created_at'
    ]
    
    def has_add_permission(self, request):
        """不允许手动添加日志"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """只有超级用户可以删除"""
        return request.user.is_superuser
    
    def operation_badge(self, obj):
        """操作类型徽章"""
        colors = {
            'BACKUP': '#2E86AB',
            'RESTORE': '#06A77D',
            'VERIFY': '#F77F00',
            'DELETE': '#D62828',
            'DOWNLOAD': '#A23B72'
        }
        color = colors.get(obj.operation, '#666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_operation_display()
        )
    operation_badge.short_description = '操作'
    
    def log_level_badge(self, obj):
        """日志级别徽章"""
        colors = {
            'SUCCESS': '#06A77D',
            'INFO': '#2E86AB',
            'WARNING': '#F77F00',
            'ERROR': '#D62828'
        }
        color = colors.get(obj.log_level, '#666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_log_level_display()
        )
    log_level_badge.short_description = '级别'
    
    def message_preview(self, obj):
        """消息预览"""
        return obj.message[:100] + ('...' if len(obj.message) > 100 else '')
    message_preview.short_description = '消息'
    
    def created_at_display(self, obj):
        """创建时间显示"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = '时间'
