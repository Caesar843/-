from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, FormView

from apps.communication.forms import ActivityApplicationForm, MaintenanceRequestForm, UnifiedRequestForm
from apps.communication.models import ActivityApplication, MaintenanceRequest, ProcessLog
from apps.store.models import Shop
from apps.user_management.models import Role, ShopBindingRequest
from apps.user_management.permissions import (
    RoleRequiredMixin,
    ShopDataAccessMixin,
    forbidden_response,
    is_shop_member,
    require_object_permission,
)


def _get_user_shops(user):
    shops_rel = getattr(user, "shops", None)
    if shops_rel is not None:
        try:
            return shops_rel.all()
        except Exception:
            pass
    profile_shop = getattr(getattr(user, "profile", None), "shop", None)
    if profile_shop:
        return Shop.objects.filter(id=profile_shop.id)
    return Shop.objects.none()


def _build_request_row(obj, kind):
    if kind == "binding":
        return {
            "id": obj.id,
            "kind": kind,
            "title": obj.requested_shop_name or "搴楅摵缁戝畾鐢宠",
            "type_display": "搴楅摵鐢宠",
            "status_display": obj.get_status_display(),
            "status": obj.status,
            "created_at": obj.created_at,
            "shop_name": getattr(getattr(obj, "approved_shop", None), "name", "-"),
            "applicant": getattr(getattr(obj, "user", None), "username", "-"),
            "detail_url": reverse("core:shop_binding_detail", kwargs={"request_id": obj.id}),
        }

    if kind == "maintenance":
        type_display = obj.get_request_type_display()
    else:
        type_display = obj.get_activity_type_display()
    return {
        "id": obj.id,
        "kind": kind,
        "title": obj.title,
        "type_display": type_display,
        "status_display": obj.get_status_display(),
        "status": obj.status,
        "created_at": obj.created_at,
        "shop_name": obj.shop.name if obj.shop else "-",
        "applicant": getattr(getattr(obj, "created_by", None), "username", "-"),
        "detail_url": reverse("communication:request_detail", kwargs={"kind": kind, "pk": obj.id}),
    }


