from django.shortcuts import render, redirect

def identitas_member_view(request):
    # Proteksi sementara dimatikan untuk testing FE
    # if request.session.get('role') != 'Member':
    #     return redirect('main:login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'tambah':
            print("Pura-puranya nambah identitas baru...") 
        elif action == 'edit':
            print("Pura-puranya update identitas...")
        elif action == 'hapus':
            print("Pura-puranya hapus identitas...")
        return redirect('kuning:identitas_member')

    context = {
        'identitas_list': [
            {'nomor': 'A12345678', 'jenis': 'Paspor', 'negara': 'Indonesia', 'terbit': '2020-01-15', 'habis': '2030-01-15', 'status': 'Aktif'},
            {'nomor': '3275012345678901', 'jenis': 'KTP', 'negara': 'Indonesia', 'terbit': '2019-06-01', 'habis': '2024-06-01', 'status': 'Kedaluwarsa'},
        ]
    }
    return render(request, 'identitas_member.html', context)

def kelola_member_view(request):
    # Data dummy member untuk di-loop di HTML
    context = {
        'member_list': [
            {
                'nomor': 'M0001', 'nama': 'Mr. John William Doe', 'email': 'john@example.com',
                'tier': 'Gold', 'tier_color': 'warning text-dark', 'total_miles': '45,000', 
                'award_miles': '32,000', 'bergabung': '2024-01-15'
            },
            {
                'nomor': 'M0002', 'nama': 'Mrs. Jane Smith', 'email': 'jane@example.com',
                'tier': 'Silver', 'tier_color': 'secondary', 'total_miles': '20,000', 
                'award_miles': '15,000', 'bergabung': '2024-03-10'
            },
            {
                'nomor': 'M0003', 'nama': 'Mr. Budi Anto Santoso', 'email': 'budi@example.com',
                'tier': 'Blue', 'tier_color': 'primary', 'total_miles': '5,000', 
                'award_miles': '3,500', 'bergabung': '2024-06-20'
            }
        ]
    }
    return render(request, 'kelola_member.html', context)