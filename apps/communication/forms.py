from django import forms
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

class MaintenanceRequestForm(forms.ModelForm):
    """维修请求表单"""
    class Meta:
        model = MaintenanceRequest
        fields = ['shop', 'title', 'description', 'request_type', 'priority']