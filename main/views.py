from django.shortcuts import render, redirect
from django.db import connection

def login_view(request):
    if 'email' in request.session:
        return redirect('main:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM PENGGUNA WHERE email = %s AND password = %s", [email, password])
            user = cursor.fetchone()

            if user:
                cursor.execute("SELECT email FROM MEMBER WHERE email = %s", [email])
                is_member = cursor.fetchone()
                
                cursor.execute("SELECT email FROM STAF WHERE email = %s", [email])
                is_staf = cursor.fetchone()

                request.session['email'] = email
                if is_member:
                    request.session['role'] = 'Member'
                elif is_staf:
                    request.session['role'] = 'Staf'
                return redirect('main:dashboard')
            else:
                return render(request, 'login.html', {'error': 'Email atau Password salah!'})

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush() 
    return redirect('main:login')

def dashboard_view(request):
    if 'email' not in request.session:
        return redirect('main:login')
    return render(request, 'dashboard.html')