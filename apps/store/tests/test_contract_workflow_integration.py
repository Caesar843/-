from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.core.exceptions import BusinessValidationError, StateConflictException
from apps.store.dtos import ContractActivateDTO, ContractCreateDTO
from apps.store.models import ApprovalFlowConfig, ApprovalTask, Contract, Shop
from apps.store.services import ContractService
from apps.tenants.models import Tenant
from apps.user_management.models import Role


class ContractWorkflowIntegrationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Workflow Tenant", code="wf")
        cls._ensure_role(Role.RoleType.SHOP)
        cls._ensure_role(Role.RoleType.OPERATION)
        cls._ensure_role(Role.RoleType.MANAGEMENT)

        cls.operation_user = cls._create_user("workflow_op", Role.RoleType.OPERATION)
        cls.management_user = cls._create_user("workflow_mgmt", Role.RoleType.MANAGEMENT)

        cls.shop = Shop.objects.create(
            tenant=cls.tenant,
            name="Workflow Shop",
            business_type=Shop.BusinessType.RETAIL,
            area=Decimal("120.00"),
            rent=Decimal("32000.00"),
        )

        ApprovalFlowConfig.objects.create(
            tenant=cls.tenant,
            target_type=ApprovalFlowConfig.TargetType.CONTRACT,
            node_name="运营审批",
            order_no=1,
            approver_role=Role.RoleType.OPERATION,
            is_active=True,
        )
        ApprovalFlowConfig.objects.create(
            tenant=cls.tenant,
            target_type=ApprovalFlowConfig.TargetType.CONTRACT,
            node_name="管理审批",
            order_no=2,
            approver_role=Role.RoleType.MANAGEMENT,
            is_active=True,
        )

    @classmethod
    def _ensure_role(cls, role_type):
        Role.objects.get_or_create(role_type=role_type, defaults={"name": role_type})

    @classmethod
    def _create_user(cls, username, role_type):
        role = Role.objects.get(role_type=role_type)
        user = User.objects.create_user(username=username, password="pass@12345")
        profile = user.profile
        profile.role = role
        profile.tenant = cls.tenant
        profile.save(update_fields=["role", "tenant", "updated_at"])
        return user

    def _create_draft_contract(self):
        today = timezone.now().date()
        dto = ContractCreateDTO(
            shop_id=self.shop.id,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=181),
            monthly_rent=Decimal("10000.00"),
            deposit=Decimal("20000.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
        )
        return ContractService().create_draft_contract(
            dto,
            operator_id=self.operation_user.id,
            tenant_id=self.tenant.id,
        )

    def test_workflow_draft_to_pending_to_approved_to_active(self):
        service = ContractService()
        contract = self._create_draft_contract()
        self.assertEqual(contract.status, Contract.Status.DRAFT)

        service.submit_for_review(contract.id, operator_id=self.operation_user.id, tenant_id=self.tenant.id)
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PENDING_REVIEW)
        self.assertEqual(
            ApprovalTask.objects.filter(contract=contract, status=ApprovalTask.Status.PENDING).count(),
            2,
        )

        service.approve_contract(contract.id, reviewer_id=self.operation_user.id, tenant_id=self.tenant.id)
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PENDING_REVIEW)
        self.assertEqual(
            ApprovalTask.objects.filter(contract=contract, status=ApprovalTask.Status.PENDING).count(),
            1,
        )

        service.approve_contract(contract.id, reviewer_id=self.management_user.id, tenant_id=self.tenant.id)
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.APPROVED)

        service.activate_contract(
            ContractActivateDTO(contract_id=contract.id),
            operator_id=self.operation_user.id,
            tenant_id=self.tenant.id,
        )
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.ACTIVE)

    def test_activate_before_approved_is_blocked_with_error_code(self):
        contract = self._create_draft_contract()
        with self.assertRaises(StateConflictException) as cm:
            ContractService().activate_contract(
                ContractActivateDTO(contract_id=contract.id),
                operator_id=self.operation_user.id,
                tenant_id=self.tenant.id,
            )

        self.assertEqual(cm.exception.error_code, "CONTRACT_STATUS_CONFLICT")
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.DRAFT)

    def test_wrong_role_cannot_approve_current_node(self):
        service = ContractService()
        contract = self._create_draft_contract()
        service.submit_for_review(contract.id, operator_id=self.operation_user.id, tenant_id=self.tenant.id)

        with self.assertRaises(BusinessValidationError) as cm:
            service.approve_contract(contract.id, reviewer_id=self.management_user.id, tenant_id=self.tenant.id)

        self.assertEqual(cm.exception.error_code, "APPROVAL_TASK_ROLE_MISMATCH")
        contract.refresh_from_db()
        self.assertEqual(contract.status, Contract.Status.PENDING_REVIEW)
