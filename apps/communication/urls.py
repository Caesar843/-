"""
Communication App URLs
----------------------
"""

from django.urls import path
from apps.communication import views

app_name = 'communication'

urlpatterns = [
    # 维修请求相关
    path('maintenance/', views.MaintenanceRequestListView.as_view(), name='maintenance_list'),
    path('maintenance/create/', views.MaintenanceRequestCreateView.as_view(), name='maintenance_create'),
    path('maintenance/<int:pk>/', views.MaintenanceRequestDetailView.as_view(), name='maintenance_detail'),
    path('maintenance/<int:pk>/update/', views.MaintenanceRequestUpdateView.as_view(), name='maintenance_update'),
    
    # 活动申请相关
    path('activities/', views.ActivityApplicationListView.as_view(), name='activity_list'),
    path('activities/create/', views.ActivityApplicationCreateView.as_view(), name='activity_create'),
    path('activities/<int:pk>/', views.ActivityApplicationDetailView.as_view(), name='activity_detail'),
    path('activities/<int:pk>/review/', views.ActivityApplicationReviewView.as_view(), name='activity_review'),
    
    # 运营专员审核相关
    path('admin/maintenance/', views.AdminMaintenanceRequestListView.as_view(), name='admin_maintenance_list'),
    path('admin/activities/', views.AdminActivityApplicationListView.as_view(), name='admin_activity_list'),
]