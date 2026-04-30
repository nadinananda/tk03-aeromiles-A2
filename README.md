# tk03-aeromiles-A2

# AeroMiles

## Prasyarat Sistem
Sebelum menjalankan aplikasi ini, pastikan sistem Anda telah terinstal:
* **Python** (Versi 3.10 atau lebih baru)
* **PostgreSQL** (Versi 14 atau lebih baru)
* **Git** (Opsional, untuk *version control*)

---

## Panduan Instalasi & Menjalankan Aplikasi

Ikuti langkah-langkah di bawah ini secara berurutan untuk menjalankan proyek di komputer lokal (localhost).

### Langkah 1: Persiapan Database PostgreSQL
1. Buka terminal psql atau pgAdmin.
2. Buat database baru bernama `aeromiles`:
   ```sql
   CREATE DATABASE aeromiles;

3. Hubungkan/masuk ke dalam database aeromiles
4. Eksekusi file dump SQL yang telah disediakan untuk membuat skema dan data dummy:
    -   Buka file TK03_DUMP_SQL_A_A2.sql dan jalankan seluruh isinya di dalam database aeromiles.
    - Catatan Penting: Pastikan extension pgcrypto sudah terinstal di database tersebut agar fungsi hashing password dapat berjalan. Jika belum, jalankan perintah ini:
  
      CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
# Konfigurasi Database PostgreSQL
DB_NAME=aeromiles
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
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
