from datetime import date
from django.shortcuts import redirect, render
from django.db import connection
from django.contrib import messages
from django.http import JsonResponse
import json
from decimal import Decimal

def _current_user(request):
    """Get current user from session"""
    email = request.session.get("email")
    if not email:
        return None

    with connection.cursor() as cursor:
        # Get user info from PENGGUNA and check if Member or Staf
        cursor.execute("""
            SELECT email, first_mid_name || ' ' || last_name as name FROM aeromiles.PENGGUNA 
            WHERE LOWER(email) = LOWER(%s)
        """, [email])
        user = cursor.fetchone()
        
        if not user:
            return None
        
        user_email, name = user
        
        # Check if Member
        cursor.execute("SELECT email FROM aeromiles.MEMBER WHERE LOWER(email) = LOWER(%s)", [email])
        is_member = cursor.fetchone() is not None
        
        # Check if Staf
        cursor.execute("SELECT email FROM aeromiles.STAF WHERE LOWER(email) = LOWER(%s)", [email])
        is_staf = cursor.fetchone() is not None
        
        role = "Member" if is_member else ("Staf" if is_staf else None)
        
        return {
            "email": user_email,
            "name": name,
            "role": role,
        }


def _require_login(request):
    """Check if user is logged in"""
    if 'email' not in request.session:
        return redirect('main:login')
    return None


def _require_role(request, required_role):
    """Check if user has required role"""
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect
    
    user = _current_user(request)
    if not user or user.get('role') != required_role:
        return redirect('main:dashboard')
    return None


