from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class ShopUserRegistrationForm(UserCreationForm):
    """
    Registration form for shop owner accounts only.
    """

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}),
    )

    class Meta:
        model = User
        fields = ("username",)
