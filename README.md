# tk04-aeromiles-A2

# AeroMiles

## Prasyarat Sistem
Sebelum menjalankan aplikasi ini, pastikan sistem Anda telah terinstal:
* **Python** (Versi 3.10 atau lebih baru)
* **Git** (Opsional, untuk *version control*)
* Akses ke database Supabase kelompok (AeroMiles)

---

## Panduan Instalasi & Menjalankan Aplikasi

Ikuti langkah-langkah di bawah ini secara berurutan untuk menjalankan proyek di komputer lokal (localhost) yang terhubung ke database cloud Supabase kami.

### Langkah 1: Persiapan Skema Database (Opsional)
*Catatan: Langkah ini hanya perlu dilakukan jika database Supabase belum diinisialisasi atau perlu di-reset.*
1. Buka menu **SQL Editor** pada *dashboard* project Supabase AeroMiles yang sudah ada.
2. Buka file `TK03_DUMP_SQL_A_A2.sql` dari repositori ini, lalu *copy* dan *paste* seluruh isinya ke dalam SQL Editor Supabase.
3. Pastikan ekstensi `pgcrypto` diaktifkan untuk fungsi hashing dengan menyertakan baris ini di awal script:
   ```sql
   CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;
   SET search_path TO aeromiles, public, extensions;
4. Klik Run untuk mengeksekusi skema dan data dummy.

### Langkah 2: Setup Virtual Environment Python
1. Buat virtual environment baru:
```Bash
     python -m venv env
```
   
1. Aktivasi virtual environment:
  - Windows:
    ```Bash
      .\env\Scripts\activate
  - Mac/Linux:
    ```Bash
      source env/bin/activate

### Langkah 3: Install Dependencies
  ```Bash
    pip install -r requirements.txt
  ```

### Langkah 4: Konfigurasi Environment Variables (.env)
Buat file baru bernama .env di direktori utama proyek (sejajar dengan file manage.py), lalu copy-paste konfigurasi berikut. Sesuaikan DB_PASSWORD dengan password PostgreSQL di komputer Anda:

```.env 
# Konfigurasi Database Supabase (Session Pooler)
DB_NAME=postgres
DB_USER=postgres.jsyrvaxztetwlbfnwdjp
DB_PASSWORD=[MASUKKAN_PASSWORD_DISINI]
DB_HOST=aws-1-ap-northeast-2.pooler.supabase.com
DB_PORT=5432
```

### Langkah 5: Migrasi Database Django
Jalankan perintah migrasi untuk membuat tabel bawaan Django (seperti tabel session untuk sistem login):

```Bash
  python manage.py migrate
```
  
### Langkah 6: Jalankan Server Lokal
Mulai jalankan server aplikasi Django:

```Bash
  python manage.py runserver
```
  
### Langkah 7: Akses Aplikasi
Aplikasi berhasil dijalankan! Buka browser Anda dan kunjungi tautan berikut:
http://127.0.0.1:8000/
