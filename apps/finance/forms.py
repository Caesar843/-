from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.finance.models import FinanceRecord


class FinanceRecordCreateForm(forms.ModelForm):
    """Finance record create form with basic period validation."""

    class Meta:
        model = FinanceRecord
        fields = ['contract', 'amount', 'fee_type', 'billing_period_start', 'billing_period_end']

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('billing_period_start')
        end_date = cleaned_data.get('billing_period_end')

        if start_date and end_date and end_date <= start_date:
            raise ValidationError(_("账单周期结束日期必须晚于开始日期"))

        return cleaned_data
