from django.shortcuts import render, redirect
from django.db import IntegrityError
from django.contrib import messages
from . import services

def extract_db_error(e):
    return str(e).split('CONTEXT:')[0].strip()


def identitas_member_view(request):
    if 'email' not in request.session or request.session.get('role') != 'Member':
        messages.error(request, "U-umm... Kamu harus login sebagai Member dulu, baka!")
        return redirect('main:login')
    
    email_user = request.session.get('email')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        nomor = request.POST.get('nomor_dokumen')
        jenis = request.POST.get('jenis_dokumen')
        negara = request.POST.get('negara_penerbit')
        terbit = request.POST.get('tanggal_terbit')
        habis = request.POST.get('tanggal_habis')
        nomor_lama = request.POST.get('nomor_lama')
        
        try:
            if action == 'tambah':
                services.tambah_identitas(nomor, email_user, jenis, negara, terbit, habis)
                messages.success(request, "Data identitas berhasil ditambahkan!")
            
            elif action == 'edit':
                services.edit_identitas(nomor, jenis, negara, terbit, habis, nomor_lama, email_user)
                messages.success(request, "Data identitas berhasil diperbarui!")

            elif action == 'hapus':
                services.hapus_identitas(nomor_lama, email_user)
                messages.success(request, "Data identitas berhasil dihapus!")
        
        except IntegrityError:
            messages.error(request, "Nomor dokumen tersebut sudah terdaftar!")
        except Exception as e:
            messages.error(request, f"Duh, gagal memproses data: {extract_db_error(e)}")
            
        return redirect('kuning:identitas_member')

    identitas_data = services.get_identitas_member(email_user)
    context = {'identitas_list': identitas_data}
    return render(request, 'identitas_member.html', context)


def kelola_member_view(request):
    if 'email' not in request.session or request.session.get('role') != 'Staf':
        messages.error(request, "Akses ditolak! Cuma Staf yang boleh ke sini!")
        return redirect('main:login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'tambah':
                services.tambah_member(
                    email=request.POST.get('email'),
                    password=request.POST.get('password'),
                    salutation=request.POST.get('salutation'),
                    nama_depan=request.POST.get('first_mid_name'),
                    nama_belakang=request.POST.get('last_name'),
                    country_code=request.POST.get('country_code'),
                    nomor_hp=request.POST.get('mobile_number'),
                    tanggal_lahir=request.POST.get('tanggal_lahir'),
                    kewarganegaraan=request.POST.get('kewarganegaraan')
                )
                messages.success(request, "Member baru berhasil ditambahkan!")

            elif action == 'edit':
                services.edit_member(
                    email=request.POST.get('email'),
                    salutation=request.POST.get('salutation'),
                    nama_depan=request.POST.get('first_mid_name'),
                    nama_belakang=request.POST.get('last_name'),
                    kewarganegaraan=request.POST.get('kewarganegaraan'),
                    country_code=request.POST.get('country_code'),
                    nomor_hp=request.POST.get('mobile_number'),
                    tanggal_lahir=request.POST.get('tanggal_lahir'),
                    tier=request.POST.get('tier')
                )
                messages.success(request, "Data Member berhasil diperbarui!")

            elif action == 'hapus':
                services.hapus_member(request.POST.get('email'))
                messages.success(request, "Member berhasil dihapus secara permanen!")

        except Exception as e:
            messages.error(request, f"Duh, error: {extract_db_error(e)}")

        return redirect('kuning:kelola_member')

    search_query = request.GET.get('search', '').strip()
    tier_filter = request.GET.get('tier', 'Semua Tier')

    member_data = services.get_semua_member_filtered(search_query, tier_filter)
    
    context = {
        'member_list': member_data,
        'search_query': search_query,
        'tier_filter': tier_filter,
        'negara_list': ['Indonesia', 'Malaysia', 'Singapura', 'Thailand', 'Jepang', 'Korea Selatan', 'Amerika Serikat', 'Inggris'],
        'kode_negara_list': ['+62', '+60', '+65', '+66', '+81', '+82', '+1', '+44'],
    }
    
    return render(request, 'kelola_member.html', context)