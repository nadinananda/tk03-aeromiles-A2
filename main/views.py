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
        messages.error(request, "U-umm... Kamu harus login dulu, baka!")
        return redirect('main:login')

    email_user = request.session['email']
    role_user = request.session['role']

    context = {
        'role': role_user,
        'email': email_user,
        'active_page': 'dashboard' 
    }

    with connection.cursor() as cursor:
        if role_user == 'Member':
            # 1. Ambil data member tanpa JOIN ke tabel TIER dulu
            cursor.execute("""
                SELECT p.first_mid_name, p.last_name, p.mobile_number, p.kewarganegaraan, p.tanggal_lahir,
                       m.tanggal_bergabung, m.nomor_member, m.total_miles, m.award_miles
                FROM PENGGUNA p
                JOIN MEMBER m ON p.email = m.email
                WHERE p.email = %s
            """, [email_user])
            row = cursor.fetchone()
            
            if row:
                total_miles_val = row[7]
                
                # 2. Hitung TIER secara dinamis berdasarkan total_miles
                cursor.execute("""
                    SELECT nama 
                    FROM TIER
                    WHERE minimal_tier_miles <= %s
                    ORDER BY minimal_tier_miles DESC
                    LIMIT 1
                """, [total_miles_val])
                tier_data = cursor.fetchone()
                tier_sekarang = tier_data[0] if tier_data else 'Blue'

                context['nama'] = f"{row[0]} {row[1]}"
                context['telepon'] = row[2]
                context['kewarganegaraan'] = row[3]
                context['tanggal_lahir'] = str(row[4])
                context['tanggal_bergabung'] = str(row[5])
                context['nomor_member'] = row[6]
                context['tier'] = tier_sekarang # Nah, ini sekarang ngirim tier yang akurat!
                context['total_miles'] = f"{total_miles_val:,}"
                context['award_miles'] = f"{row[8]:,}"

            transaksi_list = []
            
            cursor.execute("SELECT timestamp, jumlah FROM TRANSFER WHERE email_member_1 = %s", [email_user])
            for t in cursor.fetchall():
                transaksi_list.append({'tipe': 'Transfer Keluar', 'waktu': t[0], 'jumlah': f"-{t[1]}"})
            
            cursor.execute("SELECT timestamp, jumlah FROM TRANSFER WHERE email_member_2 = %s", [email_user])
            for t in cursor.fetchall():
                transaksi_list.append({'tipe': 'Transfer Masuk', 'waktu': t[0], 'jumlah': f"+{t[1]}"})
                
            cursor.execute("""
                SELECT m.timestamp, a.jumlah_award_miles 
                FROM MEMBER_AWARD_MILES_PACKAGE m 
                JOIN AWARD_MILES_PACKAGE a ON m.id_award_miles_package = a.id 
                WHERE m.email_member = %s
            """, [email_user])
            for t in cursor.fetchall():
                transaksi_list.append({'tipe': 'Beli Paket Miles', 'waktu': t[0], 'jumlah': f"+{t[1]}"})

            cursor.execute("""
                SELECT r.timestamp, h.miles, h.nama 
                FROM REDEEM r 
                JOIN HADIAH h ON r.kode_hadiah = h.kode_hadiah 
                WHERE r.email_member = %s
            """, [email_user])
            for t in cursor.fetchall():
                transaksi_list.append({'tipe': f'Redeem {t[2]}', 'waktu': t[0], 'jumlah': f"-{t[1]}"})

            transaksi_list.sort(key=lambda x: x['waktu'], reverse=True)
            
            for trx in transaksi_list:
                trx['waktu'] = trx['waktu'].strftime("%Y-%m-%d %H:%M")
                
            context['transaksi'] = transaksi_list[:5]

        elif role_user == 'Staf':
            cursor.execute("""
                SELECT p.first_mid_name, p.last_name, p.mobile_number, p.kewarganegaraan, p.tanggal_lahir,
                       s.id_staf, mk.nama_maskapai, mk.kode_maskapai
                FROM PENGGUNA p
                JOIN STAF s ON p.email = s.email
                JOIN MASKAPAI mk ON s.kode_maskapai = mk.kode_maskapai
                WHERE p.email = %s
            """, [email_user])
            row = cursor.fetchone()
            
            if row:
                context['nama'] = f"{row[0]} {row[1]}"
                context['telepon'] = row[2]
                context['kewarganegaraan'] = row[3]
                context['tanggal_lahir'] = str(row[4])
                context['id_staf'] = row[5]
                context['maskapai'] = row[6]
                kode_maskapai = row[7]

                cursor.execute("""
                    SELECT status_penerimaan, COUNT(*) 
                    FROM CLAIM_MISSING_MILES 
                    WHERE maskapai = %s 
                    GROUP BY status_penerimaan
                """, [kode_maskapai])
                
                klaim_counts = {'Menunggu': 0, 'Disetujui': 0, 'Ditolak': 0}
                for status, count in cursor.fetchall():
                    klaim_counts[status] = count
                
                context['klaim_menunggu'] = klaim_counts['Menunggu']
                context['klaim_disetujui'] = klaim_counts['Disetujui']
                context['klaim_ditolak'] = klaim_counts['Ditolak']

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