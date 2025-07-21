from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect

def dual_login(request):
    print("dual_login view received a request.") # Debug print at the very beginning
    error = None
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.groups.filter(name='Head Engineer').exists():
                login(request, user)
                return redirect('/dashboard/')
            elif user.groups.filter(name='Project Engineer').exists():
                login(request, user)
                return redirect('/projeng/dashboard/')
            else:
                error = 'You do not have permission to access the system.'
        else:
            error = 'Invalid username or password.'
    return render(request, 'registration/dual_login.html', {'error': error})

def custom_logout(request):
    logout(request)
    return redirect('/accounts/login/')