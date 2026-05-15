from functools import wraps

from django.contrib import messages
from django.db import DatabaseError, connection, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


STATUS_KLAIM = {
    'semua': None,
    'menunggu': 'Menunggu',
    'disetujui': 'Disetujui',
    'ditolak': 'Ditolak',
}

KELAS_KABIN = {'Economy', 'Premium Economy', 'Business', 'First'}


def _clean_db_error(error):
    """Ambil pesan ERROR dari PostgreSQL/trigger/procedure agar bisa ditampilkan di web."""
    message = str(error).strip()

    for marker in ('CONTEXT:', 'DETAIL:', 'HINT:'):
        if marker in message:
            message = message.split(marker)[0].strip()

    lines = [line.strip() for line in message.splitlines() if line.strip()]
    message = lines[0] if lines else 'Terjadi kesalahan pada database.'
    message = message.replace('ERROR:  ERROR:', 'ERROR:')
    message = message.replace('ERROR: ERROR:', 'ERROR:')

    return message


def _fetchone_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


def _fetchall_dict(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def member_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        if request.session.get('role') != 'Member':
            return redirect('main:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def staf_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        if request.session.get('role') != 'Staf':
            return redirect('main:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_pengguna(email):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT email, salutation, first_mid_name, last_name, country_code,
                   mobile_number, tanggal_lahir, kewarganegaraan
            FROM pengguna
            WHERE LOWER(email) = LOWER(%s)
        """, [email])
        return _fetchone_dict(cursor)


def get_member(email):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.email, m.nomor_member, m.tanggal_bergabung, m.id_tier,
                   m.award_miles, m.total_miles, t.nama AS nama_tier
            FROM member m
            LEFT JOIN tier t ON m.id_tier = t.id_tier
            WHERE LOWER(m.email) = LOWER(%s)
        """, [email])
        return _fetchone_dict(cursor)


def get_staf(email):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.email, s.id_staf, s.kode_maskapai, mk.nama_maskapai
            FROM staf s
            LEFT JOIN maskapai mk ON s.kode_maskapai = mk.kode_maskapai
            WHERE LOWER(s.email) = LOWER(%s)
        """, [email])
        return _fetchone_dict(cursor)


def _get_maskapai_list():
    with connection.cursor() as cursor:
        cursor.execute("SELECT kode_maskapai, nama_maskapai FROM maskapai ORDER BY nama_maskapai")
        return [{'kode': row[0], 'nama': row[1]} for row in cursor.fetchall()]


def _get_bandara_list():
    with connection.cursor() as cursor:
        cursor.execute("SELECT iata_code, nama, kota FROM bandara ORDER BY iata_code")
        return [{'iata': row[0], 'nama': row[1], 'kota': row[2]} for row in cursor.fetchall()]


@login_required_custom
def pengaturan_profil(request):
    email = request.session['email']
    role = request.session.get('role')
    pengguna = get_pengguna(email)
    extra = get_member(email) if role == 'Member' else get_staf(email)
    maskapai_list = _get_maskapai_list()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profil':
            salutation = request.POST.get('salutation')
            first_mid_name = request.POST.get('first_mid_name')
            last_name = request.POST.get('last_name')
            country_code = request.POST.get('country_code')
            mobile_number = request.POST.get('mobile_number')
            kewarganegaraan = request.POST.get('kewarganegaraan')
            tanggal_lahir = request.POST.get('tanggal_lahir')

            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE pengguna
                            SET salutation = %s,
                                first_mid_name = %s,
                                last_name = %s,
                                country_code = %s,
                                mobile_number = %s,
                                kewarganegaraan = %s,
                                tanggal_lahir = %s
                            WHERE LOWER(email) = LOWER(%s)
                        """, [
                            salutation, first_mid_name, last_name,
                            country_code, mobile_number, kewarganegaraan,
                            tanggal_lahir, email,
                        ])

                        if role == 'Staf':
                            kode_maskapai = request.POST.get('kode_maskapai')
                            cursor.execute("""
                                UPDATE staf
                                SET kode_maskapai = %s
                                WHERE LOWER(email) = LOWER(%s)
                            """, [kode_maskapai, email])

                messages.success(request, 'Profil berhasil diperbarui.')
            except DatabaseError as error:
                messages.error(request, _clean_db_error(error))

            return redirect('feat_hijau:pengaturan_profil')

        if action == 'ubah_password':
            password_lama = request.POST.get('password_lama')
            password_baru = request.POST.get('password_baru')
            konfirmasi = request.POST.get('konfirmasi_password_baru')

            if password_baru != konfirmasi:
                messages.error(request, 'Password baru dan konfirmasi tidak cocok.')
                return redirect('feat_hijau:pengaturan_profil')

            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT check_kredensial(%s, %s)", [email, password_lama])
                        is_valid_password = cursor.fetchone()[0]

                        if not is_valid_password:
                            messages.error(request, 'Password lama salah.')
                            return redirect('feat_hijau:pengaturan_profil')

                        cursor.execute("""
                            UPDATE pengguna
                            SET password = extensions.crypt(%s, extensions.gen_salt('bf'))
                            WHERE LOWER(email) = LOWER(%s)
                        """, [password_baru, email])

                messages.success(request, 'Password berhasil diubah.')
            except DatabaseError as error:
                messages.error(request, _clean_db_error(error))

            return redirect('feat_hijau:pengaturan_profil')

    context = {
        'pengguna': pengguna,
        'extra': extra,
        'role': role,
        'maskapai_list': maskapai_list,
        'active_page': 'pengaturan_profil',
        'salutation_list': ['Mr.', 'Mrs.', 'Ms.', 'Dr.'],
        'country_code_list': ['+62', '+1', '+44', '+65', '+81', '+82', '+60', '+66', '+84', '+61', '+49', '+33', '+86'],
    }
    return render(request, 'pengaturan_profil.html', context)


@member_required
def klaim_miles(request):
    email = request.session['email']
    status_filter = request.GET.get('status', 'semua').lower()
    if status_filter not in STATUS_KLAIM:
        status_filter = 'semua'

    query = """
        SELECT c.id, c.maskapai, mk.nama_maskapai, c.bandara_asal, c.bandara_tujuan,
               c.tanggal_penerbangan, c.flight_number, c.nomor_tiket, c.kelas_kabin,
               c.pnr, c.status_penerimaan, c.timestamp, c.email_staf
        FROM claim_missing_miles c
        LEFT JOIN maskapai mk ON c.maskapai = mk.kode_maskapai
        WHERE LOWER(c.email_member) = LOWER(%s)
    """
    params = [email]

    if STATUS_KLAIM[status_filter] is not None:
        query += " AND c.status_penerimaan = %s"
        params.append(STATUS_KLAIM[status_filter])

    query += " ORDER BY c.timestamp DESC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        klaim_list = _fetchall_dict(cursor)

    context = {
        'klaim_list': klaim_list,
        'maskapai_list': _get_maskapai_list(),
        'bandara_list': _get_bandara_list(),
        'status_filter': status_filter,
        'active_page': 'klaim_miles',
    }
    return render(request, 'klaim_miles.html', context)


@member_required
@require_POST
def klaim_baru(request):
    email = request.session['email']
    maskapai = request.POST.get('maskapai')
    bandara_asal = request.POST.get('bandara_asal')
    bandara_tujuan = request.POST.get('bandara_tujuan')
    tanggal_penerbangan = request.POST.get('tanggal_penerbangan')
    flight_number = request.POST.get('flight_number', '').strip().upper()
    nomor_tiket = request.POST.get('nomor_tiket', '').strip().upper()
    kelas_kabin = request.POST.get('kelas_kabin')
    pnr = request.POST.get('pnr', '').strip().upper()

    required_fields = [
        maskapai, bandara_asal, bandara_tujuan, tanggal_penerbangan,
        flight_number, nomor_tiket, kelas_kabin, pnr,
    ]
    if not all(required_fields):
        messages.error(request, 'Semua field klaim wajib diisi.')
        return redirect('feat_hijau:klaim_miles')

    if kelas_kabin not in KELAS_KABIN:
        messages.error(request, 'Kelas kabin tidak valid.')
        return redirect('feat_hijau:klaim_miles')

    if bandara_asal == bandara_tujuan:
        messages.error(request, 'Bandara asal dan tujuan tidak boleh sama.')
        return redirect('feat_hijau:klaim_miles')

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO claim_missing_miles
                      (email_member, maskapai, bandara_asal, bandara_tujuan,
                       tanggal_penerbangan, flight_number, nomor_tiket,
                       kelas_kabin, pnr, status_penerimaan, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Menunggu', NOW())
                """, [
                    email, maskapai, bandara_asal, bandara_tujuan,
                    tanggal_penerbangan, flight_number, nomor_tiket, kelas_kabin, pnr,
                ])
        messages.success(request, 'Klaim berhasil diajukan.')
    except DatabaseError as error:
        messages.error(request, _clean_db_error(error))

    return redirect('feat_hijau:klaim_miles')


@member_required
@require_POST
def klaim_edit(request, klaim_id):
    email = request.session['email']
    maskapai = request.POST.get('maskapai')
    bandara_asal = request.POST.get('bandara_asal')
    bandara_tujuan = request.POST.get('bandara_tujuan')
    tanggal_penerbangan = request.POST.get('tanggal_penerbangan')
    flight_number = request.POST.get('flight_number', '').strip().upper()
    nomor_tiket = request.POST.get('nomor_tiket', '').strip().upper()
    kelas_kabin = request.POST.get('kelas_kabin')
    pnr = request.POST.get('pnr', '').strip().upper()

    if kelas_kabin not in KELAS_KABIN:
        messages.error(request, 'Kelas kabin tidak valid.')
        return redirect('feat_hijau:klaim_miles')

    if bandara_asal == bandara_tujuan:
        messages.error(request, 'Bandara asal dan tujuan tidak boleh sama.')
        return redirect('feat_hijau:klaim_miles')

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE claim_missing_miles
                    SET maskapai = %s,
                        bandara_asal = %s,
                        bandara_tujuan = %s,
                        tanggal_penerbangan = %s,
                        flight_number = %s,
                        nomor_tiket = %s,
                        kelas_kabin = %s,
                        pnr = %s
                    WHERE id = %s
                      AND LOWER(email_member) = LOWER(%s)
                      AND status_penerimaan = 'Menunggu'
                """, [
                    maskapai, bandara_asal, bandara_tujuan, tanggal_penerbangan,
                    flight_number, nomor_tiket, kelas_kabin, pnr, klaim_id, email,
                ])

                if cursor.rowcount == 0:
                    messages.error(request, 'Klaim tidak dapat diedit karena tidak ditemukan atau sudah diproses.')
                else:
                    messages.success(request, 'Klaim berhasil diperbarui.')
    except DatabaseError as error:
        # Jika ada trigger/constraint database yang menolak update, tampilkan pesan dari database.
        messages.error(request, _clean_db_error(error))

    return redirect('feat_hijau:klaim_miles')


@member_required
@require_POST
def klaim_hapus(request, klaim_id):
    email = request.session['email']

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM claim_missing_miles
                    WHERE id = %s
                      AND LOWER(email_member) = LOWER(%s)
                      AND status_penerimaan = 'Menunggu'
                """, [klaim_id, email])

                if cursor.rowcount == 0:
                    messages.error(request, 'Klaim tidak dapat dibatalkan karena tidak ditemukan atau sudah diproses.')
                else:
                    messages.success(request, 'Klaim berhasil dibatalkan.')
    except DatabaseError as error:
        messages.error(request, _clean_db_error(error))

    return redirect('feat_hijau:klaim_miles')


@member_required
def klaim_detail_json(request, klaim_id):
    email = request.session['email']
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, maskapai, bandara_asal, bandara_tujuan,
                   tanggal_penerbangan, flight_number, nomor_tiket,
                   kelas_kabin, pnr, status_penerimaan
            FROM claim_missing_miles
            WHERE id = %s
              AND LOWER(email_member) = LOWER(%s)
              AND status_penerimaan = 'Menunggu'
        """, [klaim_id, email])
        data = _fetchone_dict(cursor)

    if data is None:
        return JsonResponse({'error': 'Klaim tidak ditemukan atau sudah diproses.'}, status=404)

    data['tanggal_penerbangan'] = str(data['tanggal_penerbangan'])
    return JsonResponse(data)


