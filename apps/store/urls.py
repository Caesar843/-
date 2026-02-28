from django.urls import path
from apps.store.views import (
    shop_search,
    ShopListView,
    ShopCreateView,
    ShopUpdateView,
    ShopExportView,
    ShopImportView,
    ContractListView,
    ContractCreateView,
    ContractDetailView,
    ContractAttachmentUploadView,
    ContractSignatureCreateView,
    ContractSubmitReviewView,
    ContractApproveView,
    ContractRejectView,
    ContractActivateView,
    ContractTerminateView,
    ShopDeleteView,
    ContractDeleteView,
    ContractExpiryView,
)

"""
Store App URL Configuration
---------------------------
[架构职责]
1. 店铺与合同管理应用的路由分发。
2. 映射视图函数与 URL 路径。
3. 提供命名空间，避免 URL 冲突。
"""

app_name = 'store'

urlpatterns = [
    path('shops/search/', shop_search, name='shop_search'),
    # 店铺管理
    path('shops/', ShopListView.as_view(), name='shop_list'),
    path('shops/create/', ShopCreateView.as_view(), name='shop_create'),
    path('shops/<int:pk>/update/', ShopUpdateView.as_view(), name='shop_update'),
    path('shops/export/', ShopExportView.as_view(), name='shop_export'),
    path('shops/import/', ShopImportView.as_view(), name='shop_import'),
    
    # 合同管理
    path('contracts/', ContractListView.as_view(), name='contract_list'),
    path('contracts/create/', ContractCreateView.as_view(), name='contract_create'),
    path('contracts/<int:pk>/', ContractDetailView.as_view(), name='contract_detail'),
    path('contracts/<int:pk>/attachments/upload/', ContractAttachmentUploadView.as_view(), name='contract_attachment_upload'),
    path('contracts/<int:pk>/signatures/create/', ContractSignatureCreateView.as_view(), name='contract_signature_create'),
    path('contracts/<int:pk>/submit-review/', ContractSubmitReviewView.as_view(), name='contract_submit_review'),
    path('contracts/<int:pk>/approve/', ContractApproveView.as_view(), name='contract_approve'),
    path('contracts/<int:pk>/reject/', ContractRejectView.as_view(), name='contract_reject'),
    path('contracts/<int:pk>/activate/', ContractActivateView.as_view(), name='contract_activate'),
    path('contracts/<int:pk>/terminate/', ContractTerminateView.as_view(), name='contract_terminate'),
    path('contracts/<int:pk>/delete/', ContractDeleteView.as_view(), name='contract_delete'),
    path('contracts/expiry/', ContractExpiryView.as_view(), name='contract_expiry'),
    
    # 店铺删除
    path('shops/<int:pk>/delete/', ShopDeleteView.as_view(), name='shop_delete'),
]
