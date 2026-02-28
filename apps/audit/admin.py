import csv

from django.contrib import admin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse

from apps.audit.models import AuditLog
from apps.audit.services import verify_audit_chain


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
    actions = ["export_audit_logs_csv", "verify_selected_audit_chains"]

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

    @admin.action(description="Verify selected audit chains")
    def verify_selected_audit_chains(self, request, queryset):
        targets = list(
            queryset.exclude(content_type__isnull=True)
            .exclude(object_id__isnull=True)
            .exclude(object_id="")
            .values_list("content_type_id", "object_id")
            .distinct()[:200]
        )
        if not targets:
            self.message_user(request, "未选择可校验的对象链。", level=messages.WARNING)
            return

        checked = 0
        failures = []
        for content_type_id, object_id in targets:
            checked += 1
            content_type = ContentType.objects.get_for_id(content_type_id)
            result = verify_audit_chain(content_type, object_id)
            if not result.get("ok"):
                failures.append(
                    {
                        "content_type_id": content_type_id,
                        "object_id": object_id,
                        "detail": result,
                    }
                )

        if failures:
            first_failure = failures[0]
            self.message_user(
                request,
                (
                    f"校验完成：{checked} 条对象链，失败 {len(failures)} 条。"
                    f"首个失败对象={first_failure['object_id']}，原因={first_failure['detail'].get('error')}。"
                    "可使用管理命令 verify_audit_chain 进一步排查。"
                ),
                level=messages.ERROR,
            )
            return

        self.message_user(
            request,
            f"校验完成：{checked} 条对象链全部通过。",
            level=messages.SUCCESS,
        )
