from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException, StateConflictException
from apps.store.models import (
    Shop,
    Contract,
    ApprovalTask,
    ContractAttachment,
    ContractSignature,
)
from apps.store.forms import (
    ContractForm,
    ContractAttachmentUploadForm,
    ContractSignatureForm,
)
from apps.store.services import ContractService, StoreService
from apps.store.dtos import ContractCreateDTO, ContractActivateDTO
from apps.finance.services import FinanceService
from apps.user_management.permissions import (
    RoleRequiredMixin,
    ShopDataAccessMixin,
    require_object_permission,
    forbidden_response,
    is_shop_member,
)

"""
Store App Views
---------------
[说明]
1. 处理 HTTP 请求
2. ?? DTO ??? Service ??
3. 业务异常处理/提示
"""

def _get_role_type(user):
    return getattr(getattr(getattr(user, "profile", None), "role", None), "role_type", None)


class ShopListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    context_object_name = 'shops'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """根据租户与角色过滤数据"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Store creation is now restricted to superuser-only fallback.
        context["can_create_shop"] = bool(self.request.user.is_superuser)
        return context


class ContractDetailView(LoginRequiredMixin, TemplateView):
    """Contract detail view with object-level permission checks."""
    template_name = "store/contract_detail.html"
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        denied = require_object_permission(
            request,
            "view",
            contract,
            allowed_roles=self.allowed_roles,
            allow_shop_owner=True,
        )
        if denied:
            return denied

        role_type = _get_role_type(request.user)
        can_manage_contract_docs = bool(
            request.user.is_superuser
            or role_type in ["ADMIN", "MANAGEMENT", "OPERATION"]
        )

        attachments = list(
            ContractAttachment.objects.filter(contract=contract).order_by("-created_at", "-id")
        )
        signatures = list(
            ContractSignature.objects.filter(contract=contract).order_by("-signed_at", "-id")
        )

        context = {
            "contract": contract,
            "attachments": attachments,
            "signatures": signatures,
            "can_manage_contract_docs": can_manage_contract_docs,
        }
        if can_manage_contract_docs:
            context["attachment_form"] = ContractAttachmentUploadForm()
            context["signature_form"] = ContractSignatureForm(contract=contract)

        return render(request, self.template_name, context)


class ContractAttachmentUploadView(RoleRequiredMixin, CreateView):
    """合同附件上传入口"""
    model = ContractAttachment
    template_name = "store/contract_detail.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "OPERATION"]

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs["pk"])
        form = ContractAttachmentUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0] if form.errors else "参数错误"
            messages.error(request, f"附件上传失败: {first_error}")
            return redirect("store:contract_detail", pk=contract.pk)

        try:
            attachment = ContractService().add_contract_attachment(
                contract_id=contract.id,
                operator_id=request.user.id,
                attachment_type=form.cleaned_data["attachment_type"],
                uploaded_file=form.cleaned_data["file"],
                remark=form.cleaned_data.get("remark") or "",
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(
                request,
                f"附件上传成功：{attachment.get_attachment_type_display()} v{attachment.version_no}",
            )
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f"附件上传失败: {e.message}")
        except Exception as e:
            messages.error(request, f"附件上传失败: {str(e)}")
        return redirect("store:contract_detail", pk=contract.pk)


class ContractSignatureCreateView(RoleRequiredMixin, CreateView):
    """合同签署登记入口"""
    model = ContractSignature
    template_name = "store/contract_detail.html"
    allowed_roles = ["ADMIN", "MANAGEMENT", "OPERATION"]

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs["pk"])
        form = ContractSignatureForm(request.POST, contract=contract)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0] if form.errors else "参数错误"
            messages.error(request, f"签署登记失败: {first_error}")
            return redirect("store:contract_detail", pk=contract.pk)

        try:
            attachment = form.cleaned_data.get("attachment")
            signature = ContractService().add_contract_signature(
                contract_id=contract.id,
                operator_id=request.user.id,
                party_type=form.cleaned_data["party_type"],
                signer_name=form.cleaned_data["signer_name"],
                signer_title=form.cleaned_data.get("signer_title") or "",
                sign_method=form.cleaned_data["sign_method"],
                signed_at=form.cleaned_data["signed_at"],
                attachment_id=attachment.id if attachment else None,
                evidence_hash=form.cleaned_data.get("evidence_hash") or "",
                comment=form.cleaned_data.get("comment") or "",
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(
                request,
                f"签署登记成功：{signature.get_party_type_display()} {signature.signer_name}",
            )
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f"签署登记失败: {e.message}")
        except Exception as e:
            messages.error(request, f"签署登记失败: {str(e)}")
        return redirect("store:contract_detail", pk=contract.pk)


class ShopCreateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        # Normal operations backend users must use the approval workflow.
        # Keep only superuser fallback access for emergencies.
        if not request.user.is_superuser:
            return forbidden_response(request, '请通过店铺绑定申请与审批流程创建店铺')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """处理表单"""
        try:
            instance = form.save(commit=False)
            if not instance.tenant_id:
                tenant = getattr(self.request.user, "tenant", None) or getattr(getattr(self.request.user, "profile", None), "tenant", None)
                if tenant is None and self.request.user.is_superuser:
                    from apps.tenants.models import Tenant
                    try:
                        tenant = Tenant.objects.get(code="default")
                    except Tenant.DoesNotExist:
                        tenant = None
                if tenant is not None:
                    instance.tenant = tenant
            instance.save()

            if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
                self.request.user.profile.shop = instance
                self.request.user.profile.save()

            messages.success(self.request, '店铺创建成功')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'创建失败: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """处理表单"""
        messages.error(self.request, '表单提交失败，请检查输入')
        return super().form_invalid(form)


class ShopUpdateView(RoleRequiredMixin, ShopDataAccessMixin, UpdateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['ADMIN', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """过滤可编辑数据"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset

    def form_valid(self, form):
        """处理表单"""
        response = super().form_valid(form)
        messages.success(self.request, '店铺创建成功')
        return response

    def form_invalid(self, form):
        """处理表单"""
        return super().form_invalid(form)


class ContractListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    context_object_name = 'contracts'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """过滤合同列表"""
        queryset = Contract.objects.for_tenant(self.request.tenant).filter(is_archived=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(shop=self.request.user.profile.shop)
            else:
                queryset = queryset.none()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role_type = _get_role_type(self.request.user)
        context["can_submit_review"] = bool(
            self.request.user.is_superuser
            or role_type in ["ADMIN", "OPERATION", "SHOP"]
        )
        context["can_review_contract"] = bool(
            self.request.user.is_superuser
            or role_type in ["ADMIN", "MANAGEMENT", "OPERATION"]
        )
        contracts = list(context.get("contracts", []))
        contract_ids = [contract.id for contract in contracts]
        latest_round_tasks_by_contract = {}
        if contract_ids:
            all_tasks = (
                ApprovalTask.objects.filter(contract_id__in=contract_ids)
                .select_related("assigned_to")
                .order_by("contract_id", "-round_no", "order_no", "id")
            )
            for task in all_tasks:
                bucket = latest_round_tasks_by_contract.setdefault(
                    task.contract_id,
                    {"round_no": task.round_no, "tasks": []},
                )
                if task.round_no == bucket["round_no"]:
                    bucket["tasks"].append(task)

        for contract in contracts:
            contract.approval_progress_text = "-"
            contract.approval_current_node = "-"
            contract.approval_pending_actor = ""
            contract.can_current_user_review = False

            info = latest_round_tasks_by_contract.get(contract.id)
            if not info or not info["tasks"]:
                if contract.status == Contract.Status.DRAFT:
                    contract.approval_current_node = "未发起审批"
                elif contract.status == Contract.Status.APPROVED:
                    contract.approval_current_node = "审批完成"
                elif contract.status == Contract.Status.ACTIVE:
                    contract.approval_current_node = "已激活"
                continue

            round_tasks = info["tasks"]
            total_nodes = len(round_tasks)
            approved_nodes = sum(1 for task in round_tasks if task.status == ApprovalTask.Status.APPROVED)
            pending_task = next((task for task in round_tasks if task.status == ApprovalTask.Status.PENDING), None)
            rejected_task = next((task for task in round_tasks if task.status == ApprovalTask.Status.REJECTED), None)

            contract.approval_progress_text = f"{approved_nodes}/{total_nodes}"
            if rejected_task:
                contract.approval_current_node = f"{rejected_task.node_name}（已驳回）"
            elif pending_task:
                contract.approval_current_node = pending_task.node_name
            else:
                contract.approval_current_node = "全部节点已通过"

            if pending_task:
                if pending_task.assigned_to_id:
                    contract.approval_pending_actor = pending_task.assigned_to.get_username()
                elif pending_task.approver_role:
                    contract.approval_pending_actor = pending_task.approver_role
                else:
                    contract.approval_pending_actor = "任意审批人"

                if self.request.user.is_superuser:
                    contract.can_current_user_review = True
                else:
                    assigned_ok = not pending_task.assigned_to_id or pending_task.assigned_to_id == self.request.user.id
                    role_ok = not pending_task.approver_role or pending_task.approver_role == role_type
                    contract.can_current_user_review = bool(assigned_ok and role_ok)

        context["contracts"] = contracts
        return context


class ContractCreateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    form_class = ContractForm
    template_name = 'store/contract_form.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION', 'SHOP']

    def get_form(self, form_class=None):
        """重写 get_form，使用 DTO 表单"""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """重写 get_form_kwargs，移除 instance"""
        kwargs = super().get_form_kwargs()
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs

    def form_valid(self, form):
        """处理表单"""
        try:
            cleaned_data = form.cleaned_data
            dto = ContractCreateDTO(
                shop_id=int(cleaned_data['shop']),
                start_date=cleaned_data['start_date'],
                end_date=cleaned_data['end_date'],
                monthly_rent=Decimal(cleaned_data['monthly_rent']),
                deposit=Decimal(cleaned_data['deposit']),
                payment_cycle=cleaned_data['payment_cycle']
            )
            contract_service = ContractService()
            contract_service.create_draft_contract(
                dto,
                self.request.user.id,
                tenant_id=getattr(self.request.tenant, "id", None),
            )
            messages.success(self.request, '店铺创建成功')
            return redirect(self.success_url)
        except BusinessValidationError as e:
            form.add_error(e.field, e.message)
            messages.error(self.request, f'创建失败: {e.message}')
            return self.form_invalid(form)
        except ResourceNotFoundException as e:
            messages.error(self.request, f'资源不存在: {e.message}')
            return self.form_invalid(form)
        except StateConflictException as e:
            messages.error(self.request, f'创建失败: {e.message}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'创建失败: {str(e)}')
            return self.form_invalid(form)


class ContractSubmitReviewView(RoleRequiredMixin, CreateView):
    """提交审批入口"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION', 'SHOP']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        role_type = _get_role_type(request.user)
        if role_type == 'SHOP' and not is_shop_member(request.user, contract.shop):
            return forbidden_response(request, '无权提交该合同审批')

        try:
            ContractService().submit_for_review(
                contract.id,
                request.user.id,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '合同已提交审批')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'提交审批失败: {e.message}')
        except Exception as e:
            messages.error(request, f'提交审批失败: {str(e)}')
        return redirect('store:contract_list')


class ContractApproveView(RoleRequiredMixin, CreateView):
    """审批通过入口"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        comment = (request.POST.get('comment') or '').strip()
        try:
            updated_contract = ContractService().approve_contract(
                contract.id,
                request.user.id,
                comment=comment,
                tenant_id=getattr(request.tenant, "id", None),
            )
            if updated_contract.status == Contract.Status.APPROVED:
                messages.success(request, '合同审批通过，已完成全部审批节点')
            else:
                next_task = (
                    ApprovalTask.objects.filter(
                        contract_id=updated_contract.id,
                        status=ApprovalTask.Status.PENDING,
                    )
                    .order_by("-round_no", "order_no", "id")
                    .first()
                )
                if next_task:
                    messages.success(request, f'当前节点审批通过，已流转至“{next_task.node_name}”')
                else:
                    messages.success(request, '当前节点审批通过')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'审批失败: {e.message}')
        except Exception as e:
            messages.error(request, f'审批失败: {str(e)}')
        return redirect('store:contract_list')


