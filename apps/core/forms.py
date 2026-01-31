from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User


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
    requested_shop_name = forms.CharField(
        label="申请店铺名称",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：A区-星火咖啡"}),
    )
    contact_phone = forms.CharField(
        label="联系电话",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "可选，便于管理员联系"}),
    )
    note = forms.CharField(
        label="备注",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "可选，说明申请背景"}),
    )


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
