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

    with connection.cursor() as cursor:
        # Ambil data dari PENGGUNA
        cursor.execute("""
            SELECT salutation, first_mid_name, last_name, mobile_number, kewarganegaraan, tanggal_lahir 
            FROM PENGGUNA WHERE email = %s
        """, [email_user])
        user_data = cursor.fetchone()
        
        nama = f"{user_data[0]} {user_data[1]} {user_data[2]}" if user_data else 'N/A'
        
        context = {
            'nama': nama,
            'email': email_user,
            'telepon': user_data[3] if user_data else 'N/A',
            'kewarganegaraan': user_data[4] if user_data else 'N/A',
            'tanggal_lahir': user_data[5] if user_data else 'N/A',
            'role': role_user,
        }

        if role_user == 'Member':
            cursor.execute("""
                SELECT m.nomor_member, t.nama, m.total_miles, m.award_miles, m.tanggal_bergabung
                FROM MEMBER m
                JOIN TIER t ON m.id_tier = t.id_tier
                WHERE m.email = %s
            """, [email_user])
            member_data = cursor.fetchone()
            
            if member_data:
                context.update({
                    'nomor_member': member_data[0],
                    'tier': member_data[1],
                    'total_miles': member_data[2],
                    'award_miles': member_data[3],
                    'tanggal_bergabung': member_data[4],
                })

        elif role_user == 'Staf':
            cursor.execute("""
                SELECT nomor_staf
                FROM STAF WHERE email = %s
            """, [email_user])
            staf_data = cursor.fetchone()
            
            if staf_data:
                context.update({
                    'nomor_staf': staf_data[0],
                })

    return render(request, 'dashboard.html', context)

def register_view(request):
    if request.method == 'POST':
        pass
    return render(request, 'register.html')