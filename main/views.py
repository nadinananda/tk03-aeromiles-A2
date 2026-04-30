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
    
    email_user = request.session.get('email')
    role_user = request.session.get('role')

    context = {
        'nama': 'Mr. Juma Jordan Bimo', 
        'email': email_user,
        'telepon': '+62 81234567890',
        'kewarganegaraan': 'Indonesia',
        'tanggal_lahir': '2006-06-25',
        'role': role_user,
    }

    if role_user == 'Member':
        context.update({
            'nomor_member': 'M0001',
            'tier': 'Gold',
            'total_miles': '45,000',
            'award_miles': '32,000',
            'tanggal_bergabung': '2024-01-15',
            'transaksi': [
                {'tipe': 'Transfer', 'waktu': '2025-01-15 10:30', 'jumlah': '-5,000'},
                {'tipe': 'Redeem', 'waktu': '2025-01-20 16:00', 'jumlah': '-3,000'},
                {'tipe': 'Package', 'waktu': '2025-03-01 08:00', 'jumlah': '+10,000'},
            ]
        })
    elif role_user == 'Staf':
        context.update({
            'id_staf': 'S0001',
            'maskapai': 'Garuda Indonesia',
            'klaim_menunggu': 2,
            'klaim_disetujui': 1,
            'klaim_ditolak': 1,
        })

    return render(request, 'dashboard.html', context)

def register_view(request):
    if request.method == 'POST':
        pass
    return render(request, 'register.html')