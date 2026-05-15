from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages

def check_role(request, expected_role):
    return request.session.get('role') == expected_role

def redeem_hadiah_view(request):
    return redirect('feat_merah:member_redeem')


def beli_package_view(request):
    if not check_role(request, 'Member'):
        return redirect('main:dashboard')

    email_user = request.session.get('email')

    if request.method == 'POST':
        id_package = request.POST.get('id_package')
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO aeromiles.MEMBER_AWARD_MILES_PACKAGE (id_award_miles_package, email_member, timestamp)
                    VALUES (%s, %s, NOW())
                """, [id_package, email_user])
            messages.success(request, 'Pembelian package berhasil!')
        except Exception as e:
            messages.error(request, f'Gagal beli package: {str(e)}')
        return redirect('feat_biru:beli_package')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, jumlah_award_miles, harga_paket 
            FROM aeromiles.AWARD_MILES_PACKAGE
        """)
        rows = cursor.fetchall()

    package_list = []
    for r in rows:
        package_list.append({
            'id': r[0],
            'jumlah_miles': r[1],
            'harga': f"{r[2]:,.0f}".replace(',', '.')
        })

    return render(request, 'beli_package.html', {'package_list': package_list})


def info_tier_view(request):
    if not check_role(request, 'Member'):
        return redirect('main:dashboard')

    email_user = request.session.get('email')

    benefits_map = {
        'Blue': ['E-boarding pass', 'Dapatkan miles di setiap penerbangan'],
        'Silver': ['Semua benefit Blue', 'Prioritas Check-in di counter khusus', 'Ekstra kuota bagasi 5kg'],
        'Gold': ['Semua benefit Silver', 'Akses Executive Lounge Gratis', 'Ekstra kuota bagasi 15kg', 'Prioritas boarding'],
        'Platinum': ['Semua benefit Gold', 'Ekstra kuota bagasi 20kg', 'Pemilihan kursi gratis', 'Layanan First Class check-in']
    }

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT total_miles 
            FROM aeromiles.MEMBER
            WHERE email = %s
        """, [email_user])
        member_data = cursor.fetchone()
        miles_sekarang = member_data[0] if member_data else 0

        cursor.execute("""
            SELECT nama 
            FROM aeromiles.TIER
            WHERE minimal_tier_miles <= %s
            ORDER BY minimal_tier_miles DESC
            LIMIT 1
        """, [miles_sekarang])
        tier_data = cursor.fetchone()
        tier_sekarang = tier_data[0] if tier_data else 'Blue'

        cursor.execute("""
            SELECT id_tier, nama, minimal_frekuensi_terbang, minimal_tier_miles
            FROM aeromiles.TIER
            ORDER BY minimal_tier_miles ASC
        """)
        semua_tier_rows = cursor.fetchall()

        semua_tier = []
        batas_next_tier = None
        next_tier = "Maksimal (Platinum)"

        for row in semua_tier_rows:
            nama_tier = row[1]
            semua_tier.append({
                'id': row[0],
                'nama': nama_tier,
                'min_terbang': row[2],
                'min_miles': f"{row[3]:,}",
                'keuntungan': benefits_map.get(nama_tier, ['Keuntungan segera hadir!'])
            })
            
            if row[3] > miles_sekarang and batas_next_tier is None:
                next_tier = nama_tier
                batas_next_tier = row[3]

    if batas_next_tier:
        syarat_next_tier = batas_next_tier - miles_sekarang
        persentase = int((miles_sekarang / batas_next_tier) * 100)
        max_progress_miles = batas_next_tier
    else:
        syarat_next_tier = 0
        persentase = 100
        max_progress_miles = miles_sekarang

    context = {
        'tier_sekarang': tier_sekarang,
        'miles_sekarang': f"{miles_sekarang:,}",
        'syarat_next_tier': f"{syarat_next_tier:,}",
        'next_tier': next_tier,
        'persentase': persentase,
        'max_progress_miles': f"{max_progress_miles:,}",
        'semua_tier': semua_tier
    }
    return render(request, 'info_tier.html', context)


def laporan_transaksi_view(request):
    if not check_role(request, 'Staf'):
        return redirect('main:dashboard')

    # Handle POST (Proses Hapus Riwayat Transaksi)
    if request.method == 'POST':
        tabel_asal = request.POST.get('tabel_asal')
        pk1 = request.POST.get('pk1')
        pk2 = request.POST.get('pk2')
        pk3 = request.POST.get('pk3')
        
        try:
            with connection.cursor() as cursor:
                if tabel_asal == 'TRANSFER':
                    cursor.execute("DELETE FROM aeromiles.TRANSFER WHERE email_member_1=%s AND email_member_2=%s AND timestamp=%s", [pk1, pk2, pk3])
                elif tabel_asal == 'REDEEM':
                    cursor.execute("DELETE FROM aeromiles.REDEEM WHERE email_member=%s AND kode_hadiah=%s AND timestamp=%s", [pk1, pk2, pk3])
                elif tabel_asal == 'PACKAGE':
                    cursor.execute("DELETE FROM aeromiles.MEMBER_AWARD_MILES_PACKAGE WHERE email_member=%s AND id_award_miles_package=%s AND timestamp=%s", [pk1, pk2, pk3])
            messages.success(request, 'Berhasil! Riwayat transaksi telah dihapus permanen.')
        except Exception as e:
            messages.error(request, f'Gagal menghapus riwayat: {str(e)}')
        return redirect('feat_biru:laporan_transaksi')

    with connection.cursor() as cursor:
        # 1. Ambil Summary (Cards)
        cursor.execute("SELECT SUM(total_miles) FROM aeromiles.MEMBER")
        total_miles_beredar = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM aeromiles.REDEEM 
            WHERE EXTRACT(MONTH FROM timestamp) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM timestamp) = EXTRACT(YEAR FROM CURRENT_DATE)
        """)
        total_redeem_bulan_ini = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM aeromiles.CLAIM_MISSING_MILES WHERE status_penerimaan = 'Disetujui'")
        total_klaim_disetujui = cursor.fetchone()[0] or 0

        # 2. Ambil Riwayat Transaksi (UNION ALL)
        cursor.execute("""
            SELECT 'TRANSFER' as tabel_asal, email_member_1 as pk1, email_member_2 as pk2, timestamp::text as pk3,
                   'Transfer' as tipe, email_member_1 || ' -> ' || email_member_2 as member, 
                   -jumlah as miles, timestamp as waktu
            FROM aeromiles.TRANSFER
            UNION ALL
            SELECT 'REDEEM' as tabel_asal, r.email_member as pk1, r.kode_hadiah as pk2, r.timestamp::text as pk3,
                   'Redeem' as tipe, r.email_member as member, 
                   -h.miles as miles, r.timestamp as waktu
            FROM aeromiles.REDEEM r
            JOIN aeromiles.HADIAH h ON r.kode_hadiah = h.kode_hadiah
            UNION ALL
            SELECT 'PACKAGE' as tabel_asal, m.email_member as pk1, m.id_award_miles_package as pk2, m.timestamp::text as pk3,
                   'Package' as tipe, m.email_member as member, 
                   a.jumlah_award_miles as miles, m.timestamp as waktu
            FROM aeromiles.MEMBER_AWARD_MILES_PACKAGE m
            JOIN aeromiles.AWARD_MILES_PACKAGE a ON m.id_award_miles_package = a.id
            UNION ALL
            SELECT 'KLAIM' as tabel_asal, email_member as pk1, id::text as pk2, timestamp::text as pk3,
                   'Klaim' as tipe, email_member as member, 
                   2500 as miles, timestamp as waktu
            FROM aeromiles.CLAIM_MISSING_MILES
            WHERE status_penerimaan = 'Disetujui'
            ORDER BY waktu DESC
        """)
        rows = cursor.fetchall()

        transaksi_list = []
        for r in rows:
            transaksi_list.append({
                'tabel_asal': r[0],
                'pk1': r[1],
                'pk2': r[2],
                'pk3': r[3],
                'tipe': r[4],
                'member': r[5],
                'miles': f"{r[6]:,}",
                'waktu': r[7].strftime("%Y-%m-%d %H:%M") if hasattr(r[7], 'strftime') else str(r[7]),
                'bisa_dihapus': r[0] != 'KLAIM' 
            })

        # 3. LEADERBOARD (Top 5 Member logic terintegrasi dari fitur merah)
        cursor.execute("""
            SELECT 
                ROW_NUMBER() OVER (ORDER BY m.total_miles DESC) AS rank,
                TRIM(p.first_mid_name || ' ' || COALESCE(p.last_name, '')) AS nama_lengkap,
                m.email,
                m.total_miles,
                (SELECT COUNT(*) FROM aeromiles.TRANSFER t WHERE t.email_member_1 = m.email) +
                (SELECT COUNT(*) FROM aeromiles.REDEEM r WHERE r.email_member = m.email) AS jumlah_transaksi
            FROM aeromiles.MEMBER m
            JOIN aeromiles.PENGGUNA p ON m.email = p.email
            ORDER BY m.total_miles DESC
            LIMIT 5
        """)
        top_rows = cursor.fetchall()
        
        top_5_members = []
        for r in top_rows:
            top_5_members.append({
                'rank': r[0],
                'nama': r[1],
                'email': r[2],
                'total_miles': f"{r[3]:,}",
                'jumlah_transaksi': r[4]
            })

    context = {
        'total_miles_beredar': f"{total_miles_beredar:,}",
        'total_redeem_bulan_ini': f"{total_redeem_bulan_ini:,}",
        'total_klaim_disetujui': f"{total_klaim_disetujui:,}",
        'transaksi_list': transaksi_list,
        'top_5_members': top_5_members  # <-- Dikirim ke HTML!
    }

    return render(request, 'laporan_transaksi.html', context)