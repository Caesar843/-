from django import forms
from apps.store.models import Shop
from apps.finance.models import FinanceRecord

class ShopQueryForm(forms.Form):
    """店铺查询表单"""
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(is_deleted=False),
        label='店铺',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        label='开始日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label='结束日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


class OperationQueryForm(forms.Form):
    """运营数据查询表单"""
    business_type = forms.ChoiceField(
        choices=[('', '全部业态')] + Shop.BusinessType.choices,
        label='业态类型',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        label='开始日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label='结束日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


class FinanceQueryForm(forms.Form):
    """财务查询表单"""
    fee_type = forms.ChoiceField(
        choices=[('', '全部费用类型')] + FinanceRecord.FeeType.choices,
        label='费用类型',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', '全部状态')] + FinanceRecord.Status.choices,
        label='状态',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        label='开始日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label='结束日期',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


class AdminQueryForm(forms.Form):
    """管理层查询表单"""
    period = forms.ChoiceField(
        choices=[
            ('week', '最近一周'),
            ('month', '最近一个月'),
            ('quarter', '最近三个月'),
            ('year', '最近一年')
        ],
        label='统计周期',
        initial='month',
        widget=forms.Select(attrs={'class': 'form-control'})
    )