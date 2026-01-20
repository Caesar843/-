from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.communication.models import ActivityApplication, MaintenanceRequest

class ActivityApplicationForm(forms.ModelForm):
    """活动申请表单"""
    class Meta:
        model = ActivityApplication
        fields = ['shop', 'title', 'description', 'activity_type', 'start_date', 'end_date', 'location', 'participants']
        widgets = {
            'start_date': forms.SelectDateWidget(),
            'end_date': forms.SelectDateWidget(),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise ValidationError(_("End date cannot be earlier than start date"))

        return cleaned_data


class MaintenanceRequestForm(forms.ModelForm):
    """维修请求表单"""
    class Meta:
        model = MaintenanceRequest
        fields = ['shop', 'title', 'description', 'request_type', 'priority']