from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import hashlib
import json

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required_custom(view_func):
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def member_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        if request.session.get('role') != 'Member':
            return redirect('main:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def staf_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'email' not in request.session:
            return redirect('main:login')
        if request.session.get('role') != 'Staf':
            return redirect('main:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def get_pengguna(email):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pengguna WHERE email = %s", [email])
        cols = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None


def get_member(email):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.*, t.nama AS nama_tier
            FROM member m
            LEFT JOIN tier t ON m.id_tier = t.id_tier
            WHERE m.email = %s
        """, [email])
        cols = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None


def get_staf(email):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.*, mk.nama_maskapai
            FROM staf s
            LEFT JOIN maskapai mk ON s.kode_maskapai = mk.kode_maskapai
            WHERE s.email = %s
        """, [email])
        cols = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else None

@login_required_custom
def pengaturan_profil(request):
    email = request.session['email']
    role = request.session.get('role')
    pengguna = get_pengguna(email)
    extra = get_member(email) if role == 'member' else get_staf(email)

    with connection.cursor() as cursor:
        cursor.execute("SELECT kode_maskapai, nama_maskapai FROM maskapai ORDER BY nama_maskapai")
        maskapai_list = [{'kode': r[0], 'nama': r[1]} for r in cursor.fetchall()]

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

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE pengguna SET salutation=%s, first_mid_name=%s, last_name=%s,
                    country_code=%s, mobile_number=%s, kewarganegaraan=%s, tanggal_lahir=%s
                    WHERE email=%s
                """, [salutation, first_mid_name, last_name,
                      country_code, mobile_number, kewarganegaraan, tanggal_lahir, email])

            if role == 'staf':
                kode_maskapai = request.POST.get('kode_maskapai')
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE staf SET kode_maskapai=%s WHERE email=%s",
                                   [kode_maskapai, email])

            messages.success(request, 'Profil berhasil diperbarui.')
            return redirect('pengaturan_profil')

        elif action == 'ubah_password':
            password_lama = request.POST.get('password_lama')
            password_baru = request.POST.get('password_baru')
            konfirmasi = request.POST.get('konfirmasi_password_baru')

            if password_baru != konfirmasi:
                messages.error(request, 'Password baru dan konfirmasi tidak cocok.')
            elif hash_password(password_lama) != pengguna['password']:
                messages.error(request, 'Password lama salah.')
            else:
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE pengguna SET password=%s WHERE email=%s",
                                   [hash_password(password_baru), email])
                messages.success(request, 'Password berhasil diubah.')
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
    status_filter = request.GET.get('status', 'semua')

    query = """
        SELECT c.id, c.maskapai, mk.nama_maskapai, c.bandara_asal, c.bandara_tujuan,
               c.tanggal_penerbangan, c.flight_number, c.kelas_kabin,
               c.status_penerimaan, c.timestamp
        FROM claim_missing_miles c
        LEFT JOIN maskapai mk ON c.maskapai = mk.kode_maskapai
        WHERE c.email_member = %s
    """
    params = [email]
    if status_filter != 'semua':
        query += " AND LOWER(c.status_penerimaan) = %s"
        params.append(status_filter.lower())
    query += " ORDER BY c.timestamp DESC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        cols = [col[0] for col in cursor.description]
        klaim_list = [dict(zip(cols, row)) for row in cursor.fetchall()]

        cursor.execute("SELECT kode_maskapai, nama_maskapai FROM maskapai ORDER BY nama_maskapai")
        maskapai_list = [{'kode': r[0], 'nama': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT iata_code, nama, kota FROM bandara ORDER BY iata_code")
        bandara_list = [{'iata': r[0], 'nama': r[1], 'kota': r[2]} for r in cursor.fetchall()]

    context = {
        'klaim_list': klaim_list,
        'maskapai_list': maskapai_list,
        'bandara_list': bandara_list,
        'status_filter': status_filter,
        'active_page': 'klaim_miles',
    }
    return render(request, 'klaim_miles.html', context)

@member_required
def klaim_baru(request):
    if request.method != 'POST':
        return redirect('klaim_miles')

    email = request.session['email']
    maskapai = request.POST.get('maskapai')
    bandara_asal = request.POST.get('bandara_asal')
    bandara_tujuan = request.POST.get('bandara_tujuan')
    tanggal_penerbangan = request.POST.get('tanggal_penerbangan')
    flight_number = request.POST.get('flight_number')
    nomor_tiket = request.POST.get('nomor_tiket')
    kelas_kabin = request.POST.get('kelas_kabin')
    pnr = request.POST.get('pnr')

    # Cek duplikat
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM claim_missing_miles
            WHERE email_member=%s AND flight_number=%s
              AND tanggal_penerbangan=%s AND nomor_tiket=%s
        """, [email, flight_number, tanggal_penerbangan, nomor_tiket])
        if cursor.fetchone():
            messages.error(request, 'Klaim duplikat: penerbangan yang sama sudah pernah diajukan.')
            return redirect('klaim_miles')

        cursor.execute("""
            INSERT INTO claim_missing_miles
              (email_member, maskapai, bandara_asal, bandara_tujuan,
               tanggal_penerbangan, flight_number, nomor_tiket,
               kelas_kabin, pnr, status_penerimaan, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Menunggu', NOW())
        """, [email, maskapai, bandara_asal, bandara_tujuan,
              tanggal_penerbangan, flight_number, nomor_tiket, kelas_kabin, pnr])

    messages.success(request, 'Klaim berhasil diajukan.')
    return redirect('klaim_miles')