@staf_required
def kelola_klaim(request):
    status_filter = request.GET.get('status', 'semua').lower()
    maskapai_filter = request.GET.get('maskapai', 'semua')
    tanggal_dari = request.GET.get('tanggal_dari', '')
    tanggal_sampai = request.GET.get('tanggal_sampai', '')

    if status_filter not in STATUS_KLAIM:
        status_filter = 'semua'

    query = """
        SELECT c.id, c.email_member,
               TRIM(p.first_mid_name || ' ' || p.last_name) AS nama_member,
               c.maskapai, mk.nama_maskapai,
               c.bandara_asal, ba.kota AS kota_asal,
               c.bandara_tujuan, bt.kota AS kota_tujuan,
               c.tanggal_penerbangan, c.flight_number,
               c.nomor_tiket, c.kelas_kabin, c.pnr,
               c.timestamp, c.status_penerimaan, c.email_staf
        FROM claim_missing_miles c
        LEFT JOIN pengguna p ON c.email_member = p.email
        LEFT JOIN maskapai mk ON c.maskapai = mk.kode_maskapai
        LEFT JOIN bandara ba ON c.bandara_asal = ba.iata_code
        LEFT JOIN bandara bt ON c.bandara_tujuan = bt.iata_code
        WHERE 1 = 1
    """
    params = []

    if STATUS_KLAIM[status_filter] is not None:
        query += " AND c.status_penerimaan = %s"
        params.append(STATUS_KLAIM[status_filter])

    if maskapai_filter != 'semua':
        query += " AND c.maskapai = %s"
        params.append(maskapai_filter)

    if tanggal_dari:
        query += " AND c.timestamp::date >= %s"
        params.append(tanggal_dari)

    if tanggal_sampai:
        query += " AND c.timestamp::date <= %s"
        params.append(tanggal_sampai)

    query += " ORDER BY c.timestamp DESC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        klaim_list = _fetchall_dict(cursor)

    context = {
        'klaim_list': klaim_list,
        'maskapai_list': _get_maskapai_list(),
        'status_filter': status_filter,
        'maskapai_filter': maskapai_filter,
        'tanggal_dari': tanggal_dari,
        'tanggal_sampai': tanggal_sampai,
        'active_page': 'kelola_klaim',
    }
    return render(request, 'kelola_klaim.html', context)