class RequestListView(RoleRequiredMixin, TemplateView):
    template_name = "communication/request_list.html"
    allowed_roles = ["SHOP"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        shops = _get_user_shops(user)
        kind = self.request.GET.get("kind") or ""
        status_filter = self.request.GET.get("status") or ""

        binding_qs = ShopBindingRequest.objects.filter(user=user)
        maintenance_qs = MaintenanceRequest.objects.filter(created_by=user)
        activity_qs = ActivityApplication.objects.filter(created_by=user)

        if status_filter:
            binding_qs = binding_qs.filter(status=status_filter)
            maintenance_qs = maintenance_qs.filter(status=status_filter)
            activity_qs = activity_qs.filter(status=status_filter)

        rows = []
        if kind in ("", "binding"):
            rows.extend([_build_request_row(obj, "binding") for obj in binding_qs])
        if kind in ("", "maintenance"):
            rows.extend([_build_request_row(obj, "maintenance") for obj in maintenance_qs])
        if kind in ("", "activity"):
            rows.extend([_build_request_row(obj, "activity") for obj in activity_qs])

        rows.sort(key=lambda item: item["created_at"], reverse=True)
        context["requests"] = rows
        context["kind_filter"] = kind
        context["status_filter"] = status_filter
        context["has_bound_shop"] = shops.exists()
        return context


class RequestCreateView(RoleRequiredMixin, FormView):
    template_name = "communication/request_form.html"
    form_class = UnifiedRequestForm
    success_url = "/communication/requests/"
    allowed_roles = ["SHOP"]

    def get_initial(self):
        initial = super().get_initial()
        kind = (self.request.GET.get("kind") or "").strip()
        if kind in {"maintenance", "activity"}:
            initial["kind"] = kind
        return initial

    def dispatch(self, request, *args, **kwargs):
        # Request creation requires a bound shop; guide SHOP users to binding flow first.
        if request.method.lower() == "get" and not _get_user_shops(request.user).exists():
            messages.info(request, "请先完成店铺绑定后再提交维修/活动申请。")
            return redirect("core:shop_binding_request")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.request.user
        shops = _get_user_shops(user)
        if not shops.exists():
            messages.info(self.request, "请先完成店铺绑定后再提交维修/活动申请。")
            return redirect("core:shop_binding_request")
        shop = shops.first()
        if not is_shop_member(user, shop):
            messages.error(self.request, "Access denied.")
            return forbidden_response(self.request, "Access denied")

        data = form.cleaned_data
        kind = data["kind"]
        if kind == "maintenance":
            instance = MaintenanceRequest.objects.create(
                shop=shop,
                created_by=user,
                title=data["title"],
                description=data["description"],
                attachment=data.get("attachment"),
                request_type=data.get("request_type") or MaintenanceRequest.RequestType.OTHER,
                priority=data.get("priority") or MaintenanceRequest.Priority.MEDIUM,
            )
            ProcessLog.objects.create(
                content_type="MaintenanceRequest",
                object_id=instance.id,
                action="CREATE",
                description=f"Create maintenance request: {instance.title}",
                operator=user.username,
            )
        else:
            instance = ActivityApplication.objects.create(
                shop=shop,
                created_by=user,
                title=data["title"],
                description=data["description"],
                attachment=data.get("attachment"),
                activity_type=data.get("activity_type") or ActivityApplication.ActivityType.OTHER,
                start_date=data["start_date"],
                end_date=data["end_date"],
                location=data["location"],
                participants=data["participants"],
            )
            ProcessLog.objects.create(
                content_type="ActivityApplication",
                object_id=instance.id,
                action="CREATE",
                description=f"Create activity request: {instance.title}",
                operator=user.username,
            )

        messages.success(self.request, "Submitted. Waiting for admin review.")
        return redirect(self.success_url)


class RequestDetailView(RoleRequiredMixin, TemplateView):
    template_name = "communication/request_detail.html"
    allowed_roles = ["SHOP"]

    def get(self, request, *args, **kwargs):
        kind = self.kwargs.get("kind")
        pk = self.kwargs.get("pk")
        if kind == "maintenance":
            obj = get_object_or_404(MaintenanceRequest, pk=pk)
        else:
            obj = get_object_or_404(ActivityApplication, pk=pk)

        is_owner = getattr(obj, "created_by_id", None) == request.user.id
        if not (is_owner or is_shop_member(request.user, obj.shop)):
            messages.error(request, "Access denied.")
            return forbidden_response(request, "Access denied")

        self.request_obj = obj
        self.request_kind = kind
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = getattr(self, "request_obj", None)
        kind = getattr(self, "request_kind", None)
        if not obj:
            return context

        logs = ProcessLog.objects.filter(
            content_type="MaintenanceRequest" if kind == "maintenance" else "ActivityApplication",
            object_id=obj.id,
        ).order_by("-created_at")

        context["request_obj"] = obj
        context["kind"] = kind
        context["logs"] = logs
        return context


class AdminRequestListView(RoleRequiredMixin, TemplateView):
    template_name = "communication/admin_request_list.html"
    allowed_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kind = self.request.GET.get("kind") or ""
        status_filter = self.request.GET.get("status") or ""
        shop_id = self.request.GET.get("shop_id") or ""
        start_date = self.request.GET.get("start_date") or ""
        end_date = self.request.GET.get("end_date") or ""

        maintenance_qs = MaintenanceRequest.objects.all()
        activity_qs = ActivityApplication.objects.all()

        if shop_id:
            maintenance_qs = maintenance_qs.filter(shop_id=shop_id)
            activity_qs = activity_qs.filter(shop_id=shop_id)
        if start_date:
            maintenance_qs = maintenance_qs.filter(created_at__date__gte=start_date)
            activity_qs = activity_qs.filter(created_at__date__gte=start_date)
        if end_date:
            maintenance_qs = maintenance_qs.filter(created_at__date__lte=end_date)
            activity_qs = activity_qs.filter(created_at__date__lte=end_date)
        if status_filter:
            maintenance_qs = maintenance_qs.filter(status=status_filter)
            activity_qs = activity_qs.filter(status=status_filter)

        rows = []
        if kind in ("", "maintenance"):
            rows.extend([_build_request_row(obj, "maintenance") for obj in maintenance_qs])
        if kind in ("", "activity"):
            rows.extend([_build_request_row(obj, "activity") for obj in activity_qs])

        rows.sort(key=lambda item: item["created_at"], reverse=True)
        context["requests"] = rows
        context["kind_filter"] = kind
        context["status_filter"] = status_filter
        context["shop_filter"] = shop_id
        context["start_date"] = start_date
        context["end_date"] = end_date
        context["shops"] = Shop.objects.filter(is_deleted=False)
        return context


class AdminRequestDetailView(RoleRequiredMixin, TemplateView):
    template_name = "communication/admin_request_detail.html"
    allowed_roles = ["ADMIN"]

    def get_object(self):
        kind = self.kwargs.get("kind")
        pk = self.kwargs.get("pk")
        if kind == "maintenance":
            return get_object_or_404(MaintenanceRequest, pk=pk)
        return get_object_or_404(ActivityApplication, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        kind = self.kwargs.get("kind")
        logs = ProcessLog.objects.filter(
            content_type="MaintenanceRequest" if kind == "maintenance" else "ActivityApplication",
            object_id=obj.id,
        ).order_by("-created_at")
        context["request_obj"] = obj
        context["kind"] = kind
        context["logs"] = logs
        return context

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        kind = self.kwargs.get("kind")
        status_value = request.POST.get("status")
        notes = request.POST.get("notes", "").strip()
        assigned_to = request.POST.get("assigned_to", "").strip()

        if kind == "maintenance":
            if status_value:
                obj.status = status_value
            if assigned_to:
                obj.assigned_to = assigned_to
            if notes:
                obj.handling_notes = notes
            if obj.status in [
                MaintenanceRequest.Status.IN_PROGRESS,
                MaintenanceRequest.Status.COMPLETED,
                MaintenanceRequest.Status.CANCELLED,
            ]:
                if not obj.handled_by:
                    obj.handled_by = request.user.username
                if not obj.handled_at:
                    obj.handled_at = timezone.now()
            obj.save()
            ProcessLog.objects.create(
                content_type="MaintenanceRequest",
                object_id=obj.id,
                action="UPDATE",
                description=f"Admin update maintenance status: {obj.get_status_display()}",
                operator=request.user.username,
            )
        else:
            if status_value:
                obj.status = status_value
            if notes:
                obj.review_comments = notes
            if obj.status in [ActivityApplication.Status.APPROVED, ActivityApplication.Status.REJECTED]:
                if not obj.reviewer:
                    obj.reviewer = request.user.username
                if not obj.reviewed_at:
                    obj.reviewed_at = timezone.now()
            obj.save()
            ProcessLog.objects.create(
                content_type="ActivityApplication",
                object_id=obj.id,
                action="APPROVE" if obj.status == ActivityApplication.Status.APPROVED else "REJECT",
                description=f"Admin review activity request: {obj.get_status_display()}",
                operator=request.user.username,
            )

        messages.success(request, "申请状态已更新")
        return redirect("/communication/admin/requests/")


class MaintenanceRequestListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    model = MaintenanceRequest
    template_name = "communication/maintenance_list.html"
    context_object_name = "requests"
    allowed_roles = ["ADMIN", "SHOP"]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "profile") and user.profile.role.role_type == "SHOP":
            shops = _get_user_shops(user)
            if not shops.exists():
                return MaintenanceRequest.objects.none()
            return MaintenanceRequest.objects.filter(shop__in=shops)
        return MaintenanceRequest.objects.filter(shop__is_deleted=False)


class MaintenanceRequestCreateView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = "communication/maintenance_form.html"
    success_url = "/communication/maintenance/"
    allowed_roles = ["SHOP"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == "get":
            if not _get_user_shops(request.user).exists():
                messages.info(request, "请先完成店铺绑定后再提交维修申请。")
                return redirect("core:shop_binding_request")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            instance = form.save(commit=False)
            shop = getattr(getattr(self.request.user, "profile", None), "shop", None)
            if not shop:
                messages.info(self.request, "请先完成店铺绑定后再提交维修申请。")
                return redirect("core:shop_binding_request")
            if not is_shop_member(self.request.user, shop):
                messages.error(self.request, "Access denied.")
                return forbidden_response(self.request, "Access denied")
            instance.shop = shop
            instance.created_by = self.request.user
            instance.save()

            ProcessLog.objects.create(
                content_type="MaintenanceRequest",
                object_id=instance.id,
                action="CREATE",
                description=f"Create maintenance request: {instance.title}",
                operator=self.request.user.username,
            )

            messages.success(self.request, "Request submitted.")
            return redirect(self.success_url)
        except Exception as exc:
            messages.error(self.request, f"Submit failed: {exc}")
            return self.form_invalid(form)


class MaintenanceRequestDetailView(RoleRequiredMixin, ShopDataAccessMixin, DetailView):
    model = MaintenanceRequest
    template_name = "communication/maintenance_detail.html"
    context_object_name = "request"
    allowed_roles = ["ADMIN", "SHOP"]

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        denied = require_object_permission(
            request,
            "view",
            obj,
            allowed_roles=[Role.RoleType.ADMIN],
            allow_shop_owner=True,
        )
        if denied:
            return denied
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["logs"] = ProcessLog.objects.filter(
            content_type="MaintenanceRequest",
            object_id=self.object.id,
        ).order_by("-created_at")
        return context


class MaintenanceRequestUpdateView(RoleRequiredMixin, UpdateView):
    model = MaintenanceRequest
    template_name = "communication/maintenance_form.html"
    fields = [
        "title",
        "description",
        "attachment",
        "request_type",
        "priority",
        "status",
        "assigned_to",
        "handled_by",
        "handled_at",
        "handling_notes",
        "estimated_cost",
        "actual_cost",
        "completion_date",
    ]
    success_url = "/communication/maintenance/"
    allowed_roles = ["ADMIN"]

    def form_valid(self, form):
        try:
            original = self.get_object()
            instance = form.save(commit=False)

            if original.status != instance.status:
                ProcessLog.objects.create(
                    content_type="MaintenanceRequest",
                    object_id=instance.id,
                    action="UPDATE",
                    description=f"Status change: {original.get_status_display()} -> {instance.get_status_display()}",
                    operator=self.request.user.username,
                )

            if original.assigned_to != instance.assigned_to and instance.assigned_to:
                ProcessLog.objects.create(
                    content_type="MaintenanceRequest",
                    object_id=instance.id,
                    action="ASSIGN",
                    description=f"Assign handler: {instance.assigned_to}",
                    operator=self.request.user.username,
                )

            if instance.status in [
                MaintenanceRequest.Status.IN_PROGRESS,
                MaintenanceRequest.Status.COMPLETED,
                MaintenanceRequest.Status.CANCELLED,
            ]:
                if not instance.handled_by:
                    instance.handled_by = self.request.user.username
                if not instance.handled_at:
                    instance.handled_at = timezone.now()

            instance.save()

            messages.success(self.request, "Request updated.")
            return redirect(self.success_url)
        except Exception as exc:
            messages.error(self.request, f"Update failed: {exc}")
            return self.form_invalid(form)


class ActivityApplicationListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    model = ActivityApplication
    template_name = "communication/activity_list.html"
    context_object_name = "applications"
    allowed_roles = ["ADMIN", "SHOP"]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "profile") and user.profile.role.role_type == "SHOP":
            shops = _get_user_shops(user)
            if not shops.exists():
                return ActivityApplication.objects.none()
            return ActivityApplication.objects.filter(shop__in=shops)
        return ActivityApplication.objects.filter(shop__is_deleted=False)


class ActivityApplicationCreateView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    model = ActivityApplication
    form_class = ActivityApplicationForm
    template_name = "communication/activity_form.html"
    success_url = "/communication/activities/"
    allowed_roles = ["SHOP"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == "get":
            if not _get_user_shops(request.user).exists():
                messages.info(request, "请先完成店铺绑定后再提交活动申请。")
                return redirect("core:shop_binding_request")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            instance = form.save(commit=False)
            shop = getattr(getattr(self.request.user, "profile", None), "shop", None)
            if not shop:
                messages.info(self.request, "请先完成店铺绑定后再提交活动申请。")
                return redirect("core:shop_binding_request")
            if not is_shop_member(self.request.user, shop):
                messages.error(self.request, "Access denied.")
                return forbidden_response(self.request, "Access denied")
            instance.shop = shop
            instance.created_by = self.request.user
            instance.save()

            ProcessLog.objects.create(
                content_type="ActivityApplication",
                object_id=instance.id,
                action="CREATE",
                description=f"Create activity request: {instance.title}",
                operator=self.request.user.username,
            )

            messages.success(self.request, "Request submitted.")
            return redirect(self.success_url)
        except Exception as exc:
            messages.error(self.request, f"Submit failed: {exc}")
            return self.form_invalid(form)


class ActivityApplicationDetailView(RoleRequiredMixin, ShopDataAccessMixin, DetailView):
    model = ActivityApplication
    template_name = "communication/activity_detail.html"
    context_object_name = "application"
    allowed_roles = ["ADMIN", "SHOP"]

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        denied = require_object_permission(
            request,
            "view",
            obj,
            allowed_roles=[Role.RoleType.ADMIN],
            allow_shop_owner=True,
        )
        if denied:
            return denied
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["logs"] = ProcessLog.objects.filter(
            content_type="ActivityApplication",
            object_id=self.object.id,
        ).order_by("-created_at")
        return context


class ActivityApplicationReviewView(RoleRequiredMixin, UpdateView):
    model = ActivityApplication
    template_name = "communication/activity_review.html"
    fields = ["status", "reviewer", "review_comments", "reviewed_at"]
    success_url = "/communication/activities/"
    allowed_roles = ["ADMIN"]

    def form_valid(self, form):
        try:
            instance = form.save(commit=False)
            if not instance.reviewer:
                instance.reviewer = self.request.user.username
            if not instance.reviewed_at:
                instance.reviewed_at = timezone.now()
            instance.save()

            action = "APPROVE" if instance.status == ActivityApplication.Status.APPROVED else "REJECT"
            ProcessLog.objects.create(
                content_type="ActivityApplication",
                object_id=instance.id,
                action=action,
                description=f"Review result: {instance.get_status_display()}",
                operator=self.request.user.username,
            )

            messages.success(self.request, "Request reviewed.")
            return redirect(self.success_url)
        except Exception as exc:
            messages.error(self.request, f"Review failed: {exc}")
            return self.form_invalid(form)


class AdminMaintenanceRequestListView(RoleRequiredMixin, ListView):
    model = MaintenanceRequest
    template_name = "communication/admin_maintenance_list.html"
    context_object_name = "requests"
    allowed_roles = ["ADMIN"]

    def get_queryset(self):
        queryset = MaintenanceRequest.objects.all().order_by("-created_at")
        status = self.request.GET.get("status")
        req_type = self.request.GET.get("request_type")
        shop_id = self.request.GET.get("shop_id")
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")

        if status:
            queryset = queryset.filter(status=status)
        if req_type:
            queryset = queryset.filter(request_type=req_type)
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["type_filter"] = self.request.GET.get("request_type", "")
        context["shop_filter"] = self.request.GET.get("shop_id", "")
        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")
        context["shops"] = Shop.objects.filter(is_deleted=False)
        return context


class AdminActivityApplicationListView(RoleRequiredMixin, ListView):
    model = ActivityApplication
    template_name = "communication/admin_activity_list.html"
    context_object_name = "applications"
    allowed_roles = ["ADMIN"]

    def get_queryset(self):
        queryset = ActivityApplication.objects.all().order_by("-created_at")
        status = self.request.GET.get("status")
        activity_type = self.request.GET.get("activity_type")
        shop_id = self.request.GET.get("shop_id")
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")

        if status:
            queryset = queryset.filter(status=status)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["type_filter"] = self.request.GET.get("activity_type", "")
        context["shop_filter"] = self.request.GET.get("shop_id", "")
        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")
        context["shops"] = Shop.objects.filter(is_deleted=False)
        return context