@member_required
def klaim_edit(request, klaim_id):
    if request.method != 'POST':
        return redirect('klaim_miles')

    email = request.session['email']

    # Pastikan klaim milik member ini dan masih Menunggu
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM claim_missing_miles
            WHERE id=%s AND email_member=%s AND status_penerimaan='Menunggu'
        """, [klaim_id, email])
        if not cursor.fetchone():
            messages.error(request, 'Klaim tidak dapat diedit.')
            return redirect('klaim_miles')

        cursor.execute("""
            UPDATE claim_missing_miles SET
              maskapai=%s, bandara_asal=%s, bandara_tujuan=%s,
              tanggal_penerbangan=%s, flight_number=%s,
              nomor_tiket=%s, kelas_kabin=%s, pnr=%s
            WHERE id=%s AND email_member=%s
        """, [
            request.POST.get('maskapai'),
            request.POST.get('bandara_asal'),
            request.POST.get('bandara_tujuan'),
            request.POST.get('tanggal_penerbangan'),
            request.POST.get('flight_number'),
            request.POST.get('nomor_tiket'),
            request.POST.get('kelas_kabin'),
            request.POST.get('pnr'),
            klaim_id, email
        ])

    messages.success(request, 'Klaim berhasil diperbarui.')
    return redirect('klaim_miles')

@member_required
def klaim_hapus(request, klaim_id):
    if request.method != 'POST':
        return redirect('klaim_miles')

    email = request.session['email']
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM claim_missing_miles
            WHERE id=%s AND email_member=%s AND status_penerimaan='Menunggu'
        """, [klaim_id, email])
        if cursor.rowcount == 0:
            messages.error(request, 'Klaim tidak dapat dibatalkan.')
        else:
            messages.success(request, 'Klaim berhasil dibatalkan.')

    return redirect('klaim_miles')


