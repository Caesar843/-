from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.communication.models import ActivityApplication, MaintenanceRequest
from apps.finance.models import FinanceRecord
from apps.operations.models import DeviceData, ManualOperationData
from apps.store.models import Contract, Shop
from apps.user_management.models import Role
from apps.user_management.permissions import RoleRequiredMixin


def _get_role_type(user):
    return getattr(getattr(getattr(user, "profile", None), "role", None), "role_type", None)


def _get_request_tenant(request):
    return getattr(request, "tenant", None) or getattr(getattr(request.user, "profile", None), "tenant", None)


def _period_flags(period):
    return {
        "is_week": period == "week",
        "is_month": period == "month",
        "is_quarter": period == "quarter",
        "is_year": period == "year",
        "is_custom": period == "custom",
    }


def _resolve_period_range(request, *, default_period="month"):
    period = (request.GET.get("period") or default_period).lower()
    if period not in {"week", "month", "quarter", "year", "custom"}:
        period = default_period

    today = timezone.now().date()
    preset_days = {
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
    }

    raw_start = (request.GET.get("start_date") or "").strip()
    raw_end = (request.GET.get("end_date") or "").strip()
    has_manual_range = bool(raw_start or raw_end)

    if has_manual_range:
        try:
            start_date = datetime.strptime(raw_start, "%Y-%m-%d").date()
            end_date = datetime.strptime(raw_end, "%Y-%m-%d").date()
            if start_date > end_date:
                raise ValueError("start_after_end")
            return ("custom", start_date, end_date, None)
        except ValueError:
            fallback_start = today - timedelta(days=preset_days.get(default_period, 30))
            return (
                default_period,
                fallback_start,
                today,
                "日期范围无效，已回退到默认周期。请使用 YYYY-MM-DD 且开始日期不晚于结束日期。",
            )

    if period == "custom":
        period = default_period

    start_date = today - timedelta(days=preset_days.get(period, 30))
    return (period, start_date, today, None)


def _annotate_percentages(stats):
    rows = list(stats)
    total = sum(item.get("count", 0) for item in rows)
    for item in rows:
        item["percentage"] = round((item.get("count", 0) / total * 100), 1) if total > 0 else 0
    return rows


class QueryAccessMixin(RoleRequiredMixin):
    """查询视图基础能力：角色准入 + 多租户过滤。"""

    allowed_roles = []

    def get_role_type(self):
        return _get_role_type(self.request.user)

    def get_tenant(self):
        return _get_request_tenant(self.request)

    def get_shop_queryset(self):
        tenant = self.get_tenant()
        queryset = Shop.objects.filter(is_deleted=False)
        if tenant is not None:
            queryset = queryset.filter(tenant=tenant)

        if self.get_role_type() == Role.RoleType.SHOP:
            profile_shop_id = getattr(getattr(self.request.user, "profile", None), "shop_id", None)
            if profile_shop_id:
                queryset = queryset.filter(id=profile_shop_id)
            else:
                queryset = queryset.none()

        return queryset

    def get_contract_queryset(self):
        return Contract.objects.for_tenant(self.get_tenant()).filter(is_archived=False)

    def get_finance_queryset(self):
        return FinanceRecord.objects.for_tenant(self.get_tenant())

    def get_manual_data_queryset(self):
        tenant = self.get_tenant()
        queryset = ManualOperationData.objects.filter(shop__is_deleted=False)
        if tenant is not None:
            queryset = queryset.filter(shop__tenant=tenant)
        return queryset

    def get_device_data_queryset(self):
        tenant = self.get_tenant()
        queryset = DeviceData.objects.filter(shop__is_deleted=False)
        if tenant is not None:
            queryset = queryset.filter(shop__tenant=tenant)
        return queryset

    def get_maintenance_queryset(self):
        tenant = self.get_tenant()
        queryset = MaintenanceRequest.objects.filter(shop__is_deleted=False)
        if tenant is not None:
            queryset = queryset.filter(shop__tenant=tenant)
        return queryset

    def get_activity_queryset(self):
        tenant = self.get_tenant()
        queryset = ActivityApplication.objects.filter(shop__is_deleted=False)
        if tenant is not None:
            queryset = queryset.filter(shop__tenant=tenant)
        return queryset


