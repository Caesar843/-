import csv

from django.contrib import admin
from django.http import HttpResponse

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "module",
        "action",
        "actor",
        "content_type",
        "object_id",
        "ip_address",
        "request_id",
    )
    list_filter = ("module", "action", "content_type", "actor", "created_at")
    search_fields = ("object_id", "request_id", "actor__username", "actor__email")
    readonly_fields = (
        "created_at",
        "current_hash",
        "prev_hash",
    )
    actions = ["export_audit_logs_csv"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_staff:
            return queryset
        return queryset.filter(actor=request.user)

    @admin.action(description="Export selected audit logs to CSV")
    def export_audit_logs_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=audit_logs.csv"

        writer = csv.writer(response)
        writer.writerow(
            [
                "created_at",
                "module",
                "action",
                "actor_id",
                "actor_username",
                "content_type",
                "object_id",
                "ip_address",
                "request_id",
                "before_data",
                "after_data",
                "prev_hash",
                "current_hash",
            ]
        )
        for log in queryset.select_related("actor", "content_type"):
            writer.writerow(
                [
                    log.created_at.isoformat(),
                    log.module,
                    log.action,
                    log.actor_id,
                    log.actor.username if log.actor else "",
                    str(log.content_type) if log.content_type else "",
                    log.object_id or "",
                    log.ip_address or "",
                    log.request_id or "",
                    log.before_data or {},
                    log.after_data or {},
                    log.prev_hash or "",
                    log.current_hash or "",
                ]
            )
        return response
