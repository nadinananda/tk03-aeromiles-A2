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

    # Handle POST (Proses Beli Package)
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

    # Handle GET (Tampilin Daftar Package)
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

    with connection.cursor() as cursor:
        # Ambil data tier sekarang
        cursor.execute("""
            SELECT t.nama, m.total_miles 
            FROM aeromiles.MEMBER m
            JOIN aeromiles.TIER t ON m.id_tier = t.id_tier
            WHERE m.email = %s
        """, [email_user])
        member_data = cursor.fetchone()
        
        tier_sekarang = member_data[0] if member_data else 'Blue'
        miles_sekarang = member_data[1] if member_data else 0

        # Cari tau next tier
        cursor.execute("""
            SELECT nama, minimal_tier_miles 
            FROM aeromiles.TIER
            WHERE minimal_tier_miles > %s
            ORDER BY minimal_tier_miles ASC
            LIMIT 1
        """, [miles_sekarang])
        next_tier_data = cursor.fetchone()

    if next_tier_data:
        next_tier = next_tier_data[0]
        syarat_next_tier = next_tier_data[1] - miles_sekarang
    else:
        next_tier = "Maksimal (Platinum)"
        syarat_next_tier = 0

    context = {
        'tier_sekarang': tier_sekarang,
        'miles_sekarang': miles_sekarang,
        'syarat_next_tier': syarat_next_tier,
        'next_tier': next_tier,
        'keuntungan_list': [
            'Prioritas Check-in di counter khusus',
            'Akses Executive Lounge Gratis',
            'Ekstra kuota bagasi 15kg',
            'Prioritas boarding'
        ]
    }
    return render(request, 'info_tier.html', context)


def laporan_transaksi_view(request):
    if not check_role(request, 'Staf'):
        return redirect('main:dashboard')

    with connection.cursor() as cursor:
        # Pake UNION ALL buat gabungin 3 jenis transaksi jadi satu tabel
        cursor.execute("""
            SELECT 'TRX-R' || ROW_NUMBER() OVER(ORDER BY timestamp DESC) AS id_trx, 
                   'Redeem Hadiah' AS jenis, email_member AS pelaku, timestamp AS waktu, kode_hadiah AS detail
            FROM aeromiles.REDEEM
            UNION ALL
            SELECT 'TRX-P' || ROW_NUMBER() OVER(ORDER BY timestamp DESC), 
                   'Beli Package', email_member, timestamp, id_award_miles_package
            FROM aeromiles.MEMBER_AWARD_MILES_PACKAGE
            UNION ALL
            SELECT 'TRX-T' || ROW_NUMBER() OVER(ORDER BY timestamp DESC), 
                   'Transfer', email_member_1 || ' -> ' || email_member_2, timestamp, 'Transfer ' || jumlah || ' Miles'
            FROM aeromiles.TRANSFER
            ORDER BY waktu DESC
        """)
        rows = cursor.fetchall()

    transaksi_list = []
    for r in rows:
        transaksi_list.append({
            'id_trx': r[0],
            'jenis': r[1],
            'pelaku': r[2],
            'waktu': r[3].strftime("%Y-%m-%d %H:%M") if hasattr(r[3], 'strftime') else str(r[3]),
            'detail': r[4]
        })

    return render(request, 'laporan_transaksi.html', {'transaksi_list': transaksi_list})
