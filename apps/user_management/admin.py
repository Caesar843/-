from django.contrib import admin

from apps.user_management.models import (
    Role,
    UserProfile,
    ObjectPermissionGrant,
    ApprovalRecord,
)


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
