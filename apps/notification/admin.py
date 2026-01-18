from django.contrib import admin
from apps.notification.models import (
    NotificationTemplate,
    Notification,
    SMSRecord,
    NotificationPreference
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'type', 'is_active')
        }),
        ('模板内容', {
            'fields': ('title', 'content', 'variables')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'notification_type', 'status', 'is_read', 'created_at']
    list_filter = ['notification_type', 'status', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'read_at']
    fieldsets = (
        ('接收人信息', {
            'fields': ('recipient', 'is_read', 'read_at')
        }),
        ('通知内容', {
            'fields': ('notification_type', 'template', 'title', 'content')
        }),
        ('业务关联', {
            'fields': ('related_model', 'related_id'),
            'classes': ('collapse',)
        }),
        ('状态跟踪', {
            'fields': ('status', 'sent_at', 'failed_reason'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        count = queryset.filter(is_read=False).update(is_read=True)
        self.message_user(request, f"已标记 {count} 条通知为已读。")
    mark_as_read.short_description = "标记选中通知为已读"


@admin.register(SMSRecord)
class SMSRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone_number', 'status', 'provider', 'created_at', 'sent_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['phone_number', 'content', 'provider_msg_id']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'delivered_at', 'provider_msg_id']
    fieldsets = (
        ('接收信息', {
            'fields': ('phone_number', 'content')
        }),
        ('发送状态', {
            'fields': ('status', 'sent_at', 'delivered_at', 'error_message')
        }),
        ('服务商信息', {
            'fields': ('provider', 'provider_msg_id'),
            'classes': ('collapse',)
        }),
        ('业务关联', {
            'fields': ('notification', 'related_model', 'related_id'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'enable_system_notification', 'enable_sms_notification', 'enable_email_notification']
    list_filter = ['enable_system_notification', 'enable_sms_notification', 'enable_email_notification']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('通知渠道', {
            'fields': ('enable_system_notification', 'enable_sms_notification', 'enable_email_notification')
        }),
        ('短信设置', {
            'fields': ('sms_enabled_hours',),
            'classes': ('collapse',)
        }),
        ('通知内容偏好', {
            'fields': ('notify_contract_events', 'notify_payment_events', 'notify_maintenance_events', 'notify_activity_events')
        }),
        ('支付提醒设置', {
            'fields': ('payment_reminder_days',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
