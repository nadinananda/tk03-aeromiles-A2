from django.shortcuts import render, redirect

def check_role(request, expected_role):
    return request.session.get('role') == expected_role

def redeem_hadiah_view(request):
    if not check_role(request, 'Member'):
        return redirect('main:dashboard')

    context = {
        'hadiah_list': [
            {'kode': 'RWD-001', 'nama': 'Tiket Domestik PP', 'miles': 15000, 'penyedia': 'Garuda Indonesia', 'berlaku_sampai': '2025-12-31'},
            {'kode': 'RWD-002', 'nama': 'Upgrade Business Class', 'miles': 25000, 'penyedia': 'Garuda Indonesia', 'berlaku_sampai': '2025-12-31'},
            {'kode': 'RWD-003', 'nama': 'Akses Lounge 1x', 'miles': 3000, 'penyedia': 'Angkasa Pura', 'berlaku_sampai': '2025-06-30'},
        ]
    }
    return render(request, 'redeem_hadiah.html', context)


def beli_package_view(request):
    if not check_role(request, 'Member'):
        return redirect('main:dashboard')

    context = {
        'package_list': [
            {'id': 'AMP-001', 'jumlah_miles': 1000, 'harga': '150.000'},
            {'id': 'AMP-002', 'jumlah_miles': 5000, 'harga': '650.000'},
            {'id': 'AMP-003', 'jumlah_miles': 10000, 'harga': '1.200.000'},
        ]
    }
    return render(request, 'beli_package.html', context)



def info_tier_view(request):
    if not check_role(request, 'Member'):
        return redirect('main:dashboard')

    context = {
        'tier_sekarang': 'Gold',
        'miles_sekarang': 45000,
        'syarat_next_tier': 50000, 
        'next_tier': 'Platinum',
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

    context = {
        'transaksi_list': [
            {'id_trx': 'TRX-001', 'jenis': 'Redeem Hadiah', 'pelaku': 'member@aeromiles.com', 'waktu': '2025-01-20 16:00', 'detail': 'Tiket Domestik PP'},
            {'id_trx': 'TRX-002', 'jenis': 'Beli Package', 'pelaku': 'jane@aeromiles.com', 'waktu': '2025-02-01 09:15', 'detail': 'Package 1000 Miles'},
            {'id_trx': 'TRX-003', 'jenis': 'Transfer', 'pelaku': 'member@aeromiles.com -> jane@aeromiles.com', 'waktu': '2025-01-15 10:30', 'detail': 'Transfer 5000 Miles'},
        ]
    }    
    return render(request, 'laporan_transaksi.html', context)