class ContractRejectView(RoleRequiredMixin, CreateView):
    """审批驳回入口"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        reason = (request.POST.get('reason') or '').strip()
        if not reason:
            messages.error(request, '驳回失败: 请填写驳回原因')
            return redirect('store:contract_list')
        try:
            ContractService().reject_contract(
                contract.id,
                request.user.id,
                reason=reason,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '合同已驳回')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'驳回失败: {e.message}')
        except Exception as e:
            messages.error(request, f'驳回失败: {str(e)}')
        return redirect('store:contract_list')


class ContractActivateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """处理请求"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        try:
            dto = ContractActivateDTO(contract_id=contract.id)
            ContractService().activate_contract(
                dto,
                request.user.id,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '合同已激活')
            try:
                FinanceService.generate_records_for_contract(
                    contract.id,
                    tenant_id=getattr(request.tenant, "id", None),
                    operator_id=request.user.id,
                )
                messages.success(request, '财务记录生成成功')
            except Exception as e:
                messages.warning(request, f'财务记录生成失败: {str(e)}')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'激活失败: {e.message}')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
        return redirect('store:contract_list')


class ContractTerminateView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """处理请求"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        try:
            ContractService().terminate_contract(
                contract.id,
                request.user.id,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '合同已激活')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'激活失败: {e.message}')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
        return redirect('store:contract_list')



from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q

@require_GET
def shop_search(request):
    query = (request.GET.get('q') or '').strip()
    if not query:
        return JsonResponse({'results': []})
    qs = Shop.objects.filter(is_deleted=False).filter(
        Q(name__icontains=query)
        | Q(contact_person__icontains=query)
        | Q(contact_phone__icontains=query)
    ).order_by('name')[:10]

    results = [
        {
            'id': shop.id,
            'name': shop.name,
            'business_type': shop.business_type,
            'contact_person': shop.contact_person or '',
            'contact_phone': shop.contact_phone or '',
            'address': shop.description or '',
        }
        for shop in qs
    ]
    return JsonResponse({'results': results})
class ShopDeleteView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """功能说明"""
        try:
            shop_id = kwargs['pk']
            store_service = StoreService()
            store_service.delete_shop(
                shop_id,
                request.user.id,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '店铺删除成功')
            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'激活失败: {e.message}')
            return redirect('store:shop_list')
        except ResourceNotFoundException as e:
            messages.error(request, f'资源不存在: {e.message}')
            return redirect('store:shop_list')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_list')


class ContractDeleteView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['ADMIN', 'OPERATION']

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """合同删除改为归档，保留全部历史财务记录"""
        contract = get_object_or_404(
            Contract.objects.for_tenant(request.tenant).filter(is_archived=False),
            pk=kwargs['pk']
        )
        try:
            ContractService().archive_contract(
                contract.id,
                request.user.id,
                tenant_id=getattr(request.tenant, "id", None),
            )
            messages.success(request, '合同已归档，历史财务记录已保留')
        except (BusinessValidationError, StateConflictException, ResourceNotFoundException) as e:
            messages.error(request, f'归档失败: {e.message}')
        except Exception as e:
            messages.error(request, f'归档失败: {str(e)}')
        return redirect('store:contract_list')


class ShopExportView(RoleRequiredMixin, CreateView):
    """功能说明"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get(self, request, *args, **kwargs):
        """功能说明"""
        try:
            store_service = StoreService()
            csv_content = store_service.export_shops()

            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="shops.csv"'
            return response
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_list')


