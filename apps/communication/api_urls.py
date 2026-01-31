from django.urls import path
from apps.communication.api_views import RequestListCreateAPIView, RequestDetailAPIView

urlpatterns = [
    path("", RequestListCreateAPIView.as_view(), name="request-list"),
    path("<int:pk>/", RequestDetailAPIView.as_view(), name="request-detail"),
]
