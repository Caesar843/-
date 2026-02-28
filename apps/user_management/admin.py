from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect

from apps.user_management.models import (
    Role,
    UserProfile,
    ObjectPermissionGrant,
    ApprovalRecord,
    ShopBindingRequest,
)
from apps.user_management.services import ShopBindingApprovalService


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_type", "name", "created_at", "updated_at")
    search_fields = ("role_type", "name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "shop", "phone", "created_at")
    search_fields = ("user__username", "user__email", "phone")
    list_filter = ("role",)


@admin.register(ObjectPermissionGrant)
class ObjectPermissionGrantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "content_type",
        "object_id",
        "grantee_user",
        "grantee_role",
        "valid_from",
        "valid_until",
        "granted_by",
        "created_at",
    )
    list_filter = ("action", "content_type", "grantee_role")
    search_fields = ("object_id", "grantee_user__username", "grantee_role__name")
    raw_id_fields = ("grantee_user", "grantee_role", "granted_by")


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "content_type",
        "object_id",
        "approved_by",
        "approved_at",
        "signature_hash",
    )
    list_filter = ("action", "content_type")
    search_fields = ("object_id", "approved_by__username", "signature_hash")
    raw_id_fields = ("approved_by",)


@admin.register(ShopBindingRequest)
class ShopBindingRequestAdmin(admin.ModelAdmin):
    change_form_template = "admin/user_management/shopbindingrequest/change_form.html"
    list_display = (
        "display_user",
        "display_shop_name",
        "display_mall",
        "display_contact_phone",
        "display_status",
        "approved_shop",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = (
        "status",
        ("created_at", admin.DateFieldListFilter),
        "user",
    )
    search_fields = ("user__username", "requested_shop_name", "contact_phone", "mall_name")
    raw_id_fields = ("user", "approved_shop", "reviewed_by")
    readonly_fields = (
        "user",
        "requested_shop_name",
        "requested_shop_id",
        "mall_name",
        "industry_category",
        "address",
        "contact_name",
        "contact_phone",
        "contact_email",
        "role_requested",
        "authorization_note",
        "note",
        "status",
        "approved_shop",
        "reviewed_by",
        "reviewed_at",
        "review_reason",
        "created_at",
        "updated_at",
        "previous_application",
    )
    date_hierarchy = "created_at"
    service = ShopBindingApprovalService()
    actions = ["action_approve", "action_reject"]

    def has_add_permission(self, request):
        return False

    # --------- 列表展示人性化标题，避免乱码 --------- #
    @admin.display(description="申请人")
    def display_user(self, obj):
        return obj.user

    @admin.display(description="申请店铺名")
    def display_shop_name(self, obj):
        return obj.requested_shop_name

    @admin.display(description="商场/区域")
    def display_mall(self, obj):
        return obj.mall_name

    @admin.display(description="联系电话")
    def display_contact_phone(self, obj):
        return obj.contact_phone

    @admin.display(description="状态")
    def display_status(self, obj):
        return obj.get_status_display()

    # --------- 批量操作 --------- #
    @admin.action(description="审批通过所选申请")
    def action_approve(self, request, queryset):
        success = 0
        errors = []
        for obj in queryset:
            try:
                self.service.approve(obj.id, request.user)
                success += 1
            except Exception as exc:
                errors.append(f"ID {obj.id}: {exc}")
        if success:
            self.message_user(request, f"{success} 条申请已通过", level=messages.SUCCESS)
        if errors:
            self.message_user(request, "；".join(errors), level=messages.ERROR)

    @admin.action(description="拒绝所选申请（需填写原因）")
    def action_reject(self, request, queryset):
        if "apply" in request.POST:
            reason = (request.POST.get("reject_reason") or "").strip()
            if not reason:
                self.message_user(request, "拒绝原因必填", level=messages.ERROR)
                return
            success = 0
            errors = []
            for obj in queryset:
                try:
                    self.service.reject(obj.id, request.user, reason)
                    success += 1
                except Exception as exc:
                    errors.append(f"ID {obj.id}: {exc}")
            if success:
                self.message_user(request, f"{success} 条申请已拒绝", level=messages.SUCCESS)
            if errors:
                self.message_user(request, "；".join(errors), level=messages.ERROR)
            return

        context = {
            **self.admin_site.each_context(request),
            "title": "批量拒绝申请",
            "queryset": queryset,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(
            request,
            "admin/user_management/shopbindingrequest/reject_confirm.html",
            context,
        )

    def response_change(self, request, obj):
        if "_approve" in request.POST:
            try:
                self.service.approve(obj.id, request.user)
                self.message_user(request, "申请已通过并完成店铺绑定", level=messages.SUCCESS)
            except Exception as exc:
                self.message_user(request, f"审批失败：{exc}", level=messages.ERROR)
            return redirect(".")
        if "_reject" in request.POST:
            reason = (request.POST.get("reject_reason") or "").strip()
            try:
                self.service.reject(obj.id, request.user, reason)
                self.message_user(request, "申请已拒绝", level=messages.SUCCESS)
            except Exception as exc:
                self.message_user(request, f"拒绝失败：{exc}", level=messages.ERROR)
            return redirect(".")
        return super().response_change(request, obj)