class ShopQueryView(QueryAccessMixin, TemplateView):
    """店铺端多维查询视图。"""

    template_name = "query/shop_query.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "OPERATION", "SHOP"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shops = self.get_shop_queryset().order_by("name")
        context["shops"] = shops

        shop_id = (self.request.GET.get("shop_id") or "").strip()
        if not shop_id:
            return context

        selected_shop = shops.filter(id=shop_id).first()
        if not selected_shop:
            context["shop_selection_error"] = "所选店铺不存在或无权限访问，请重新选择。"
            messages.error(self.request, context["shop_selection_error"])
            return context

        context["selected_shop"] = selected_shop
        context["contracts"] = self.get_contract_queryset().filter(shop=selected_shop).order_by("-created_at")
        context["finance_records"] = (
            self.get_finance_queryset().filter(contract__shop=selected_shop).order_by("-created_at")
        )
        context["operation_data"] = (
            self.get_manual_data_queryset().filter(shop=selected_shop).order_by("-data_date")[:30]
        )
        context["maintenance_requests"] = (
            self.get_maintenance_queryset().filter(shop=selected_shop).order_by("-created_at")
        )
        context["activity_applications"] = (
            self.get_activity_queryset().filter(shop=selected_shop).order_by("-created_at")
        )
        return context


class OperationQueryView(QueryAccessMixin, TemplateView):
    """运营查询视图。"""

    template_name = "query/operation_query.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "OPERATION"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        business_type = (self.request.GET.get("business_type") or "").strip()
        period, start_date, end_date, date_input_error = _resolve_period_range(
            self.request,
            default_period="month",
        )

        context.update(
            {
                "is_retail": business_type == "RETAIL",
                "is_food": business_type == "FOOD",
                "is_entertainment": business_type == "ENTERTAINMENT",
                "is_service": business_type == "SERVICE",
                "is_other": business_type == "OTHER",
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                **_period_flags(period),
            }
        )
        if date_input_error:
            context["date_input_error"] = date_input_error
            messages.warning(self.request, date_input_error)

        shops = self.get_shop_queryset()
        if business_type:
            shops = shops.filter(business_type=business_type)
        context["shops"] = shops

        manual_data_queryset = self.get_manual_data_queryset().filter(data_date__range=[start_date, end_date])
        if business_type:
            manual_data_queryset = manual_data_queryset.filter(shop__business_type=business_type)

        context["manual_data_summary"] = manual_data_queryset.aggregate(
            total_sales=Sum("sales_amount"),
            total_foot_traffic=Sum("foot_traffic"),
            total_transactions=Sum("transaction_count"),
            avg_transaction_value=Avg("average_transaction_value"),
        )

        device_data_queryset = self.get_device_data_queryset().filter(data_time__date__range=[start_date, end_date])
        if business_type:
            device_data_queryset = device_data_queryset.filter(shop__business_type=business_type)

        context["device_data_summary"] = device_data_queryset.values("data_type").annotate(
            total_value=Sum("value"),
            avg_value=Avg("value"),
            count=Count("id"),
        )

        maintenance_stats_queryset = self.get_maintenance_queryset()
        activity_stats_queryset = self.get_activity_queryset()
        if business_type:
            maintenance_stats_queryset = maintenance_stats_queryset.filter(shop__business_type=business_type)
            activity_stats_queryset = activity_stats_queryset.filter(shop__business_type=business_type)

        context["maintenance_stats"] = _annotate_percentages(
            maintenance_stats_queryset.values("status").annotate(count=Count("id"))
        )
        context["activity_stats"] = _annotate_percentages(
            activity_stats_queryset.values("status").annotate(count=Count("id"))
        )
        return context


class FinanceQueryView(QueryAccessMixin, TemplateView):
    """财务查询视图。"""

    template_name = "query/finance_query.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "FINANCE"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fee_type = (self.request.GET.get("fee_type") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        period, start_date, end_date, date_input_error = _resolve_period_range(
            self.request,
            default_period="month",
        )

        context.update(
            {
                "is_rent": fee_type == "RENT",
                "is_property_fee": fee_type == "PROPERTY_FEE",
                "is_utility_fee": fee_type == "UTILITY_FEE",
                "is_other_fee": fee_type == "OTHER",
                "is_unpaid": status == "UNPAID",
                "is_paid": status == "PAID",
                "is_void": status == "VOID",
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                **_period_flags(period),
            }
        )
        if date_input_error:
            context["date_input_error"] = date_input_error
            messages.warning(self.request, date_input_error)

        finance_filter = Q(billing_period_start__range=[start_date, end_date])
        if fee_type:
            finance_filter &= Q(fee_type=fee_type)
        if status:
            finance_filter &= Q(status=status)

        finance_queryset = self.get_finance_queryset()
        context["finance_records"] = finance_queryset.filter(finance_filter).order_by("-created_at")
        context["unpaid_records"] = finance_queryset.filter(status=FinanceRecord.Status.UNPAID).aggregate(
            total_amount=Sum("amount"),
            count=Count("id"),
        )
        context["unpaid_amount"] = context["unpaid_records"].get("total_amount") or 0
        context["shop_unpaid_stats"] = (
            finance_queryset.filter(status=FinanceRecord.Status.UNPAID)
            .values("contract__shop__name")
            .annotate(total_amount=Sum("amount"), count=Count("id"))
            .order_by("-total_amount")
        )
        context["fee_type_stats"] = (
            finance_queryset.filter(finance_filter)
            .values("fee_type")
            .annotate(total_amount=Sum("amount"), count=Count("id"))
        )
        return context


