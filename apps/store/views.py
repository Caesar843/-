from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from apps.core.exceptions import BusinessValidationError, ResourceNotFoundException, StateConflictException
from apps.store.models import Shop, Contract
from apps.store.forms import ContractForm
from apps.store.services import ContractService, StoreService
from apps.store.dtos import ContractCreateDTO
from apps.finance.services import FinanceService
from apps.user_management.permissions import (
    RoleRequiredMixin,
    ShopDataAccessMixin,
    require_object_permission,
)

"""
Store App Views
---------------
[????]
1. ?? HTTP ??????
2. ?? DTO ??? Service ??
3. ?????????/????
"""


class ShopListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """??????"""
    model = Shop
    template_name = 'store/shop_list.html'
    context_object_name = 'shops'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """???????????????????????"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset


class ContractDetailView(LoginRequiredMixin, TemplateView):
    """Contract detail view with object-level permission checks."""
    template_name = "store/contract_detail.html"
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

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
        return render(request, self.template_name, {"contract": contract})


class ShopCreateView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']

    def form_valid(self, form):
        """???????????"""
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

            messages.success(self.request, '??????')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'??????: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """???????????"""
        messages.error(self.request, '??????????????')
        return super().form_invalid(form)


class ShopUpdateView(RoleRequiredMixin, ShopDataAccessMixin, UpdateView):
    """??????"""
    model = Shop
    template_name = 'store/shop_form.html'
    fields = ['name', 'business_type', 'area', 'rent', 'contact_person', 'contact_phone', 'entry_date', 'org_unit', 'description']
    success_url = reverse_lazy('store:shop_list')
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """?????????????"""
        queryset = Shop.objects.for_tenant(self.request.tenant).filter(is_deleted=False)
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(id=self.request.user.profile.shop.id)
            else:
                queryset = queryset.none()
        return queryset

    def form_valid(self, form):
        """???????????"""
        response = super().form_valid(form)
        messages.success(self.request, '????????')
        return response

    def form_invalid(self, form):
        """???????????"""
        return super().form_invalid(form)


class ContractListView(RoleRequiredMixin, ShopDataAccessMixin, ListView):
    """??????"""
    model = Contract
    template_name = 'store/contract_list.html'
    context_object_name = 'contracts'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_queryset(self):
        """???????????????"""
        queryset = Contract.objects.for_tenant(self.request.tenant).all()
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role.role_type == 'SHOP':
            if self.request.user.profile.shop:
                queryset = queryset.filter(shop=self.request.user.profile.shop)
            else:
                queryset = queryset.none()
        return queryset


class ContractCreateView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Contract
    form_class = ContractForm
    template_name = 'store/contract_form.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION', 'SHOP']

    def get_form(self, form_class=None):
        """?? get_form ???????? instance ??? DTOForm"""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """?? get_form_kwargs ????? instance ??"""
        kwargs = super().get_form_kwargs()
        if 'instance' in kwargs:
            del kwargs['instance']
        return kwargs

    def form_valid(self, form):
        """???????????"""
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
            contract_service.create_draft_contract(dto, self.request.user.id)
            messages.success(self.request, '??????')
            return redirect(self.success_url)
        except BusinessValidationError as e:
            form.add_error(e.field, e.message)
            messages.error(self.request, f'????: {e.message}')
            return self.form_invalid(form)
        except ResourceNotFoundException as e:
            messages.error(self.request, f'?????: {e.message}')
            return self.form_invalid(form)
        except StateConflictException as e:
            messages.error(self.request, f'????: {e.message}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'??????: {str(e)}')
            return self.form_invalid(form)


class ContractActivateView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """??????"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        if contract.status == Contract.Status.DRAFT:
            contract.status = Contract.Status.ACTIVE
            contract.save()
            messages.success(request, '??????')

            try:
                FinanceService.generate_records_for_contract(contract.id)
                messages.success(request, '?????????')
            except Exception as e:
                messages.warning(request, f'????????: {str(e)}')
        else:
            messages.error(request, '??????????????')
        return redirect('store:contract_list')


class ContractTerminateView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """??????"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        if contract.status == Contract.Status.ACTIVE:
            contract.status = Contract.Status.TERMINATED
            contract.save()
            messages.success(request, '??????')
        else:
            messages.error(request, '??????????????')
        return redirect('store:contract_list')


class ShopDeleteView(RoleRequiredMixin, ShopDataAccessMixin, CreateView):
    """??????"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """??????"""
        try:
            shop_id = kwargs['pk']
            store_service = StoreService()
            store_service.delete_shop(shop_id, request.user.id)
            messages.success(request, '??????')
            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'????: {e.message}')
            return redirect('store:shop_list')
        except ResourceNotFoundException as e:
            messages.error(request, f'?????: {e.message}')
            return redirect('store:shop_list')
        except Exception as e:
            messages.error(request, f'??????: {str(e)}')
            return redirect('store:shop_list')


class ContractDeleteView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Contract
    template_name = 'store/contract_list.html'
    success_url = '/store/contracts/'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """??????"""
        contract = get_object_or_404(Contract.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        if contract.status in [Contract.Status.TERMINATED, Contract.Status.EXPIRED]:
            from apps.finance.models import FinanceRecord
            FinanceRecord.objects.filter(contract=contract).delete()
            contract.delete()
            messages.success(request, '??????')
        else:
            messages.error(request, '??????????????')
        return redirect('store:contract_list')


class ShopExportView(RoleRequiredMixin, CreateView):
    """??????"""
    model = Shop
    template_name = 'store/shop_list.html'
    success_url = '/store/shops/'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get(self, request, *args, **kwargs):
        """??????"""
        try:
            store_service = StoreService()
            csv_content = store_service.export_shops()

            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="shops.csv"'
            return response
        except Exception as e:
            messages.error(request, f'????: {str(e)}')
            return redirect('store:shop_list')


class ShopImportView(RoleRequiredMixin, TemplateView):
    """??????"""
    template_name = 'store/shop_import.html'
    allowed_roles = ['SUPER_ADMIN', 'OPERATION']

    def get(self, request, *args, **kwargs):
        """??????"""
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """??????"""
        try:
            if 'csv_file' not in request.FILES:
                messages.error(request, '???????CSV??')
                return redirect('store:shop_import')

            csv_file = request.FILES['csv_file']
            file_content = csv_file.read().decode('utf-8')

            store_service = StoreService()
            result = store_service.import_shops(file_content, request.user.id)

            messages.success(request, f'Import done: {result["success_count"]} ok, {result["error_count"]} failed')

            if result['errors']:
                error_message = 'Import errors:\n' + '\n'.join(result['errors'])
                messages.error(request, error_message)

            return redirect('store:shop_list')
        except BusinessValidationError as e:
            messages.error(request, f'????: {e.message}')
            return redirect('store:shop_import')
        except Exception as e:
            messages.error(request, f'????: {str(e)}')
            return redirect('store:shop_import')


class ContractExpiryView(RoleRequiredMixin, TemplateView):
    """????????"""
    template_name = 'store/contract_expiry.html'
    allowed_roles = ['SUPER_ADMIN', 'MANAGEMENT', 'OPERATION', 'SHOP']

    def get_context_data(self, **kwargs):
        """???????"""
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