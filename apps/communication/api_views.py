from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communication.models import ActivityApplication, MaintenanceRequest, ProcessLog
from apps.communication.serializers import (
    ActivityApplicationCreateSerializer,
    ActivityApplicationSerializer,
    MaintenanceRequestCreateSerializer,
    MaintenanceRequestSerializer,
)
from apps.user_management.models import Role
from apps.user_management.permissions import is_admin_user, is_shop_member


def _get_user_role_type(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "ADMIN"
    role = getattr(getattr(user, "profile", None), "role", None)
    return getattr(role, "role_type", None)


def _get_user_shop_ids(user):
    shops_rel = getattr(user, "shops", None)
    if shops_rel is not None:
        try:
            return list(shops_rel.values_list("id", flat=True))
        except Exception:
            pass
    profile_shop_id = getattr(getattr(user, "profile", None), "shop_id", None)
    return [profile_shop_id] if profile_shop_id else []


def _serialize_request(obj, kind):
    if kind == "maintenance":
        data = MaintenanceRequestSerializer(obj).data
    else:
        data = ActivityApplicationSerializer(obj).data
    data["kind"] = kind
    return data


class RequestListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role_type = _get_user_role_type(request.user)
        if role_type not in [Role.RoleType.SHOP, "ADMIN"]:
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        kind = request.GET.get("kind")
        status_filter = request.GET.get("status")
        shop_id = request.GET.get("shop_id")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if role_type == Role.RoleType.SHOP:
            shop_ids = _get_user_shop_ids(request.user)
            if not shop_ids:
                return Response({"error": "No shop bound"}, status=status.HTTP_403_FORBIDDEN)
            maintenance_qs = MaintenanceRequest.objects.filter(shop_id__in=shop_ids)
            activity_qs = ActivityApplication.objects.filter(shop_id__in=shop_ids)
        else:
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

        results = []
        if kind in (None, "", "maintenance"):
            results.extend([_serialize_request(obj, "maintenance") for obj in maintenance_qs])
        if kind in (None, "", "activity"):
            results.extend([_serialize_request(obj, "activity") for obj in activity_qs])

        results.sort(key=lambda item: item["created_at"], reverse=True)
        return Response(results)

    def post(self, request):
        role_type = _get_user_role_type(request.user)
        if role_type != Role.RoleType.SHOP:
            return Response({"error": "Only shop users can submit requests"}, status=status.HTTP_403_FORBIDDEN)

        shop_ids = _get_user_shop_ids(request.user)
        if not shop_ids:
            return Response({"error": "No shop bound"}, status=status.HTTP_403_FORBIDDEN)

        kind = request.data.get("kind")
        if kind == "maintenance":
            serializer = MaintenanceRequestCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            instance = serializer.save(shop_id=shop_ids[0], created_by=request.user)
            ProcessLog.objects.create(
                content_type="MaintenanceRequest",
                object_id=instance.id,
                action="CREATE",
                description=f"Create maintenance request: {instance.title}",
                operator=request.user.username,
            )
            return Response(_serialize_request(instance, "maintenance"), status=status.HTTP_201_CREATED)
        if kind == "activity":
            serializer = ActivityApplicationCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            instance = serializer.save(shop_id=shop_ids[0], created_by=request.user)
            ProcessLog.objects.create(
                content_type="ActivityApplication",
                object_id=instance.id,
                action="CREATE",
                description=f"Create activity request: {instance.title}",
                operator=request.user.username,
            )
            return Response(_serialize_request(instance, "activity"), status=status.HTTP_201_CREATED)

        return Response({"error": "kind must be maintenance or activity"}, status=status.HTTP_400_BAD_REQUEST)


class RequestDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, kind=None):
        if kind == "activity":
            return get_object_or_404(ActivityApplication, pk=pk), "activity"
        if kind == "maintenance":
            return get_object_or_404(MaintenanceRequest, pk=pk), "maintenance"

        maintenance = MaintenanceRequest.objects.filter(pk=pk).first()
        activity = ActivityApplication.objects.filter(pk=pk).first()

        if maintenance and activity:
            return None, None
        if maintenance:
            return maintenance, "maintenance"
        if activity:
            return activity, "activity"
        return None, None

    def get(self, request, pk):
        kind = request.GET.get("kind")
        obj, resolved_kind = self.get_object(pk, kind)
        if not obj:
            return Response({"error": "Request type required"}, status=status.HTTP_400_BAD_REQUEST)

        role_type = _get_user_role_type(request.user)
        if role_type == Role.RoleType.SHOP:
            if not is_shop_member(request.user, obj.shop):
                return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
        elif not is_admin_user(request.user):
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        return Response(_serialize_request(obj, resolved_kind))

    def patch(self, request, pk):
        if not is_admin_user(request.user):
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        kind = request.data.get("kind") or request.GET.get("kind")
        obj, resolved_kind = self.get_object(pk, kind)
        if not obj:
            return Response({"error": "Request type required"}, status=status.HTTP_400_BAD_REQUEST)

        if resolved_kind == "maintenance":
            for field in [
                "status",
                "assigned_to",
                "handled_by",
                "handled_at",
                "handling_notes",
                "estimated_cost",
                "actual_cost",
                "completion_date",
            ]:
                if field in request.data:
                    setattr(obj, field, request.data.get(field))

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
            for field in ["status", "reviewer", "review_comments", "reviewed_at"]:
                if field in request.data:
                    setattr(obj, field, request.data.get(field))

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

        return Response(_serialize_request(obj, resolved_kind))
