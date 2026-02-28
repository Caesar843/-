# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
import re


class ShopUserRegistrationForm(UserCreationForm):
    """
    Registration form for shop owner accounts only.
    """

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入用户名"}),
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "请输入邮箱"}),
    )
    phone = forms.CharField(
        label="Phone",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入手机号"}),
    )

    verification_channel = forms.ChoiceField(
        label="验证码接收方式",
        choices=(("EMAIL", "邮箱"), ("SMS", "手机")),
        widget=forms.RadioSelect(),
        initial="EMAIL",
    )
    verification_code = forms.CharField(
        label="验证码",
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入验证码"}),
    )
    verification_ticket = forms.CharField(
        label="verification_ticket",
        required=False,
        widget=forms.HiddenInput(),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入密码"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请再次输入密码"}),
    )

    class Meta:
        model = User
        fields = ("username", "email")


class ShopBindingRequestForm(forms.Form):
    IDENTITY_CHOICES = (
        ("OWNER", "我是店主"),
        ("MANAGER", "我是店长"),
        ("OPERATOR", "我是授权运营"),
        ("OTHER", "其他"),
    )
    ROLE_CHOICES = (
        ("OWNER", "店铺负责人"),
        ("FINANCE", "财务"),
        ("OPERATION", "运营"),
        ("READONLY", "只读"),
    )
    CATEGORY_CHOICES = (
        ("FOOD", "餐饮"),
        ("RETAIL", "零售"),
        ("SERVICE", "服务"),
        ("ENT", "娱乐"),
        ("OTHER", "其他"),
    )

    identity_type = forms.ChoiceField(
        label="绑定身份",
        choices=IDENTITY_CHOICES,
        widget=forms.RadioSelect(),
        required=True,
        initial="OWNER",
    )
    requested_shop_name = forms.CharField(
        label="申请店铺名称",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：A区-星火咖啡"}),
    )
    requested_shop_id = forms.CharField(
        label="店铺编号/ID",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "可选，若已知更易审核"}),
    )
    mall_name = forms.CharField(
        label="所在商场/园区/区域",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：星河广场-一期"}),
    )
    industry_category = forms.ChoiceField(
        label="行业类目",
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    address = forms.CharField(
        label="店铺地址",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "省市区 + 详细地址"}),
    )
    contact_name = forms.CharField(
        label="联系人姓名",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：张三"}),
    )
    contact_phone = forms.CharField(
        label="联系电话",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "支持区号或手机号"}),
    )
    contact_email = forms.EmailField(
        label="联系邮箱",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "可选，用于接收通知"}),
    )
    role_requested = forms.ChoiceField(
        label="期望绑定角色",
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    authorization_note = forms.CharField(
        label="授权说明",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "若非店主，请填写授权说明"}),
    )
    note = forms.CharField(
        label="申请说明",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "例如：我是A区星火咖啡店长，店主张三已授权我绑定账号"}),
    )

    def clean_requested_shop_name(self):
        value = (self.cleaned_data.get("requested_shop_name") or "").strip()
        if not value:
            raise forms.ValidationError("请填写真实店铺名称")
        if len(value) < 2 or len(value) > 120:
            raise forms.ValidationError("店铺名称长度不合规范")
        if re.search(r"[<>\\/\\\\]", value):
            raise forms.ValidationError("店铺名称包含非法字符")
        return value

    def clean_contact_phone(self):
        value = (self.cleaned_data.get("contact_phone") or "").strip()
        if not value:
            raise forms.ValidationError("手机号格式不正确")
        normalized = re.sub(r"[\s-]", "", value)
        if normalized.startswith("+"):
            normalized = normalized[1:]
        if not normalized.isdigit() or len(normalized) < 7 or len(normalized) > 15:
            raise forms.ValidationError("手机号格式不正确")
        return value

    def clean_authorization_note(self):
        identity_type = self.cleaned_data.get("identity_type")
        value = (self.cleaned_data.get("authorization_note") or "").strip()
        if identity_type in {"MANAGER", "OPERATOR"} and not value:
            raise forms.ValidationError("非店主身份需填写授权说明")
        return value

    def clean_mall_name(self):
        value = (self.cleaned_data.get("mall_name") or "").strip()
        if not value:
            raise forms.ValidationError("请填写所在商场/园区/区域")
        return value


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "请输入注册邮箱"}
        )


class PasswordResetEmailForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "请输入注册邮箱"}),
    )


class PasswordResetCodeForm(forms.Form):
    code = forms.CharField(
        label="Verification Code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入邮箱验证码"}),
    )


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "请输入新密码"}
        )
        self.fields["new_password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "请再次输入新密码"}
        )
