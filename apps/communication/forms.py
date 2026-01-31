from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.communication.models import ActivityApplication, MaintenanceRequest

class ActivityApplicationForm(forms.ModelForm):
    """活动申请表单"""
    class Meta:
        model = ActivityApplication
        fields = ['shop', 'title', 'description', 'attachment', 'activity_type', 'start_date', 'end_date', 'location', 'participants']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control ui-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control ui-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, 'profile'):
            role_type = self.user.profile.role.role_type
            if role_type == 'SHOP':
                shop = self.user.profile.shop
                if shop:
                    self.fields['shop'].queryset = self.fields['shop'].queryset.filter(id=shop.id)
                    self.fields['shop'].initial = shop
                    self.fields['shop'].disabled = True
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
        fields = ['shop', 'title', 'description', 'attachment', 'request_type', 'priority']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, 'profile'):
            role_type = self.user.profile.role.role_type
            if role_type == 'SHOP':
                shop = self.user.profile.shop
                if shop:
                    self.fields['shop'].queryset = self.fields['shop'].queryset.filter(id=shop.id)
                    self.fields['shop'].initial = shop
                    self.fields['shop'].disabled = True


class UnifiedRequestForm(forms.Form):
    KIND_CHOICES = [
        ("maintenance", "维修申请"),
        ("activity", "活动申请"),
    ]

    kind = forms.ChoiceField(choices=KIND_CHOICES)
    title = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    attachment = forms.FileField(required=False)

    request_type = forms.ChoiceField(
        choices=MaintenanceRequest.RequestType.choices,
        required=False
    )
    priority = forms.ChoiceField(
        choices=MaintenanceRequest.Priority.choices,
        required=False
    )

    activity_type = forms.ChoiceField(
        choices=ActivityApplication.ActivityType.choices,
        required=False
    )
    start_date = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    end_date = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    location = forms.CharField(max_length=200, required=False)
    participants = forms.IntegerField(required=False, min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "ui-input")

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get("kind")
        if kind == "activity":
            missing = []
            for field in ["start_date", "end_date", "location", "participants"]:
                if not cleaned_data.get(field):
                    missing.append(field)
            if missing:
                raise ValidationError(_("活动申请请填写开始时间、结束时间、场地与参与人数"))
            start_date = cleaned_data.get("start_date")
            end_date = cleaned_data.get("end_date")
            if start_date and end_date and end_date <= start_date:
                raise ValidationError(_("结束时间必须晚于开始时间"))
        return cleaned_data