class ShopImportView(RoleRequiredMixin, TemplateView):
    """功能说明"""
    template_name = 'store/shop_import.html'
    allowed_roles = ['ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """功能说明"""
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """功能说明"""
        try:
            if 'csv_file' not in request.FILES:
                messages.error(request, '??? CSV ??')
                return redirect('store:shop_import')

            csv_file = request.FILES['csv_file']
            # 文件大小与类型校验（2MB）
            max_size = 2 * 1024 * 1024
            if csv_file.size > max_size:
                messages.error(request, 'CSV 文件过大（最大 2MB）')
                return redirect('store:shop_import')
            filename = (csv_file.name or '').lower()
            if not filename.endswith('.csv'):
                messages.error(request, '仅支持 .csv 文件')
                return redirect('store:shop_import')
            content_type = (csv_file.content_type or '').lower()
            allowed_types = {'text/csv', 'application/vnd.ms-excel', 'text/plain'}
            if content_type and content_type not in allowed_types:
                messages.error(request, 'CSV 文件类型不受支持')
                return redirect('store:shop_import')
            file_content = csv_file.read().decode('utf-8')

            store_service = StoreService()
            result = store_service.import_shops(file_content, request.user.id)

            messages.success(request, f'Import done: {result["success_count"]} ok, {result["error_count"]} failed')

            if result['errors']:
                error_message = 'Import errors:\n' + '\n'.join(result['errors'])
                messages.error(request, error_message)

            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'激活失败: {e.message}')
            return redirect('store:shop_import')
        except Exception as e:
            messages.error(request, f'激活失败: {str(e)}')
            return redirect('store:shop_import')


class ContractExpiryView(RoleRequiredMixin, TemplateView):
    """合同到期提醒"""
    template_name = 'store/contract_expiry.html'
    allowed_roles = ['ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_context_data(self, **kwargs):
        """获取到期数据"""
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        thirty_days_later = today + timezone.timedelta(days=30)

        expiring_contracts = Contract.objects.for_tenant(self.request.tenant).filter(
            status=Contract.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=thirty_days_later
        )

        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                expiring_contracts = expiring_contracts.filter(shop=self.request.user.profile.shop)
            else:
                expiring_contracts = expiring_contracts.none()

        expiring_contracts = expiring_contracts.order_by('end_date')

        expired_contracts = Contract.objects.for_tenant(self.request.tenant).filter(
            status=Contract.Status.ACTIVE,
            end_date__lt=today
        )

        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                expired_contracts = expired_contracts.filter(shop=self.request.user.profile.shop)
            else:
                expired_contracts = expired_contracts.none()

        expired_contracts = expired_contracts.order_by('end_date')

        context['expiring_contracts'] = expiring_contracts
        context['expired_contracts'] = expired_contracts
        context['today'] = today

        return context

