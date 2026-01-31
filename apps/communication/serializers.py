from rest_framework import serializers
from apps.communication.models import MaintenanceRequest, ActivityApplication


class MaintenanceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = ["title", "description", "attachment", "request_type", "priority"]


class ActivityApplicationCreateSerializer(serializers.ModelSerializer):
    start_date = serializers.DateTimeField(input_formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"])
    end_date = serializers.DateTimeField(input_formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"])

    class Meta:
        model = ActivityApplication
        fields = ["title", "description", "attachment", "activity_type", "start_date", "end_date", "location", "participants"]


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    request_type_display = serializers.CharField(source="get_request_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            "id",
            "shop",
            "shop_name",
            "created_by",
            "created_by_name",
            "title",
            "description",
            "attachment",
            "request_type",
            "request_type_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_to",
            "handled_by",
            "handled_at",
            "handling_notes",
            "estimated_cost",
            "actual_cost",
            "completion_date",
            "created_at",
            "updated_at",
        ]


class ActivityApplicationSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    activity_type_display = serializers.CharField(source="get_activity_type_display", read_only=True)

    class Meta:
        model = ActivityApplication
        fields = [
            "id",
            "shop",
            "shop_name",
            "created_by",
            "created_by_name",
            "title",
            "description",
            "attachment",
            "activity_type",
            "activity_type_display",
            "start_date",
            "end_date",
            "location",
            "participants",
            "status",
            "status_display",
            "reviewer",
            "review_comments",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
