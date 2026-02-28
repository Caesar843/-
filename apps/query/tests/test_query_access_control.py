from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.finance.models import FinanceRecord
from apps.store.models import Contract, Shop
from apps.tenants.models import Tenant
from apps.user_management.models import Role


class QueryAccessControlTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Query Tenant A", code="qa")
        cls.tenant_b = Tenant.objects.create(name="Query Tenant B", code="qb")

        cls._ensure_role(Role.RoleType.SHOP)
        cls._ensure_role(Role.RoleType.OPERATION)
        cls._ensure_role(Role.RoleType.FINANCE)
        cls._ensure_role(Role.RoleType.MANAGEMENT)

        cls.shop_a = Shop.objects.create(
            tenant=cls.tenant_a,
            name="Query Shop A",
            business_type=Shop.BusinessType.RETAIL,
            area=Decimal("120.00"),
            rent=Decimal("15000.00"),
        )
        cls.shop_b = Shop.objects.create(
            tenant=cls.tenant_b,
            name="Query Shop B",
            business_type=Shop.BusinessType.FOOD,
            area=Decimal("140.00"),
            rent=Decimal("18000.00"),
        )

        today = timezone.now().date()
        cls.contract_a = Contract.objects.create(
            tenant=cls.tenant_a,
            shop=cls.shop_a,
            start_date=today - timedelta(days=15),
            end_date=today + timedelta(days=180),
            monthly_rent=Decimal("9800.00"),
            deposit=Decimal("10000.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
            status=Contract.Status.ACTIVE,
        )
        cls.contract_b = Contract.objects.create(
            tenant=cls.tenant_b,
            shop=cls.shop_b,
            start_date=today - timedelta(days=15),
            end_date=today + timedelta(days=180),
            monthly_rent=Decimal("9900.00"),
            deposit=Decimal("10000.00"),
            payment_cycle=Contract.PaymentCycle.MONTHLY,
            status=Contract.Status.ACTIVE,
        )

        FinanceRecord.objects.create(
            tenant=cls.tenant_a,
            contract=cls.contract_a,
            amount=Decimal("9800.00"),
            fee_type=FinanceRecord.FeeType.RENT,
            billing_period_start=today - timedelta(days=5),
            billing_period_end=today - timedelta(days=4),
            status=FinanceRecord.Status.UNPAID,
        )
        FinanceRecord.objects.create(
            tenant=cls.tenant_b,
            contract=cls.contract_b,
            amount=Decimal("9900.00"),
            fee_type=FinanceRecord.FeeType.RENT,
            billing_period_start=today - timedelta(days=5),
            billing_period_end=today - timedelta(days=4),
            status=FinanceRecord.Status.UNPAID,
        )

        cls.shop_user = cls._create_user("query_shop", Role.RoleType.SHOP, tenant=cls.tenant_a, shop=cls.shop_a)
        cls.operation_user = cls._create_user("query_op", Role.RoleType.OPERATION, tenant=cls.tenant_a)
        cls.finance_user = cls._create_user("query_fin", Role.RoleType.FINANCE, tenant=cls.tenant_a)
        cls.management_user = cls._create_user("query_mgmt", Role.RoleType.MANAGEMENT, tenant=cls.tenant_a)

    @classmethod
    def _ensure_role(cls, role_type):
        Role.objects.get_or_create(role_type=role_type, defaults={"name": role_type})

    @classmethod
    def _create_user(cls, username, role_type, tenant, shop=None):
        role = Role.objects.get(role_type=role_type)
        user = User.objects.create_user(username=username, password="pass@12345")
        profile = user.profile
        profile.role = role
        profile.tenant = tenant
        profile.shop = shop
        profile.save(update_fields=["role", "tenant", "shop", "updated_at"])
        return user

    def test_shop_user_shop_query_is_scoped_to_bound_shop(self):
        self.client.force_login(self.shop_user)
        response = self.client.get(reverse("query:shop_query"))
        self.assertEqual(response.status_code, 200)
        shop_ids = set(response.context["shops"].values_list("id", flat=True))
        self.assertEqual(shop_ids, {self.shop_a.id})

    def test_shop_user_cannot_access_operation_query(self):
        self.client.force_login(self.shop_user)
        response = self.client.get(reverse("query:operation_query"))
        self.assertEqual(response.status_code, 403)

    def test_operation_query_filters_out_other_tenant_shops(self):
        self.client.force_login(self.operation_user)
        response = self.client.get(reverse("query:operation_query"))
        self.assertEqual(response.status_code, 200)
        shop_ids = set(response.context["shops"].values_list("id", flat=True))
        self.assertIn(self.shop_a.id, shop_ids)
        self.assertNotIn(self.shop_b.id, shop_ids)

    def test_finance_query_is_tenant_scoped(self):
        self.client.force_login(self.finance_user)
        response = self.client.get(reverse("query:finance_query"))
        self.assertEqual(response.status_code, 200)
        record_ids = {record.id for record in response.context["finance_records"]}
        record_tenants = {record.tenant_id for record in response.context["finance_records"]}
        self.assertEqual(record_tenants, {self.tenant_a.id})
        self.assertIn(
            FinanceRecord.objects.get(contract=self.contract_a, tenant=self.tenant_a).id,
            record_ids,
        )
        self.assertNotIn(
            FinanceRecord.objects.get(contract=self.contract_b, tenant=self.tenant_b).id,
            record_ids,
        )

    def test_finance_user_cannot_access_admin_query(self):
        self.client.force_login(self.finance_user)
        response = self.client.get(reverse("query:admin_query"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_exposes_role_based_available_count(self):
        self.client.force_login(self.finance_user)
        response = self.client.get(reverse("query:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["available_query_count"], 1)
        self.assertFalse(response.context["can_view_shop_query"])
        self.assertFalse(response.context["can_view_operation_query"])
        self.assertTrue(response.context["can_view_finance_query"])
        self.assertFalse(response.context["can_view_admin_query"])
