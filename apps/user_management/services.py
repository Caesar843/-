from decimal import Decimal
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException, StateConflictException
from apps.store.models import Shop
from apps.tenants.context import get_current_tenant
from apps.user_management.models import (
    ApprovalRecord,
    ObjectPermissionGrant,
    Role,
    ShopBindingRequest,
    UserProfile,
)
from apps.user_management.permissions import record_approval


class ShopBindingApprovalService:
    """
    Service layer for approving or rejecting shop binding requests.
    Ensures transactional consistency across application status, shop upsert, and permission binding.
    """

    DEFAULT_AREA = Decimal("1.00")
    DEFAULT_RENT = Decimal("1.00")

    def approve(self, application_id: int, reviewer: User) -> Tuple[ShopBindingRequest, Shop]:
        """
        Approve a shop binding request.
        - Upserts Shop (dedupe by code, then name+mall_name)
        - Binds applicant as shop owner (profile + object permissions)
        - Records audit info
        """
        with transaction.atomic():
            try:
                app = (
                    ShopBindingRequest.objects.select_for_update()
                    .select_related("user", "approved_shop")
                    .get(id=application_id)
                )
            except ShopBindingRequest.DoesNotExist:
                raise ResourceNotFoundException(message="申请不存在", data={"id": application_id})

            if app.status == ShopBindingRequest.Status.APPROVED and app.approved_shop:
                return app, app.approved_shop
            if app.status == ShopBindingRequest.Status.REJECTED:
                raise StateConflictException(message="已被拒绝的申请不可再次通过")
            if app.status not in [ShopBindingRequest.Status.PENDING]:
                raise StateConflictException(message="仅待审核状态可执行通过操作")

            shop = self._upsert_shop_from_application(app, reviewer)
            self._bind_user_to_shop(app.user, shop, reviewer)

            app.status = ShopBindingRequest.Status.APPROVED
            app.approved_shop = shop
            app.reviewed_by = reviewer
            app.reviewed_at = timezone.now()
            app.review_reason = ""
            app.save(
                update_fields=[
                    "status",
                    "approved_shop",
                    "reviewed_by",
                    "reviewed_at",
                    "review_reason",
                    "updated_at",
                ]
            )

            record_approval(
                action=ApprovalRecord.ActionChoices.SHOP_BINDING_APPROVE,
                obj=app,
                approved_by=reviewer,
                comment="绑定申请通过",
                request_snapshot={
                    "requested_shop_name": app.requested_shop_name,
                    "requested_shop_id": app.requested_shop_id,
                    "mall_name": app.mall_name,
                },
            )

            return app, shop

    def reject(self, application_id: int, reviewer: User, reason: str) -> ShopBindingRequest:
        """
        Reject a shop binding request with mandatory reason.
        """
        if not reason or not reason.strip():
            raise BusinessValidationError(message="拒绝原因不能为空", data={"field": "review_reason"})

        with transaction.atomic():
            try:
                app = ShopBindingRequest.objects.select_for_update().get(id=application_id)
            except ShopBindingRequest.DoesNotExist:
                raise ResourceNotFoundException(message="申请不存在", data={"id": application_id})

            if app.status == ShopBindingRequest.Status.REJECTED:
                return app
            if app.status == ShopBindingRequest.Status.APPROVED:
                raise StateConflictException(message="已通过的申请不可拒绝")

            app.status = ShopBindingRequest.Status.REJECTED
            app.reviewed_by = reviewer
            app.reviewed_at = timezone.now()
            app.review_reason = reason.strip()
            app.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "review_reason",
                    "updated_at",
                ]
            )

            record_approval(
                action=ApprovalRecord.ActionChoices.SHOP_BINDING_REJECT,
                obj=app,
                approved_by=reviewer,
                comment=reason.strip(),
                request_snapshot={
                    "requested_shop_name": app.requested_shop_name,
                    "requested_shop_id": app.requested_shop_id,
                    "mall_name": app.mall_name,
                },
            )
            return app

    # ---------------- internal helpers ---------------- #

    def _map_business_type(self, category: Optional[str]) -> str:
        mapping = {
            "FOOD": Shop.BusinessType.FOOD,
            "RETAIL": Shop.BusinessType.RETAIL,
            "SERVICE": Shop.BusinessType.SERVICE,
            "ENT": Shop.BusinessType.ENTERTAINMENT,
        }
        return mapping.get((category or "").upper(), Shop.BusinessType.OTHER)

    def _get_tenant(self, app: ShopBindingRequest):
        tenant = getattr(getattr(app.user, "profile", None), "tenant", None)
        return tenant or get_current_tenant()

    def _upsert_shop_from_application(self, app: ShopBindingRequest, reviewer: User) -> Shop:
        tenant = self._get_tenant(app)
        if tenant is None:
            raise BusinessValidationError(message="无法确定店铺所属租户，审批前请先为申请人配置租户")
        qs = Shop.objects.filter(is_deleted=False)
        if tenant:
            qs = qs.filter(tenant=tenant)

        normalized_code = (app.requested_shop_id or "").strip()
        normalized_name = (app.requested_shop_name or "").strip()
        normalized_mall = (app.mall_name or "").strip()

        shop: Optional[Shop] = None
        if normalized_code:
            shop = qs.filter(code__iexact=normalized_code).first()
        if not shop and normalized_name:
            if normalized_mall:
                shop = qs.filter(name__iexact=normalized_name, mall_name__iexact=normalized_mall).first()
            else:
                shop = qs.filter(name__iexact=normalized_name).first()

        defaults = {
            "tenant": tenant,
            "name": normalized_name or "未命名店铺",
            "code": normalized_code or None,
            "mall_name": normalized_mall or None,
            "address": (app.address or "")[:255] or None,
            "business_type": self._map_business_type(app.industry_category),
            "contact_person": app.contact_name or "",
            "contact_phone": app.contact_phone or "",
            "description": app.note or app.authorization_note or app.mall_name or "",
            "area": self.DEFAULT_AREA,
            "rent": self.DEFAULT_RENT,
        }

        if shop:
            for field, value in defaults.items():
                if value:
                    setattr(shop, field, value)
            shop.save()
        else:
            shop = Shop.objects.create(**defaults)
        return shop

    def _bind_user_to_shop(self, user: User, shop: Shop, reviewer: User):
        role, _ = Role.objects.get_or_create(
            role_type=Role.RoleType.SHOP,
            defaults={"name": "店铺负责人"},
        )
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        profile.role = role
        profile.shop = shop
        if not profile.tenant and getattr(shop, "tenant", None):
            profile.tenant = shop.tenant
        profile.save(update_fields=["role", "shop", "tenant", "updated_at"])

        content_type = ContentType.objects.get_for_model(shop)
        for action in [
            ObjectPermissionGrant.ActionChoices.VIEW,
            ObjectPermissionGrant.ActionChoices.EDIT,
        ]:
            ObjectPermissionGrant.objects.get_or_create(
                grantee_user=user,
                content_type=content_type,
                object_id=shop.id,
                action=action,
                defaults={"granted_by": reviewer},
            )
