from controltareas.settings import SECRET, API
from django.http import response
from typing import Any
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import login,logout,authenticate
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
import requests, jwt, json

def decodered(data):
    data_token = jwt.decode(data,SECRET, algorithms=["HS256"])
    return data_token

def authenticated(request):
    if request.COOKIES.get('validate'):
        return True
    else:
        return False

def setcookie(tokenAPI):
    obj = redirect('dashboard')
    obj.set_cookie('validate',tokenAPI,expires=43200)
    return obj

def forgotPassword(request):
    return render(request,'login/forgot-password.html')

def lockscreen(request):
    return render(request,'login/lockscreen.html')

def recoverPassword(request):
    return render(request,'login/recover-password.html')

def validate(request):
    email = request.POST.get('email')
    password = request.POST.get('password')
    payload = json.dumps({'email': email, 'password': password})
    headers = {'Accept-Encoding': 'UTF-8', 'Content-Type': 'application/json', 'Accept': '*/*', 'email': email, 'password': password}
    r = requests.post(API+'login/addlogin/', headers=headers, data=payload)
    if r.ok:
        tokenAPI = r.json()
        obj = setcookie(tokenAPI['data']['token'])
        
        return obj
    else:
        return redirect('login')
    
def Login(request):
    return render(request,'login/login.html')
    
def logout(request):
    if authenticated(request):
        token = request.COOKIES.get('validate')
        # headers={'Content-Type':'aplication/json', 'Authorization':'Token '+token}
        # data = requests.get('https://apitasktest.herokuapp.com/logout/', headers=headers)
        rep = redirect('login')
        rep.delete_cookie('validate') # elimina el valor de la cookie de usuario establecido previamente en el navegador del usuario
        return rep
    else:
        return redirect('login')


