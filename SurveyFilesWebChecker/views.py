from django.contrib.auth.decorators import login_required

from django.http import HttpResponseRedirect

from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render, redirect
from django.shortcuts import redirect, render, reverse
from django.contrib.auth import logout
from tools import *

def home(request):

    # return HttpResponseRedirect(reverse('jxlfiles:jxl_list_view'))

    current_users = get_current_users()
    #
    return render(request, 'home.html', {'current_users': current_users})


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super(UserCreateForm, self).__init__(*args, **kwargs)

        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()

        return user

# def signup(request):
#     if request.method == 'POST':
#         form = UserCreateForm(request.POST)
#         if form.is_valid():
#             form.save()
#             username = form.cleaned_data.get('username')
#             raw_password = form.cleaned_data.get('password1')
#             user = authenticate(username=username, password=raw_password)
#             login(request, user)
#             return redirect('home')
#     else:
#         form = UserCreateForm()
#     return render(request, 'registration/signup.html', {'form': form})