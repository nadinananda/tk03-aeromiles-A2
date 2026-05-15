from datetime import date
from django.shortcuts import redirect, render
from django.db import DatabaseError, connection, transaction
from django.contrib import messages


def _clean_db_error(error):
    """Ambil bagian error PostgreSQL yang paling relevan untuk ditampilkan."""
    message = str(error).strip()
    for marker in ("CONTEXT:", "DETAIL:", "HINT:"):
        if marker in message:
            message = message.split(marker)[0].strip()
    if "ERROR:" in message:
        message = message.split("ERROR:", 1)[1].strip()
    return message or "Terjadi kesalahan pada database."


def _fetchall_dict(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _pop_db_success_notice():
    notices = getattr(connection.connection, "notices", []) if connection.connection else []
    success_message = None
    for notice in reversed(notices):
        if "SUKSES:" in notice:
            success_message = "SUKSES:" + notice.split("SUKSES:", 1)[1].strip()
            break
    if hasattr(notices, "clear"):
        notices.clear()
    return success_message

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
    provider_filter = request.GET.get('provider', 'semua')
    status_filter = request.GET.get('status', 'semua')

    with connection.cursor() as cursor:
        if request.method == 'POST':
            action = request.POST.get('action')

            try:
                with transaction.atomic():
                    if action == 'create':
                        nama = request.POST.get('nama', '').strip()
                        miles = int(request.POST.get('miles'))
                        deskripsi = request.POST.get('deskripsi', '').strip()
                        valid_start = request.POST.get('valid_start')
                        program_end = request.POST.get('program_end')
                        id_penyedia = int(request.POST.get('id_penyedia'))

                        cursor.execute("LOCK TABLE aeromiles.HADIAH IN SHARE ROW EXCLUSIVE MODE")
                        cursor.execute("""
                            SELECT COALESCE(MAX(CAST(SUBSTRING(kode_hadiah FROM 5) AS INTEGER)), 0) + 1
                            FROM aeromiles.HADIAH
                            WHERE kode_hadiah ~ '^RWD-[0-9]+$'
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
                        nama = request.POST.get('nama', '').strip()
                        miles = int(request.POST.get('miles'))
                        deskripsi = request.POST.get('deskripsi', '').strip()
                        valid_start = request.POST.get('valid_start')
                        program_end = request.POST.get('program_end')
                        id_penyedia = int(request.POST.get('id_penyedia'))

                        cursor.execute("""
                            UPDATE aeromiles.HADIAH
                            SET nama = %s,
                                miles = %s,
                                deskripsi = %s,
                                valid_start_date = %s,
                                program_end = %s,
                                id_penyedia = %s
                            WHERE kode_hadiah = %s
                        """, [nama, miles, deskripsi, valid_start, program_end, id_penyedia, kode_hadiah])

                        if cursor.rowcount == 0:
                            error_msg = "Hadiah tidak ditemukan."
                        else:
                            success_msg = f"Hadiah '{nama}' berhasil diperbarui."

                    elif action == 'delete':
                        kode_hadiah = request.POST.get('kode_hadiah')

                        cursor.execute("""
                            SELECT program_end
                            FROM aeromiles.HADIAH
                            WHERE kode_hadiah = %s
                        """, [kode_hadiah])
                        result = cursor.fetchone()

                        if not result:
                            error_msg = "Hadiah tidak ditemukan."
                        elif result[0] >= date.today():
                            error_msg = "Hadiah hanya dapat dihapus setelah periode berakhir."
                        else:
                            cursor.execute("""
                                DELETE FROM aeromiles.REDEEM
                                WHERE kode_hadiah = %s
                            """, [kode_hadiah])
                            cursor.execute("""
                                DELETE FROM aeromiles.HADIAH
                                WHERE kode_hadiah = %s
                            """, [kode_hadiah])
                            success_msg = "Hadiah berhasil dihapus."

                if success_msg:
                    messages.success(request, success_msg)
                    return redirect('feat_merah:manage_rewards')

            except (DatabaseError, ValueError) as e:
                error_msg = _clean_db_error(e)

        reward_query = """
            WITH maskapai_provider AS (
                SELECT id_penyedia, STRING_AGG(nama_maskapai, ', ' ORDER BY nama_maskapai) AS nama_penyedia
                FROM aeromiles.MASKAPAI
                GROUP BY id_penyedia
            ),
            reward_rows AS (
                SELECT
                    h.kode_hadiah,
                    h.nama,
                    h.miles,
                    h.deskripsi,
                    h.valid_start_date,
                    h.program_end,
                    h.id_penyedia,
                    COALESCE(m.nama_mitra, mp.nama_penyedia, 'Penyedia #' || h.id_penyedia::text) AS penyedia_nama,
                    CASE
                        WHEN CURRENT_DATE < h.valid_start_date THEN 'Akan Datang'
                        WHEN CURRENT_DATE > h.program_end THEN 'Selesai'
                        ELSE 'Aktif'
                    END AS status
                FROM aeromiles.HADIAH h
                LEFT JOIN aeromiles.MITRA m ON h.id_penyedia = m.id_penyedia
                LEFT JOIN maskapai_provider mp ON h.id_penyedia = mp.id_penyedia
            )
            SELECT *
            FROM reward_rows
            WHERE 1 = 1
        """
        params = []

        if provider_filter != 'semua':
            reward_query += " AND id_penyedia = %s"
            params.append(provider_filter)

        if status_filter in ('Aktif', 'Akan Datang', 'Selesai'):
            reward_query += " AND status = %s"
            params.append(status_filter)

        reward_query += " ORDER BY kode_hadiah DESC"
        cursor.execute(reward_query, params)
        hadiah_list = _fetchall_dict(cursor)

        cursor.execute("""
            WITH maskapai_provider AS (
                SELECT id_penyedia, STRING_AGG(nama_maskapai, ', ' ORDER BY nama_maskapai) AS nama_penyedia
                FROM aeromiles.MASKAPAI
                GROUP BY id_penyedia
            )
            SELECT
                p.id,
                COALESCE(m.nama_mitra, mp.nama_penyedia, 'Penyedia #' || p.id::text) AS nama_penyedia,
                CASE
                    WHEN m.email_mitra IS NOT NULL THEN 'Mitra'
                    WHEN mp.nama_penyedia IS NOT NULL THEN 'Maskapai'
                    ELSE 'Penyedia'
                END AS tipe
            FROM aeromiles.PENYEDIA p
            LEFT JOIN aeromiles.MITRA m ON p.id = m.id_penyedia
            LEFT JOIN maskapai_provider mp ON p.id = mp.id_penyedia
            ORDER BY p.id
        """)
        providers = _fetchall_dict(cursor)

    context = {
        'hadiah_list': hadiah_list,
        'providers': providers,
        'today': date.today().isoformat(),
        'error': error_msg,
        'success': success_msg,
        'provider_filter': provider_filter,
        'status_filter': status_filter,
        'active_page': 'kelola_hadiah',
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
                with transaction.atomic():
                    if action == 'create':
                        email_mitra = request.POST.get('email', '').strip().lower()
                        nama_mitra = request.POST.get('nama', '').strip()
                        tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')

                        cursor.execute("LOCK TABLE aeromiles.PENYEDIA IN SHARE ROW EXCLUSIVE MODE")
                        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM aeromiles.PENYEDIA")
                        id_penyedia = cursor.fetchone()[0]

                        cursor.execute("""
                            INSERT INTO aeromiles.PENYEDIA (id)
                            VALUES (%s)
                        """, [id_penyedia])
                        cursor.execute("""
                            SELECT setval(pg_get_serial_sequence('aeromiles.penyedia', 'id'), %s, true)
                        """, [id_penyedia])

                        cursor.execute("""
                            INSERT INTO aeromiles.MITRA
                                (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama)
                            VALUES (%s, %s, %s, %s)
                        """, [email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama])

                        success_msg = f"Mitra '{nama_mitra}' berhasil ditambahkan."

                    elif action == 'update':
                        email_mitra = request.POST.get('email', '').strip()
                        nama_mitra = request.POST.get('nama', '').strip()
                        tanggal_kerja_sama = request.POST.get('tanggal_kerja_sama')

                        cursor.execute("""
                            UPDATE aeromiles.MITRA
                            SET nama_mitra = %s,
                                tanggal_kerja_sama = %s
                            WHERE LOWER(email_mitra) = LOWER(%s)
                        """, [nama_mitra, tanggal_kerja_sama, email_mitra])

                        if cursor.rowcount == 0:
                            error_msg = "Mitra tidak ditemukan."
                        else:
                            success_msg = f"Mitra '{nama_mitra}' berhasil diperbarui."

                    elif action == 'delete':
                        email_mitra = request.POST.get('email', '').strip()

                        cursor.execute("""
                            SELECT id_penyedia
                            FROM aeromiles.MITRA
                            WHERE LOWER(email_mitra) = LOWER(%s)
                        """, [email_mitra])
                        mitra_result = cursor.fetchone()

                        if not mitra_result:
                            error_msg = "Mitra tidak ditemukan."
                        else:
                            id_penyedia = mitra_result[0]
                            cursor.execute("""
                                DELETE FROM aeromiles.REDEEM
                                WHERE kode_hadiah IN (
                                    SELECT kode_hadiah
                                    FROM aeromiles.HADIAH
                                    WHERE id_penyedia = %s
                                )
                            """, [id_penyedia])
                            cursor.execute("""
                                DELETE FROM aeromiles.PENYEDIA
                                WHERE id = %s
                            """, [id_penyedia])

                            success_msg = "Mitra berhasil dihapus."

                if success_msg:
                    messages.success(request, success_msg)
                    return redirect('feat_merah:manage_partners')

            except (DatabaseError, ValueError) as e:
                error_msg = _clean_db_error(e)

        cursor.execute("""
            SELECT
                m.email_mitra, m.id_penyedia, m.nama_mitra, m.tanggal_kerja_sama,
                COUNT(h.kode_hadiah) as hadiah_count
            FROM aeromiles.MITRA m
            LEFT JOIN aeromiles.HADIAH h ON m.id_penyedia = h.id_penyedia
            GROUP BY m.email_mitra, m.id_penyedia, m.nama_mitra, m.tanggal_kerja_sama
            ORDER BY m.tanggal_kerja_sama DESC
        """)
        partners_list = _fetchall_dict(cursor)

    context = {
        'partners': partners_list,
        'error': error_msg,
        'success': success_msg,
        'active_page': 'kelola_mitra',
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
    confirmation_data = None
    
    with connection.cursor() as cursor:
        if request.method == 'POST':
            kode_hadiah = request.POST.get('kode_hadiah')
            action = request.POST.get('action', 'redeem_confirm')

            try:
                if action == 'confirm':
                    # Get hadiah details for confirmation
                    cursor.execute("""
                        SELECT nama, miles FROM aeromiles.HADIAH WHERE kode_hadiah = %s
                    """, [kode_hadiah])
                    hadiah_info = cursor.fetchone()
                    
                    if hadiah_info:
                        confirmation_data = {
                            'kode_hadiah': kode_hadiah,
                            'nama': hadiah_info[0],
                            'miles': hadiah_info[1]
                        }
                
                elif action == 'redeem_confirm':
                    # Perform actual redeem
                    cursor.execute("""
                        INSERT INTO aeromiles.REDEEM (email_member, kode_hadiah, timestamp)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """, [user["email"], kode_hadiah])

                    messages.success(request, "Hadiah berhasil ditukarkan.")
                    return redirect('feat_merah:member_redeem')

            except DatabaseError as e:
                error_msg = _clean_db_error(e)

        cursor.execute("""
            SELECT award_miles, total_miles, id_tier 
            FROM aeromiles.MEMBER 
            WHERE LOWER(email) = LOWER(%s)
        """, [user["email"]])
        member_info = cursor.fetchone()
        member_miles = member_info[0] if member_info else 0
        
        cursor.execute("""
            WITH maskapai_provider AS (
                SELECT id_penyedia, STRING_AGG(nama_maskapai, ', ' ORDER BY nama_maskapai) AS nama_penyedia
                FROM aeromiles.MASKAPAI
                GROUP BY id_penyedia
            )
            SELECT
                h.kode_hadiah, h.nama, h.miles, h.deskripsi,
                h.valid_start_date, h.program_end, h.id_penyedia,
                COALESCE(m.nama_mitra, mp.nama_penyedia, 'Penyedia #' || h.id_penyedia::text) AS penyedia_nama
            FROM aeromiles.HADIAH h
            LEFT JOIN aeromiles.MITRA m ON h.id_penyedia = m.id_penyedia
            LEFT JOIN maskapai_provider mp ON h.id_penyedia = mp.id_penyedia
            WHERE CURRENT_DATE BETWEEN h.valid_start_date AND h.program_end
            ORDER BY h.nama
        """)
        available_hadiah = _fetchall_dict(cursor)

        cursor.execute("""
            SELECT
                r.kode_hadiah, h.nama, h.miles, r.timestamp
            FROM aeromiles.REDEEM r
            JOIN aeromiles.HADIAH h ON r.kode_hadiah = h.kode_hadiah
            WHERE r.email_member = %s
            ORDER BY r.timestamp DESC
        """, [user["email"]])
        redeem_history = _fetchall_dict(cursor)

    context = {
        'user': user,
        'member_miles': member_miles,
        'available_hadiah': available_hadiah,
        'redeem_history': redeem_history,
        'error': error_msg,
        'success': success_msg,
        'confirmation': confirmation_data,
        'active_page': 'redeem',
    }
    return render(request, 'feat_merah/member_redeem.html', context)


# ============================================================================
# CLAIM MISSING MILES APPROVAL - UPDATE FOR STAF
# ============================================================================

def approve_claim_missing_miles_view(request):
    """Approve claim missing miles - triggers member miles update"""
    role_redirect = _require_role(request, 'Staf')
    if role_redirect:
        return role_redirect

    error_msg = None
    success_msg = None

    with connection.cursor() as cursor:
        if request.method == 'POST':
            claim_id = request.POST.get('claim_id')
            status = request.POST.get('status')  # 'Disetujui' or 'Ditolak'
            
            try:
                # Get staf email from session
                staf_email = request.session.get('email')
                
                # Call stored procedure to process claim
                cursor.execute("""
                    CALL aeromiles.sp_proses_claim_missing_miles(%s::integer, %s::varchar, %s::varchar)
                """, [claim_id, staf_email, status])
                db_success_msg = _pop_db_success_notice()
                
                # Get success message
                cursor.execute("""
                    SELECT 
                        email_member, flight_number 
                    FROM aeromiles.CLAIM_MISSING_MILES 
                    WHERE id = %s
                """, [claim_id])
                claim_info = cursor.fetchone()
                if claim_info:
                    member_email, flight_number = claim_info
                    if status == 'Disetujui':
                        success_msg = f'SUKSES: Total miles Member "{member_email}" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "{flight_number}".'
                    else:
                        success_msg = f'SUKSES: Klaim penerbangan untuk member "{member_email}" telah ditolak.'

                success_msg = db_success_msg or success_msg
                if success_msg:
                    messages.success(request, success_msg)
                return redirect('feat_merah:laporan_transaksi')

            except DatabaseError as e:
                error_msg = _clean_db_error(e)

        cursor.execute("""
            SELECT 
                id, email_member, maskapai, bandara_asal, bandara_tujuan, 
                tanggal_penerbangan, flight_number, nomor_tiket, 
                kelas_kabin, pnr, status_penerimaan, timestamp
            FROM aeromiles.CLAIM_MISSING_MILES
            ORDER BY timestamp DESC
        """)
        claims = _fetchall_dict(cursor)

    context = {
        'claims': claims,
        'error': error_msg,
        'success': success_msg,
        'active_page': 'kelola_klaim',
    }
    return render(request, 'feat_merah/approve_claims.html', context)


