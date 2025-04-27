from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views import generic
from .forms import ProfileForm
from django import forms
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password, password_validators_help_text_html

# Create your views here.

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:landing')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('core:landing')
        else:
            messages.error(request, "Incorrect username or password. Please try again.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'registration/profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'registration/edit_profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/change_password.html', {'form': form})



class ResetPasswordForm(forms.Form):
        username = forms.CharField(max_length=150)
        new_password = forms.CharField(
            widget=forms.PasswordInput,
            help_text=password_validators_help_text_html(),  # 💬 Show password rules here
        )
        confirm_password = forms.CharField(widget=forms.PasswordInput)

        def clean(self):
            cleaned_data = super().clean()
            password = cleaned_data.get('new_password')
            confirm = cleaned_data.get('confirm_password')

            if password and confirm:
                if password != confirm:
                    raise forms.ValidationError("Passwords do not match.")

                username = cleaned_data.get('username')
                user = User.objects.filter(username=username).first()
                if user:
                    validate_password(password, user)

                if user.check_password(password):
                    raise forms.ValidationError("New password must be different from the old password.")

            return cleaned_data

        def clean_username(self):
            username = self.cleaned_data['username']
            if not User.objects.filter(username=username).exists():
                raise forms.ValidationError("Username not found.")
            return username


def reset_password(request):
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            new_password = form.cleaned_data['new_password']
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password reset successful. You can now log in.')
        else:
            messages.error(request, "Password does not meet requirements or the passwords do not match. Please try again.")
    else:
        form = ResetPasswordForm()
    return render(request, 'registration/change_password.html', {'form': form})