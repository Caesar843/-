from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException
from apps.finance.models import FinanceRecord
from apps.finance.services import FinanceService
from apps.store.models import Contract, Shop
from apps.tenants.models import Tenant


class FinanceServiceTenantGuardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Finance Tenant A", code="fa")
        cls.tenant_b = Tenant.objects.create(name="Finance Tenant B", code="fb")

        cls.shop_a = Shop.objects.create(
            tenant=cls.tenant_a,
            name="Finance Shop A",
            business_type=Shop.BusinessType.RETAIL,
            area=Decimal("88.00"),
            rent=Decimal("18000.00"),
        )
        cls.shop_b = Shop.objects.create(
            tenant=cls.tenant_b,
            name="Finance Shop B",
            business_type=Shop.BusinessType.FOOD,
            area=Decimal("96.00"),
            rent=Decimal("21000.00"),
        )

        today = timezone.now().date()
        cls.contract_active_a = Contract.objects.create(
            tenant=cls.tenant_a,
            shop=cls.shop_a,
            start_date=today,
            end_date=today + timedelta(days=95),
            monthly_rent=Decimal("9000.00"),
            deposit=Decimal("10000.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
            status=Contract.Status.ACTIVE,
        )
        cls.contract_active_b = Contract.objects.create(
            tenant=cls.tenant_b,
            shop=cls.shop_b,
            start_date=today,
            end_date=today + timedelta(days=95),
            monthly_rent=Decimal("9300.00"),
            deposit=Decimal("12000.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
            status=Contract.Status.ACTIVE,
        )
        cls.contract_draft_a = Contract.objects.create(
            tenant=cls.tenant_a,
            shop=cls.shop_a,
            start_date=today + timedelta(days=120),
            end_date=today + timedelta(days=240),
            monthly_rent=Decimal("9500.00"),
            deposit=Decimal("0.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
            status=Contract.Status.DRAFT,
        )

    def test_generate_records_accepts_correct_tenant_and_tags_records(self):
        records = FinanceService.generate_records_for_contract(
            self.contract_active_a.id,
            tenant_id=self.tenant_a.id,
            operator_id=None,
        )

        self.assertGreaterEqual(len(records), 1)
        record_ids = {record.id for record in records}
        persisted = FinanceRecord.objects.filter(id__in=record_ids)
        self.assertTrue(persisted.exists())
        self.assertTrue(all(record.tenant_id == self.tenant_a.id for record in persisted))
        self.assertTrue(all(record.contract_id == self.contract_active_a.id for record in persisted))

    def test_generate_records_rejects_cross_tenant_access(self):
        with self.assertRaises(ResourceNotFoundException) as cm:
            FinanceService.generate_records_for_contract(
                self.contract_active_a.id,
                tenant_id=self.tenant_b.id,
                operator_id=None,
            )

        self.assertEqual(cm.exception.error_code, "RESOURCE_NOT_FOUND")

    def test_generate_records_rejects_non_active_contract(self):
        with self.assertRaises(BusinessValidationError):
            FinanceService.generate_records_for_contract(
                self.contract_draft_a.id,
                tenant_id=self.tenant_a.id,
                operator_id=None,
            )
