from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.contrib import messages
import time
from datetime import date

def login_view(request):
    if 'email' in request.session:
        return redirect('main:dashboard')

    context = {
        'demo_member': 'member1@aeromiles.com / 12345',
        'demo_staf': 'staf1@aeromiles.com / 12345',
    }

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        with connection.cursor() as cursor:
            cursor.execute("SELECT check_kredensial(%s, %s)", [email, password])
            is_valid_login = cursor.fetchone()[0]

            if is_valid_login:
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
                context.update({
                    'error': 'Email atau Password salah, silakan coba lagi.',
                    'email_value': email,
                })

    return render(request, 'main/login.html', context)

def logout_view(request):
    email = request.session.get('email')
    request.session.flush()
    
    context = {
        'email': email,
        'logout_time': date.today().strftime('%d %B %Y')
    }
    return render(request, 'main/logout.html', context)

def dashboard_view(request):
    if 'email' not in request.session:
        return redirect('main:login')
    
    email_user = request.session.get('email')
    role_user = request.session.get('role')

    with connection.cursor() as cursor:
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
                
                try:
                    cursor.execute("""
                        SELECT h.nama, r.timestamp 
                        FROM REDEEM r
                        JOIN HADIAH h ON r.kode_hadiah = h.kode_hadiah
                        WHERE r.email_member = %s
                        ORDER BY r.timestamp DESC LIMIT 5
                    """, [email_user])
                    transaksi = cursor.fetchall()
                    context['transaksi'] = [
                        {'nama': t[0], 'waktu': t[1]}
                        for t in transaksi
                    ]
                except Exception as e:
                    context['transaksi'] = []

        elif role_user == 'Staf':
            cursor.execute("""
                SELECT id_staf
                FROM STAF WHERE email = %s
            """, [email_user])
            staf_data = cursor.fetchone()
            
            if staf_data:
                context.update({
                    'id_staf': staf_data[0],
                })

    return render(request, 'main/dashboard.html', context)

def register_view(request):
    maskapai_list = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT kode_maskapai, nama_maskapai FROM MASKAPAI")
            maskapai_list = cursor.fetchall()
    except Exception as e:
        print(f"Gagal ambil maskapai: {e}")

    context = {'maskapai_list': maskapai_list}

    if request.method == 'POST':
        role = request.POST.get('role')
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        salutation = request.POST.get('salutation')
        nama_depan = request.POST.get('nama_depan')
        nama_belakang = request.POST.get('nama_belakang')
        kewarganegaraan = request.POST.get('kewarganegaraan')
        country_code = request.POST.get('country_code')
        nomor_hp = request.POST.get('nomor_hp')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        
        kode_maskapai_pilihan = request.POST.get('kode_maskapai')

        if password != confirm_password:
            context['error'] = "U-umm... Password-nya nggak sama, baka! Coba cek lagi!"
            return render(request, 'main/register.html', context)

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO PENGGUNA (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
                    VALUES (%s, extensions.crypt(%s, extensions.gen_salt('bf')), %s, %s, %s, %s, %s, %s, %s)
                """, [email, password, salutation, nama_depan, nama_belakang, country_code, nomor_hp, tanggal_lahir, kewarganegaraan])

                if role == 'Member':
                    cursor.execute("SELECT nomor_member FROM MEMBER")
                    semua_member = cursor.fetchall()
                    max_num = 0
                    for m in semua_member:
                        angka_saja = ''.join(filter(str.isdigit, m[0]))
                        if angka_saja:
                            max_num = max(max_num, int(angka_saja))
                    
                    nomor_member = f"M{max_num + 1:04d}"
                    
                    cursor.execute("""
                        INSERT INTO MEMBER (email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles)
                        VALUES (%s, %s, CURRENT_DATE, 'T-BLUE', 0, 0)
                    """, [email, nomor_member])
                
                elif role == 'Staf':
                    if not kode_maskapai_pilihan:
                        raise ValueError("Maskapai harus dipilih untuk peran Staf!")

                    cursor.execute("SELECT id_staf FROM STAF")
                    semua_staf = cursor.fetchall()
                    max_num = 0
                    for s in semua_staf:
                        angka_saja = ''.join(filter(str.isdigit, s[0]))
                        if angka_saja:
                            max_num = max(max_num, int(angka_saja))
                            
                    id_staf = f"S{max_num + 1:04d}"
                    
                    cursor.execute("""
                        INSERT INTO STAF (email, id_staf, kode_maskapai)
                        VALUES (%s, %s, %s)
                    """, [email, id_staf, kode_maskapai_pilihan])

            messages.success(request, "Registrasi berhasil! Sekarang kamu bisa login... kalau mau.")
            return redirect('main:login')

        except Exception as e:
            error_asli = str(e).split('CONTEXT:')[0].strip()
            context['error'] = error_asli
            return render(request, 'main/register.html', context)

    return render(request, 'main/register.html', context)