class AdminQueryView(QueryAccessMixin, TemplateView):
    """管理层查询视图。"""

    template_name = "query/admin_query.html"
    allowed_roles = ["ADMIN", "MANAGEMENT"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        period = (self.request.GET.get("period") or "month").lower()
        if period not in {"week", "month", "quarter", "year"}:
            period = "month"
        business_type = (self.request.GET.get("business_type") or "").strip()

        end_date = timezone.now().date()
        days_by_period = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365,
        }
        start_date = end_date - timedelta(days=days_by_period[period])

        context.update(
            {
                "is_retail": business_type == "RETAIL",
                "is_food": business_type == "FOOD",
                "is_entertainment": business_type == "ENTERTAINMENT",
                "is_service": business_type == "SERVICE",
                "is_other": business_type == "OTHER",
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        shop_queryset = self.get_shop_queryset()
        contract_queryset = self.get_contract_queryset()
        finance_queryset = self.get_finance_queryset()
        operation_queryset = self.get_manual_data_queryset()
        maintenance_queryset = self.get_maintenance_queryset()
        activity_queryset = self.get_activity_queryset()

        if business_type:
            shop_queryset = shop_queryset.filter(business_type=business_type)
            contract_queryset = contract_queryset.filter(shop__business_type=business_type)
            finance_queryset = finance_queryset.filter(contract__shop__business_type=business_type)
            operation_queryset = operation_queryset.filter(shop__business_type=business_type)
            maintenance_queryset = maintenance_queryset.filter(shop__business_type=business_type)
            activity_queryset = activity_queryset.filter(shop__business_type=business_type)

        context["total_shops"] = shop_queryset.count()
        context["active_contracts"] = contract_queryset.filter(status=Contract.Status.ACTIVE).count()
        context["total_revenue"] = (
            finance_queryset.filter(
                status=FinanceRecord.Status.PAID,
                paid_at__date__range=[start_date, end_date],
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        context["unpaid_amount"] = (
            finance_queryset.filter(status=FinanceRecord.Status.UNPAID).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        context["operation_summary"] = operation_queryset.filter(data_date__range=[start_date, end_date]).aggregate(
            total_sales=Sum("sales_amount"),
            total_foot_traffic=Sum("foot_traffic"),
            avg_transaction_value=Avg("average_transaction_value"),
        )

        context["maintenance_total"] = maintenance_queryset.count()
        context["maintenance_completed"] = maintenance_queryset.filter(
            status=MaintenanceRequest.Status.COMPLETED
        ).count()
        context["activity_total"] = activity_queryset.count()
        context["activity_approved"] = activity_queryset.filter(status=ActivityApplication.Status.APPROVED).count()

        context["business_type_stats"] = shop_queryset.values("business_type").annotate(count=Count("id"))
        context["maintenance_stats"] = _annotate_percentages(
            maintenance_queryset.values("status").annotate(count=Count("id"))
        )
        context["activity_stats"] = _annotate_percentages(
            activity_queryset.values("status").annotate(count=Count("id"))
        )
        return context


class DashboardView(RoleRequiredMixin, TemplateView):
    """查询功能仪表盘。"""

    template_name = "query/dashboard.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "OPERATION", "FINANCE", "SHOP"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role_type = _get_role_type(self.request.user)
        can_view_shop_query = role_type in {"ADMIN", "MANAGEMENT", "OPERATION", "SHOP"}
        can_view_operation_query = role_type in {"ADMIN", "MANAGEMENT", "OPERATION"}
        can_view_finance_query = role_type in {"ADMIN", "MANAGEMENT", "FINANCE"}
        can_view_admin_query = role_type in {"ADMIN", "MANAGEMENT"}

        context.update(
            {
                "can_view_shop_query": can_view_shop_query,
                "can_view_operation_query": can_view_operation_query,
                "can_view_finance_query": can_view_finance_query,
                "can_view_admin_query": can_view_admin_query,
                "available_query_count": sum(
                    [
                        can_view_shop_query,
                        can_view_operation_query,
                        can_view_finance_query,
                        can_view_admin_query,
                    ]
                ),
            }
        )
        return context
