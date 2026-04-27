from django.shortcuts import render, redirect
from django.db import connection

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        with connection.cursor() as cursor:
            # 1. Cek kredensial di tabel PENGGUNA
            cursor.execute("SELECT email FROM PENGGUNA WHERE email = %s AND password = %s", [email, password])
            user = cursor.fetchone()

            if user:
                # 2. Cek Role (apakah Member atau Staf)
                cursor.execute("SELECT email FROM MEMBER WHERE email = %s", [email])
                is_member = cursor.fetchone()
                
                cursor.execute("SELECT email FROM STAF WHERE email = %s", [email])
                is_staf = cursor.fetchone()

                # 3. Simpan ke Session
                request.session['email'] = email
                if is_member:
                    request.session['role'] = 'Member'
                elif is_staf:
                    request.session['role'] = 'Staf'
                
                return redirect('feat_merah:dashboard')
            else:
                return render(request, 'login.html', {'error': 'Email atau Password salah!'})

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush() # Menghapus semua data session
    return redirect('feat_merah:login')

def dashboard_view(request):
    # Placeholder view untuk halaman Dashboard
    return render(request, 'dashboard.html')