@member_required
def klaim_detail_json(request, klaim_id):
    """Untuk mengisi modal edit."""
    email = request.session['email']
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, maskapai, bandara_asal, bandara_tujuan,
                   tanggal_penerbangan, flight_number, nomor_tiket,
                   kelas_kabin, pnr, status_penerimaan
            FROM claim_missing_miles
            WHERE id=%s AND email_member=%s
        """, [klaim_id, email])
        cols = [col[0] for col in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({'error': 'Not found'}, status=404)
    data = dict(zip(cols, row))
    if data.get('tanggal_penerbangan'):
        data['tanggal_penerbangan'] = str(data['tanggal_penerbangan'])
    return JsonResponse(data)

@staf_required
def kelola_klaim(request):
    status_filter = request.GET.get('status', 'semua')
    maskapai_filter = request.GET.get('maskapai', 'semua')
    tanggal_dari = request.GET.get('tanggal_dari', '')
    tanggal_sampai = request.GET.get('tanggal_sampai', '')

    query = """
        SELECT c.id, c.email_member,
               p.first_mid_name || ' ' || p.last_name AS nama_member,
               c.maskapai, mk.nama_maskapai,
               c.bandara_asal, c.bandara_tujuan,
               c.tanggal_penerbangan, c.flight_number,
               c.kelas_kabin, c.timestamp, c.status_penerimaan,
               c.email_staf
        FROM claim_missing_miles c
        LEFT JOIN pengguna p ON c.email_member = p.email
        LEFT JOIN maskapai mk ON c.maskapai = mk.kode_maskapai
        WHERE 1=1
    """
    params = []
    if status_filter != 'semua':
        query += " AND LOWER(c.status_penerimaan) = %s"
        params.append(status_filter.lower())
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
        cols = [col[0] for col in cursor.description]
        klaim_list = [dict(zip(cols, row)) for row in cursor.fetchall()]

        cursor.execute("SELECT kode_maskapai, nama_maskapai FROM maskapai ORDER BY nama_maskapai")
        maskapai_list = [{'kode': r[0], 'nama': r[1]} for r in cursor.fetchall()]

    context = {
        'klaim_list': klaim_list,
        'maskapai_list': maskapai_list,
        'status_filter': status_filter,
        'maskapai_filter': maskapai_filter,
        'tanggal_dari': tanggal_dari,
        'tanggal_sampai': tanggal_sampai,
        'active_page': 'kelola_klaim',
    }
    return render(request, 'feat_hijau/kelola_klaim.html', context)

@staf_required
@require_POST
def update_status_klaim(request, klaim_id):
    email_staf = request.session['email']
    new_status = request.POST.get('status') 

    if new_status not in ('Disetujui', 'Ditolak'):
        messages.error(request, 'Status tidak valid.')
        return redirect('feat_hijau:kelola_klaim')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.email_member, c.bandara_asal, c.bandara_tujuan, c.kelas_kabin, c.maskapai
            FROM claim_missing_miles c WHERE c.id=%s AND c.status_penerimaan='Menunggu'
        """, [klaim_id])
        cols = [col[0] for col in cursor.description]
        klaim = cursor.fetchone()

    if not klaim:
        messages.error(request, 'Klaim tidak ditemukan atau sudah diproses.')
        return redirect('kelola_klaim')

    klaim = dict(zip(cols, klaim))

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE claim_missing_miles
            SET status_penerimaan=%s, email_staf=%s
            WHERE id=%s
        """, [new_status, email_staf, klaim_id])

        if new_status == 'Disetujui':
            # Hitung miles berdasarkan rute & kelas (logika sederhana)
            miles_tambah = _hitung_miles(klaim['bandara_asal'], klaim['bandara_tujuan'], klaim['kelas_kabin'])
            cursor.execute("""
                UPDATE member SET award_miles = award_miles + %s, total_miles = total_miles + %s
                WHERE email = %s
            """, [miles_tambah, miles_tambah, klaim['email_member']])

    status_label = 'disetujui' if new_status == 'Disetujui' else 'ditolak'
    messages.success(request, f'Klaim berhasil {status_label}.')
    return redirect('feat_hijau:kelola_klaim')


def _hitung_miles(bandara_asal, bandara_tujuan, kelas_kabin):
    """Hitung miles sederhana berdasarkan kelas kabin (dapat disesuaikan)."""
    base = 1000
    multiplier = {'Economy': 1, 'Premium Economy': 1.5, 'Business': 2, 'First': 3}
    return int(base * multiplier.get(kelas_kabin, 1))

@member_required
def transfer_miles(request):
    email = request.session['email']

    with connection.cursor() as cursor:
        cursor.execute("SELECT award_miles FROM member WHERE email=%s", [email])
        row = cursor.fetchone()
        award_miles = row[0] if row else 0

        cursor.execute("""
            SELECT t.email_member_1, t.email_member_2, t.timestamp, t.jumlah, t.catatan,
                   p1.first_mid_name || ' ' || p1.last_name AS nama_pengirim,
                   p2.first_mid_name || ' ' || p2.last_name AS nama_penerima
            FROM transfer t
            LEFT JOIN pengguna p1 ON t.email_member_1 = p1.email
            LEFT JOIN pengguna p2 ON t.email_member_2 = p2.email
            WHERE t.email_member_1 = %s OR t.email_member_2 = %s
            ORDER BY t.timestamp DESC
        """, [email, email])
        cols = [col[0] for col in cursor.description]
        transfer_list = [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Tandai tipe: Kirim atau Terima
    for t in transfer_list:
        t['tipe'] = 'Kirim' if t['email_member_1'] == email else 'Terima'
        t['jumlah_display'] = -t['jumlah'] if t['tipe'] == 'Kirim' else t['jumlah']
        t['member_lawan'] = t['nama_penerima'] if t['tipe'] == 'Kirim' else t['nama_pengirim']
        t['email_lawan'] = t['email_member_2'] if t['tipe'] == 'Kirim' else t['email_member_1']

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
    email_penerima = request.POST.get('email_penerima', '').strip()
    jumlah_str = request.POST.get('jumlah', '0')
    catatan = request.POST.get('catatan', '')

    try:
        jumlah = int(jumlah_str)
    except ValueError:
        messages.error(request, 'Jumlah miles tidak valid.')
        return redirect('transfer_miles')

    if email_pengirim == email_penerima:
        messages.error(request, 'Tidak dapat mentransfer miles ke diri sendiri.')
        return redirect('transfer_miles')

    if jumlah <= 0:
        messages.error(request, 'Jumlah miles harus lebih dari 0.')
        return redirect('transfer_miles')

    with connection.cursor() as cursor:
        # Cek penerima adalah member aktif
        cursor.execute("SELECT email FROM member WHERE email=%s", [email_penerima])
        if not cursor.fetchone():
            messages.error(request, 'Email penerima bukan member aktif.')
            return redirect('transfer_miles')

        # Cek saldo cukup
        cursor.execute("SELECT award_miles FROM member WHERE email=%s", [email_pengirim])
        row = cursor.fetchone()
        award_miles = row[0] if row else 0
        if award_miles < jumlah:
            messages.error(request, f'Award miles tidak mencukupi. Saldo saat ini: {award_miles} miles.')
            return redirect('transfer_miles')

        # Eksekusi transfer
        cursor.execute("""
            UPDATE member SET award_miles = award_miles - %s WHERE email = %s
        """, [jumlah, email_pengirim])
        cursor.execute("""
            UPDATE member SET award_miles = award_miles + %s WHERE email = %s
        """, [jumlah, email_penerima])
        cursor.execute("""
            INSERT INTO transfer (email_member_1, email_member_2, timestamp, jumlah, catatan)
            VALUES (%s, %s, NOW(), %s, %s)
        """, [email_pengirim, email_penerima, jumlah, catatan])

    messages.success(request, f'Transfer {jumlah} miles ke {email_penerima} berhasil.')
    return redirect('feat_hijau:transfer_miles')