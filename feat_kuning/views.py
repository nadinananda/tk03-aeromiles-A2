from django.shortcuts import render, redirect
from django.db import connection
from datetime import date

def identitas_member_view(request):
    if 'email' not in request.session:
        return redirect('main:login')
    
    if request.session.get('role') != 'Member':
        return redirect('main:dashboard')

    email_user = request.session.get('email')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT nomor, jenis, negara_penerbit, tanggal_terbit, tanggal_habis
            FROM IDENTITAS WHERE email_member = %s
            ORDER BY tanggal_terbit DESC
        """, [email_user])
        identitas_list = cursor.fetchall()
    
    identitas_data = [
        {
            'nomor': i[0],
            'jenis': i[1],
            'negara': i[2],
            'terbit': i[3],
            'habis': i[4],
            'status': 'Aktif' if i[4] > date.today() else 'Kedaluwarsa'
        }
        for i in identitas_list
    ]
    
    context = {'identitas_list': identitas_data}
    return render(request, 'feat_kuning/identitas_member.html', context)

def kelola_member_view(request):
    if 'email' not in request.session:
        return redirect('main:login')
    
    if request.session.get('role') != 'Staf':
        return redirect('main:dashboard')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.nomor_member, p.salutation, p.first_mid_name, p.last_name, 
                   p.email, t.nama, m.total_miles, m.award_miles, m.tanggal_bergabung
            FROM MEMBER m
            JOIN PENGGUNA p ON m.email = p.email
            JOIN TIER t ON m.id_tier = t.id_tier
            ORDER BY m.tanggal_bergabung DESC
        """)
        members = cursor.fetchall()
    
    member_data = [
        {
            'nomor': m[0],
            'nama': f"{m[1]} {m[2]} {m[3]}",
            'email': m[4],
            'tier': m[5],
            'total_miles': f"{m[6]:,}",
            'award_miles': f"{m[7]:,}",
            'bergabung': m[8]
        }
        for m in members
    ]
    
    context = {'member_list': member_data}
    return render(request, 'kelola_member.html', context)