@staf_required
@require_POST
def update_status_klaim(request, klaim_id):
    email_staf = request.session['email']
    new_status = request.POST.get('status')

    if new_status not in ('Disetujui', 'Ditolak'):
        messages.error(request, 'Status tidak valid.')
        return redirect('feat_hijau:kelola_klaim')

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.email_member, c.flight_number, t.nama AS tier_lama
                    FROM claim_missing_miles c
                    JOIN member m ON c.email_member = m.email
                    JOIN tier t ON m.id_tier = t.id_tier
                    WHERE c.id = %s
                """, [klaim_id])
                data_awal = cursor.fetchone()

                cursor.execute(
                    "CALL sp_proses_claim_missing_miles(%s, %s, %s)",
                    [klaim_id, email_staf, new_status]
                )

                if data_awal:
                    email_member = data_awal[0]
                    flight_number = data_awal[1]
                    tier_lama = data_awal[2]

                    cursor.execute("""
                        SELECT t.nama
                        FROM member m
                        JOIN tier t ON m.id_tier = t.id_tier
                        WHERE m.email = %s
                    """, [email_member])
                    row_tier_baru = cursor.fetchone()
                    tier_baru = row_tier_baru[0] if row_tier_baru else tier_lama

                    if new_status == 'Disetujui':
                        if tier_lama != tier_baru:
                            messages.success(
                                request,
                                f'SUKSES: Tier Member "{email_member}" telah diperbarui dari "{tier_lama}" menjadi "{tier_baru}" berdasarkan total miles yang dimiliki.'
                            )
                        else:
                            messages.success(
                                request,
                                f'SUKSES: Total miles Member "{email_member}" telah diperbarui dari klaim penerbangan "{flight_number}".'
                            )
                    else:
                        messages.success(
                            request,
                            f'SUKSES: Klaim penerbangan "{flight_number}" milik Member "{email_member}" berhasil ditolak.'
                        )
                else:
                    messages.success(request, 'SUKSES: Proses klaim berhasil.')

    except DatabaseError as error:
        messages.error(request, _clean_db_error(error))

    return redirect('feat_hijau:kelola_klaim')

@member_required
def transfer_miles(request):
    email = request.session['email']

    with connection.cursor() as cursor:
        cursor.execute("SELECT award_miles FROM member WHERE LOWER(email) = LOWER(%s)", [email])
        row = cursor.fetchone()
        award_miles = row[0] if row else 0

        cursor.execute("""
            SELECT t.email_member_1, t.email_member_2, t.timestamp, t.jumlah, t.catatan,
                   TRIM(p1.first_mid_name || ' ' || p1.last_name) AS nama_pengirim,
                   TRIM(p2.first_mid_name || ' ' || p2.last_name) AS nama_penerima
            FROM transfer t
            LEFT JOIN pengguna p1 ON t.email_member_1 = p1.email
            LEFT JOIN pengguna p2 ON t.email_member_2 = p2.email
            WHERE LOWER(t.email_member_1) = LOWER(%s)
               OR LOWER(t.email_member_2) = LOWER(%s)
            ORDER BY t.timestamp DESC
        """, [email, email])
        transfer_list = _fetchall_dict(cursor)

    for item in transfer_list:
        is_pengirim = item['email_member_1'].lower() == email.lower()
        item['tipe'] = 'Kirim' if is_pengirim else 'Terima'
        item['jumlah_display'] = -item['jumlah'] if is_pengirim else item['jumlah']
        item['member_lawan'] = item['nama_penerima'] if is_pengirim else item['nama_pengirim']
        item['email_lawan'] = item['email_member_2'] if is_pengirim else item['email_member_1']

    context = {
        'transfer_list': transfer_list,
        'award_miles': award_miles,
        'active_page': 'transfer_miles',
    }
    return render(request, 'transfer_miles.html', context)

@member_required
@require_POST
def transfer_baru(request):
    email_pengirim = request.session['email']
    email_penerima = request.POST.get('email_penerima', '').strip().lower()
    jumlah_str = request.POST.get('jumlah', '0')
    catatan = request.POST.get('catatan', '').strip() or None

    try:
        jumlah = int(jumlah_str)
    except (TypeError, ValueError):
        messages.error(request, 'Jumlah miles tidak valid.')
        return redirect('feat_hijau:transfer_miles')

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Ambil tier penerima sebelum transfer
                cursor.execute("""
                    SELECT t.nama
                    FROM member m
                    JOIN tier t ON m.id_tier = t.id_tier
                    WHERE LOWER(m.email) = LOWER(%s)
                """, [email_penerima])
                row_tier_lama = cursor.fetchone()
                tier_lama = row_tier_lama[0] if row_tier_lama else None

                # Panggil stored procedure versi sederhana: 4 parameter
                cursor.execute(
                    "CALL sp_transfer_miles(%s, %s, %s, %s)",
                    [email_pengirim, email_penerima, jumlah, catatan]
                )

                # Ambil tier penerima setelah transfer
                cursor.execute("""
                    SELECT t.nama
                    FROM member m
                    JOIN tier t ON m.id_tier = t.id_tier
                    WHERE LOWER(m.email) = LOWER(%s)
                """, [email_penerima])
                row_tier_baru = cursor.fetchone()
                tier_baru = row_tier_baru[0] if row_tier_baru else tier_lama

        pesan = f'SUKSES: Transfer {jumlah} miles dari "{email_pengirim}" ke "{email_penerima}" berhasil dicatat.'

        if tier_lama and tier_baru and tier_lama != tier_baru:
            pesan += f' SUKSES: Tier Member "{email_penerima}" telah diperbarui dari "{tier_lama}" menjadi "{tier_baru}" berdasarkan total miles yang dimiliki.'

        messages.success(request, pesan)

    except DatabaseError as error:
        messages.error(request, _clean_db_error(error))

    return redirect('feat_hijau:transfer_miles')