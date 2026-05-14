from django.db import connection
from datetime import date

def tambah_identitas(nomor, email_user, jenis, negara, terbit, habis):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO IDENTITAS (nomor, email_member, jenis, negara_penerbit, tanggal_terbit, tanggal_habis)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [nomor, email_user, jenis, negara, terbit, habis])

def edit_identitas(nomor, jenis, negara, terbit, habis, nomor_lama, email_user):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE IDENTITAS 
            SET nomor=%s, jenis=%s, negara_penerbit=%s, tanggal_terbit=%s, tanggal_habis=%s
            WHERE nomor=%s AND email_member=%s
        """, [nomor, jenis, negara, terbit, habis, nomor_lama, email_user])

def hapus_identitas(nomor_lama, email_user):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM IDENTITAS WHERE nomor=%s AND email_member=%s", [nomor_lama, email_user])

def get_identitas_member(email_user):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT nomor, jenis, negara_penerbit, tanggal_terbit, tanggal_habis
            FROM IDENTITAS WHERE email_member = %s
            ORDER BY tanggal_terbit DESC
        """, [email_user])
        identitas_list = cursor.fetchall()
    
    return [
        {
            'nomor': i[0],
            'jenis': i[1],
            'negara': i[2],
            'terbit': str(i[3]),
            'habis': str(i[4]),
            'status': 'Aktif' if i[4] > date.today() else 'Kedaluwarsa'
        }
        for i in identitas_list
    ]

def tambah_member(email, password, salutation, nama_depan, nama_belakang, country_code, nomor_hp, tanggal_lahir, kewarganegaraan):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO PENGGUNA (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
            VALUES (%s, extensions.crypt(%s, extensions.gen_salt('bf')), %s, %s, %s, %s, %s, %s, %s)
        """, [email, password, salutation, nama_depan, nama_belakang, country_code, nomor_hp, tanggal_lahir, kewarganegaraan])

        cursor.execute("SELECT nomor_member FROM MEMBER")
        semua_member = cursor.fetchall()
        max_num = 0
        for m in semua_member:
            angka_saja = ''.join(filter(str.isdigit, m[0]))
            if angka_saja:
                max_num = max(max_num, int(angka_saja))
        
        nomor_member = f"M{max_num + 1:04d}"
        
        cursor.execute("""
            INSERT INTO MEMBER (email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles)
            VALUES (%s, %s, CURRENT_DATE, 'T-BLUE', 0, 0)
        """, [email, nomor_member])

def edit_member(email, salutation, nama_depan, nama_belakang, kewarganegaraan, country_code, nomor_hp, tanggal_lahir, tier):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE PENGGUNA 
            SET salutation=%s, first_mid_name=%s, last_name=%s, country_code=%s, mobile_number=%s, kewarganegaraan=%s, tanggal_lahir=%s
            WHERE email=%s
        """, [salutation, nama_depan, nama_belakang, country_code, nomor_hp, kewarganegaraan, tanggal_lahir, email])

        cursor.execute("UPDATE MEMBER SET id_tier=%s WHERE email=%s", [tier, email])

def hapus_member(email):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM PENGGUNA WHERE email=%s", [email])

def get_semua_member_filtered(search_query, tier_filter):
    with connection.cursor() as cursor:
        query = """
            SELECT m.nomor_member, p.salutation, p.first_mid_name, p.last_name, 
                   p.email, t.nama, m.total_miles, m.award_miles, m.tanggal_bergabung, t.id_tier,
                   p.kewarganegaraan, p.country_code, p.mobile_number, p.tanggal_lahir
            FROM MEMBER m
            JOIN PENGGUNA p ON m.email = p.email
            JOIN TIER t ON m.id_tier = t.id_tier
            WHERE 1=1
        """
        params = []
        
        if search_query:
            query += " AND (m.nomor_member ILIKE %s OR p.email ILIKE %s OR (p.first_mid_name || ' ' || p.last_name) ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
            
        if tier_filter != 'Semua Tier':
            query += " AND t.nama = %s"
            params.append(tier_filter)

        query += " ORDER BY m.tanggal_bergabung DESC"
        cursor.execute(query, params)
        members = cursor.fetchall()
    
    return [
        {
            'nomor': m[0],
            'salutation': m[1],
            'first_mid_name': m[2],
            'last_name': m[3],
            'nama': f"{m[1]} {m[2]} {m[3]}",
            'email': m[4],
            'tier': m[5],
            'id_tier': m[9], 
            'tier_color': 'primary' if m[5] == 'Blue' else 'secondary' if m[5] == 'Silver' else 'warning' if m[5] == 'Gold' else 'dark',
            'total_miles': f"{m[6]:,}",
            'award_miles': f"{m[7]:,}",
            'bergabung': str(m[8]),
            'kewarganegaraan': m[10],
            'country_code': m[11],
            'mobile_number': m[12],
            'tanggal_lahir': str(m[13])
        }
        for m in members
    ]