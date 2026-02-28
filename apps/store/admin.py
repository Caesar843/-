from django.contrib import admin

from apps.store.models import (
    ApprovalFlowConfig,
    ApprovalTask,
    ContractItem,
    ContractAttachment,
    ContractSignature,
)


@admin.register(ApprovalFlowConfig)
class ApprovalFlowConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "target_type", "node_name", "order_no", "approver_role", "approver", "is_active")
    list_filter = ("target_type", "is_active", "tenant")
    search_fields = ("node_name", "approver_role", "approver__username", "tenant__name", "tenant__code")
    ordering = ("tenant_id", "target_type", "order_no")


@admin.register(ApprovalTask)
class ApprovalTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "contract", "round_no", "order_no", "node_name", "status", "assigned_to", "acted_by")
    list_filter = ("tenant", "status", "round_no")
    search_fields = ("contract__contract_no", "node_name", "assigned_to__username", "acted_by__username")
    ordering = ("-id",)


@admin.register(ContractItem)
class ContractItemAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "contract", "item_type", "calc_type", "amount", "payment_cycle", "status", "sequence")
    list_filter = ("tenant", "item_type", "calc_type", "payment_cycle", "status")
    search_fields = ("contract__contract_no", "contract__shop__name")
    ordering = ("contract_id", "sequence", "id")


@admin.register(ContractAttachment)
class ContractAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "contract",
        "attachment_type",
        "version_no",
        "is_current",
        "file_hash",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("tenant", "attachment_type", "is_current")
    search_fields = ("contract__contract_no", "original_name", "file_hash")
    ordering = ("-created_at", "-id")


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "contract",
        "party_type",
        "signer_name",
        "sign_method",
        "signed_at",
        "created_by",
    )
    list_filter = ("tenant", "party_type", "sign_method")
    search_fields = ("contract__contract_no", "signer_name", "evidence_hash")
    ordering = ("-signed_at", "-id")
