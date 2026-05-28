import logging

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms


logger = logging.getLogger(__name__)


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used only for account and order records in this demo.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            logger.info("New customer registration user_id=%s username=%s", user.id, user.username)
        return user