def manage_rewards_view(request):
    """CRUD operations for HADIAH (Rewards) - Staf only"""
    role_redirect = _require_role(request, 'Staf')
    if role_redirect:
        return role_redirect

    error_msg = None
    success_msg = None

    with connection.cursor() as cursor:
        if request.method == 'POST':
            action = request.POST.get('action')
            
            try:
                if action == 'create':
                    nama = request.POST.get('nama')
                    miles = int(request.POST.get('miles'))
                    deskripsi = request.POST.get('deskripsi')
                    valid_start = request.POST.get('valid_start')
                    program_end = request.POST.get('program_end')
                    id_penyedia = int(request.POST.get('id_penyedia'))
                    
                  
                    cursor.execute("""
                        SELECT COALESCE(MAX(CAST(SUBSTRING(kode_hadiah, 5) AS INTEGER)), 0) + 1 
                        FROM aeromiles.HADIAH
                    """)
                    next_id = cursor.fetchone()[0]
                    kode_hadiah = f"RWD-{next_id:03d}"
                    
                    cursor.execute("""
                        INSERT INTO aeromiles.HADIAH 
                        (kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [kode_hadiah, nama, miles, deskripsi, valid_start, program_end, id_penyedia])
                    
                    success_msg = f"Hadiah '{nama}' berhasil ditambahkan dengan kode {kode_hadiah}."
                
                elif action == 'update':
                    kode_hadiah = request.POST.get('kode_hadiah')
                    nama = request.POST.get('nama')
                    miles = int(request.POST.get('miles'))
                    deskripsi = request.POST.get('deskripsi')
                    valid_start = request.POST.get('valid_start')
                    program_end = request.POST.get('program_end')
                    
                    cursor.execute("""
                        UPDATE aeromiles.HADIAH 
                        SET nama = %s, miles = %s, deskripsi = %s, 
                            valid_start_date = %s, program_end = %s
                        WHERE kode_hadiah = %s
                    """, [nama, miles, deskripsi, valid_start, program_end, kode_hadiah])
                    
                    success_msg = f"Hadiah '{nama}' berhasil diperbarui."
                
                elif action == 'delete':
                    kode_hadiah = request.POST.get('kode_hadiah')
                    
                   
                    cursor.execute("""
                        SELECT program_end FROM aeromiles.HADIAH WHERE kode_hadiah = %s
                    """, [kode_hadiah])
                    result = cursor.fetchone()
                    
                    if result and result[0] < date.today():
                        cursor.execute("""
                            DELETE FROM aeromiles.HADIAH WHERE kode_hadiah = %s
                        """, [kode_hadiah])
                        success_msg = "Hadiah berhasil dihapus."
                    else:
                        error_msg = "Hadiah hanya dapat dihapus setelah periode berakhir."
                
                if success_msg:
                    return redirect('feat_merah:manage_rewards')
                    
            except Exception as e:
                error_msg = f"Error: {str(e)}"

       
        cursor.execute("""
            SELECT 
                h.kode_hadiah, h.nama, h.miles, h.deskripsi, 
                h.valid_start_date, h.program_end, h.id_penyedia,
                CASE 
                    WHEN CURRENT_DATE < valid_start_date THEN 'Akan Datang'
                    WHEN CURRENT_DATE > program_end THEN 'Selesai'
                    ELSE 'Aktif'
                END as status
            FROM aeromiles.HADIAH h
            ORDER BY h.kode_hadiah DESC
        """)
        columns = [col[0] for col in cursor.description]
        hadiah_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
     
        cursor.execute("SELECT id, id FROM aeromiles.PENYEDIA ORDER BY id")
        providers = [{"id": row[0]} for row in cursor.fetchall()]

    context = {
        'hadiah_list': hadiah_list,
        'providers': providers,
        'today': date.today().isoformat(),
        'error': error_msg,
        'success': success_msg,
    }
    return render(request, 'feat_merah/manage_rewards.html', context)


def manage_partners_view(request):
    """CRUD operations for MITRA (Partners) - Staf only"""
    role_redirect = _require_role(request, 'Staf')
    if role_redirect:
        return role_redirect

    error_msg = None
    success_msg = None

    with connection.cursor() as cursor:
        if request.method == 'POST':
            action = request.POST.get('action')
            
            try:
                if action == 'create':
                    email_mitra = request.POST.get('email')
                    nama_mitra = request.POST.get('nama')
                    tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')
                    
                   
                    cursor.execute("INSERT INTO aeromiles.PENYEDIA DEFAULT VALUES RETURNING id")
                    id_penyedia = cursor.fetchone()[0]
                    
                
                    cursor.execute("""
                        INSERT INTO aeromiles.MITRA 
                        (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama)
                        VALUES (%s, %s, %s, %s)
                    """, [email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama])
                    
                    success_msg = f"Mitra '{nama_mitra}' berhasil ditambahkan."
                
                elif action == 'update':
                    email_mitra = request.POST.get('email')
                    nama_mitra = request.POST.get('nama')
                    tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')
                    
                    cursor.execute("""
                        UPDATE aeromiles.MITRA 
                        SET nama_mitra = %s, tanggal_kerja_sama = %s
                        WHERE email_mitra = %s
                    """, [nama_mitra, tanggal_kerja_sama, email_mitra])
                    
                    success_msg = f"Mitra '{nama_mitra}' berhasil diperbarui."
                
                elif action == 'delete':
                    email_mitra = request.POST.get('email')
                    
                 
                    cursor.execute("""
                        SELECT id_penyedia FROM aeromiles.MITRA WHERE email_mitra = %s
                    """, [email_mitra])
                    result = cursor.fetchone()
                    
                    if result:
                        id_penyedia = result[0]
                        
                        cursor.execute("""
                            DELETE FROM aeromiles.MITRA WHERE email_mitra = %s
                        """, [email_mitra])
                        
                        success_msg = "Mitra berhasil dihapus."
                    else:
                        error_msg = "Mitra tidak ditemukan."
                
                if success_msg:
                    return redirect('feat_merah:manage_partners')
                    
            except Exception as e:
                error_msg = f"Error: {str(e)}"

       
        cursor.execute("""
            SELECT 
                m.email_mitra, m.id_penyedia, m.nama_mitra, m.tanggal_kerja_sama,
                COUNT(h.kode_hadiah) as hadiah_count
            FROM aeromiles.MITRA m
            LEFT JOIN aeromiles.HADIAH h ON m.id_penyedia = h.id_penyedia
            GROUP BY m.email_mitra, m.id_penyedia, m.nama_mitra, m.tanggal_kerja_sama
            ORDER BY m.tanggal_kerja_sama DESC
        """)
        columns = [col[0] for col in cursor.description]
        partners_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

    context = {
        'partners': partners_list,
        'error': error_msg,
        'success': success_msg,
    }
    return render(request, 'feat_merah/manage_partners.html', context)



def member_redeem_view(request):
    """Redeem rewards for members"""
    login_redirect = _require_login(request)
    if login_redirect:
        return login_redirect
    
    user = _current_user(request)
    if user["role"] != "Member":
        return redirect('main:dashboard')

    error_msg = None
    success_msg = None
    
    with connection.cursor() as cursor:
        if request.method == 'POST':
            kode_hadiah = request.POST.get('kode_hadiah')
            
            try:
                cursor.execute("""
                    INSERT INTO aeromiles.REDEEM (email_member, kode_hadiah, timestamp)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """, [user["email"], kode_hadiah])
                
                success_msg = f"Hadiah berhasil ditukarkan!"
                
            except Exception as e:
                error_msg = str(e)
                if "ERROR:" in error_msg:
                    error_msg = error_msg.split("ERROR:")[1].strip()

        cursor.execute("""
            SELECT award_miles, total_miles, id_tier 
            FROM aeromiles.MEMBER 
            WHERE LOWER(email) = LOWER(%s)
        """, [user["email"]])
        member_info = cursor.fetchone()
        member_miles = member_info[0] if member_info else 0
        
        cursor.execute("""
            SELECT 
                h.kode_hadiah, h.nama, h.miles, h.deskripsi, 
                h.valid_start_date, h.program_end, h.id_penyedia,
                p.nama_maskapai as penyedia_nama
            FROM aeromiles.HADIAH h
            LEFT JOIN aeromiles.MASKAPAI p ON h.id_penyedia = (
                SELECT id_penyedia FROM aeromiles.MASKAPAI m WHERE m.kode_maskapai = p.kode_maskapai LIMIT 1
            )
            WHERE CURRENT_DATE BETWEEN h.valid_start_date AND h.program_end
            ORDER BY h.nama
        """)
        columns = [col[0] for col in cursor.description]
        available_hadiah = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT 
                r.kode_hadiah, h.nama, h.miles, r.timestamp
            FROM aeromiles.REDEEM r
            JOIN aeromiles.HADIAH h ON r.kode_hadiah = h.kode_hadiah
            WHERE r.email_member = %s
            ORDER BY r.timestamp DESC
        """, [user["email"]])
        columns = [col[0] for col in cursor.description]
        redeem_history = [dict(zip(columns, row)) for row in cursor.fetchall()]

    context = {
        'user': user,
        'member_miles': member_miles,
        'available_hadiah': available_hadiah,
        'redeem_history': redeem_history,
        'error': error_msg,
        'success': success_msg,
    }
    return render(request, 'feat_merah/member_redeem.html', context)