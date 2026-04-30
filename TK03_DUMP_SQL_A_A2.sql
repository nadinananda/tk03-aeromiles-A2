-- ==============================================================================
-- 1. SCHEMA INITIALIZATION
-- ==============================================================================
DROP SCHEMA IF EXISTS aeromiles CASCADE;
CREATE SCHEMA aeromiles;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SET search_path TO aeromiles,public;

-- ==============================================================================
-- 2. DDL (DATA DEFINITION LANGUAGE) - CREATE TABLES
-- ==============================================================================

CREATE TABLE PENGGUNA (
    email VARCHAR(100) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    salutation VARCHAR(10) NOT NULL CHECK (salutation IN ('Mr.', 'Mrs.', 'Ms.', 'Dr.')),
    first_mid_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(5) NOT NULL,
    mobile_number VARCHAR(20) NOT NULL,
    tanggal_lahir DATE NOT NULL,
    kewarganegaraan VARCHAR(50) NOT NULL
);

CREATE TABLE TIER (
    id_tier VARCHAR(10) PRIMARY KEY,
    nama VARCHAR(50) NOT NULL,
    minimal_frekuensi_terbang INT NOT NULL,
    minimal_tier_miles INT NOT NULL
);

CREATE SEQUENCE seq_nomor_member START 1;

CREATE TABLE MEMBER (
    email VARCHAR(100) PRIMARY KEY REFERENCES PENGGUNA(email) ON DELETE CASCADE,
    nomor_member VARCHAR(20) NOT NULL UNIQUE,
    tanggal_bergabung DATE NOT NULL,
    id_tier VARCHAR(10) NOT NULL REFERENCES TIER(id_tier),
    award_miles INT DEFAULT 0,
    total_miles INT DEFAULT 0
);

CREATE TABLE PENYEDIA (
    id SERIAL PRIMARY KEY
);

CREATE TABLE MASKAPAI (
    kode_maskapai VARCHAR(10) PRIMARY KEY,
    nama_maskapai VARCHAR(100) NOT NULL,
    id_penyedia INT NOT NULL REFERENCES PENYEDIA(id)
);

CREATE TABLE STAF (
    email VARCHAR(100) PRIMARY KEY REFERENCES PENGGUNA(email) ON DELETE CASCADE,
    id_staf VARCHAR(20) NOT NULL UNIQUE,
    kode_maskapai VARCHAR(10) NOT NULL REFERENCES MASKAPAI(kode_maskapai)
);

CREATE TABLE MITRA (
    email_mitra VARCHAR(100) PRIMARY KEY,
    id_penyedia INT NOT NULL UNIQUE REFERENCES PENYEDIA(id) ON DELETE CASCADE,
    nama_mitra VARCHAR(100) NOT NULL,
    tanggal_kerja_sama DATE NOT NULL
);

CREATE TABLE IDENTITAS (
    nomor VARCHAR(50) PRIMARY KEY,
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    tanggal_habis DATE NOT NULL,
    tanggal_terbit DATE NOT NULL,
    negara_penerbit VARCHAR(50) NOT NULL,
    jenis VARCHAR(30) NOT NULL CHECK (jenis IN ('Paspor', 'KTP', 'SIM'))
);

CREATE TABLE AWARD_MILES_PACKAGE (
    id VARCHAR(20) PRIMARY KEY,
    harga_paket DECIMAL(15,2) NOT NULL,
    jumlah_award_miles INT NOT NULL
);

CREATE TABLE MEMBER_AWARD_MILES_PACKAGE (
    id_award_miles_package VARCHAR(20) NOT NULL REFERENCES AWARD_MILES_PACKAGE(id),
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (id_award_miles_package, email_member, timestamp)
);

CREATE TABLE BANDARA (
    iata_code CHAR(3) PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    kota VARCHAR(100) NOT NULL,
    negara VARCHAR(100) NOT NULL
);

CREATE TABLE CLAIM_MISSING_MILES (
    id SERIAL PRIMARY KEY,
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    email_staf VARCHAR(100) REFERENCES STAF(email), -- Boleh null saat status 'Menunggu'
    maskapai VARCHAR(10) NOT NULL REFERENCES MASKAPAI(kode_maskapai),
    bandara_asal CHAR(3) NOT NULL REFERENCES BANDARA(iata_code),
    bandara_tujuan CHAR(3) NOT NULL REFERENCES BANDARA(iata_code),
    tanggal_penerbangan DATE NOT NULL,
    flight_number VARCHAR(10) NOT NULL,
    nomor_tiket VARCHAR(20) NOT NULL,
    kelas_kabin VARCHAR(20) NOT NULL CHECK (kelas_kabin IN ('Economy', 'Business', 'First')),
    pnr VARCHAR(10) NOT NULL,
    status_penerimaan VARCHAR(20) NOT NULL CHECK (status_penerimaan IN ('Menunggu', 'Disetujui', 'Ditolak')),
    timestamp TIMESTAMP NOT NULL,
    CONSTRAINT unique_claim_aturan UNIQUE (email_member, flight_number, tanggal_penerbangan, nomor_tiket)
);

CREATE TABLE TRANSFER (
    email_member_1 VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    email_member_2 VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    jumlah INT NOT NULL,
    catatan VARCHAR(255),
    PRIMARY KEY (email_member_1, email_member_2, timestamp),
    CONSTRAINT check_self_transfer CHECK (email_member_1 != email_member_2)
);

CREATE TABLE HADIAH (
    kode_hadiah VARCHAR(20) PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    miles INT NOT NULL,
    deskripsi TEXT,
    valid_start_date DATE NOT NULL,
    program_end DATE NOT NULL,
    id_penyedia INT NOT NULL REFERENCES PENYEDIA(id) ON DELETE CASCADE
);

CREATE TABLE REDEEM (
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    kode_hadiah VARCHAR(20) NOT NULL REFERENCES HADIAH(kode_hadiah),
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (email_member, kode_hadiah, timestamp)
);


-- ==============================================================================
-- 3. DML (DATA MANIPULATION LANGUAGE) - DUMMY DATA INSERTS
-- ==============================================================================

-- TIER (4 Data)
INSERT INTO TIER (id_tier, nama, minimal_frekuensi_terbang, minimal_tier_miles) VALUES
('T-BLUE', 'Blue', 0, 0),
('T-SLVR', 'Silver', 10, 10000),
('T-GOLD', 'Gold', 30, 30000),
('T-PLAT', 'Platinum', 60, 60000);

-- PENGGUNA (60 Data: 50 Member + 10 Staf) menggunakan generate_series, hash password '12345' dengan bcrypt
INSERT INTO PENGGUNA (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
SELECT 
    'member' || x || '@aeromiles.com', 
    crypt('12345', gen_salt('bf')),
    CASE WHEN x % 2 = 0 THEN 'Mr.' ELSE 'Ms.' END, 'Akun', 'Member ' || x, '+62', 
    '08110000' || LPAD(x::varchar, 3, '0'), '1990-01-01'::date + (x || ' days')::interval, 'Indonesia'
FROM generate_series(1, 50) as x;

INSERT INTO PENGGUNA (email, password, salutation, first_mid_name, last_name, country_code, mobile_number, tanggal_lahir, kewarganegaraan)
SELECT 
    'staf' || x || '@aeromiles.com', 
    crypt('12345', gen_salt('bf')), 
    'Mr.', 'Akun', 'Staf ' || x, '+62', 
    '08220000' || LPAD(x::varchar, 3, '0'), '1985-05-15'::date + (x || ' days')::interval, 'Indonesia'
FROM generate_series(1, 10) as x;

-- MEMBER (50 Data)
INSERT INTO MEMBER (email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles)
SELECT 
    'member' || x || '@aeromiles.com', 'M' || LPAD(x::varchar, 4, '0'), 
    '2024-01-01'::date + (x || ' days')::interval, 
    CASE x % 4 WHEN 0 THEN 'T-BLUE' WHEN 1 THEN 'T-SLVR' WHEN 2 THEN 'T-GOLD' ELSE 'T-PLAT' END,
    x * 1000, x * 1500
FROM generate_series(1, 50) as x;

-- PENYEDIA (8 Data)
INSERT INTO PENYEDIA (id) VALUES (1),(2),(3),(4),(5),(6),(7),(8);

-- MASKAPAI (5 Data) memakai id_penyedia 1, 2, 3
INSERT INTO MASKAPAI (kode_maskapai, nama_maskapai, id_penyedia) VALUES
('GA', 'Garuda Indonesia', 1),
('SQ', 'Singapore Airlines', 2),
('QZ', 'AirAsia', 3),
('JT', 'Lion Air', 1),
('CX', 'Cathay Pacific', 2);

-- STAF (10 Data)
INSERT INTO STAF (email, id_staf, kode_maskapai)
SELECT 
    'staf' || x || '@aeromiles.com', 'S' || LPAD(x::varchar, 4, '0'),
    CASE x % 5 WHEN 0 THEN 'GA' WHEN 1 THEN 'SQ' WHEN 2 THEN 'QZ' WHEN 3 THEN 'JT' ELSE 'CX' END
FROM generate_series(1, 10) as x;

-- MITRA (5 Data) memakai id_penyedia 4, 5, 6, 7, 8 (Harus UNIQUE)
INSERT INTO MITRA (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama) VALUES
('mitra1@bank.com', 4, 'Bank Mandiri', '2023-01-01'),
('mitra2@hotel.com', 5, 'Hyatt Hotel', '2023-02-01'),
('mitra3@rental.com', 6, 'Avis Rental', '2023-03-01'),
('mitra4@resto.com', 7, 'Bistecca', '2023-04-01'),
('mitra5@shop.com', 8, 'Plaza Senayan', '2023-05-01');

-- IDENTITAS (30 Data)
INSERT INTO IDENTITAS (nomor, email_member, tanggal_habis, tanggal_terbit, negara_penerbit, jenis)
SELECT 
    'IDN' || LPAD(x::varchar, 8, '0'), 'member' || x || '@aeromiles.com',
    '2030-01-01'::date, '2020-01-01'::date, 'Indonesia',
    CASE x % 3 WHEN 0 THEN 'Paspor' WHEN 1 THEN 'KTP' ELSE 'SIM' END
FROM generate_series(1, 30) as x;

-- AWARD_MILES_PACKAGE (5 Data)
INSERT INTO AWARD_MILES_PACKAGE (id, harga_paket, jumlah_award_miles) VALUES
('AMP-001', 500000.00, 1000),
('AMP-002', 900000.00, 2000),
('AMP-003', 2000000.00, 5000),
('AMP-004', 3800000.00, 10000),
('AMP-005', 7000000.00, 20000);

-- MEMBER_AWARD_MILES_PACKAGE (20 Data)
INSERT INTO MEMBER_AWARD_MILES_PACKAGE (id_award_miles_package, email_member, timestamp)
SELECT 
    'AMP-00' || ((x % 5) + 1)::varchar, 'member' || x || '@aeromiles.com',
    NOW() - (x || ' days')::interval
FROM generate_series(1, 20) as x;

-- BANDARA (15 Data)
INSERT INTO BANDARA (iata_code, nama, kota, negara) VALUES
('CGK', 'Soekarno-Hatta', 'Jakarta', 'Indonesia'), ('DPS', 'Ngurah Rai', 'Bali', 'Indonesia'),
('SUB', 'Juanda', 'Surabaya', 'Indonesia'), ('KNO', 'Kualanamu', 'Medan', 'Indonesia'),
('YIA', 'Yogyakarta Intl', 'Yogyakarta', 'Indonesia'), ('SIN', 'Changi', 'Singapore', 'Singapore'),
('KUL', 'Kuala Lumpur', 'Kuala Lumpur', 'Malaysia'), ('BKK', 'Suvarnabhumi', 'Bangkok', 'Thailand'),
('NRT', 'Narita', 'Tokyo', 'Japan'), ('HND', 'Haneda', 'Tokyo', 'Japan'),
('ICN', 'Incheon', 'Seoul', 'South Korea'), ('SYD', 'Kingsford Smith', 'Sydney', 'Australia'),
('MEL', 'Melbourne', 'Melbourne', 'Australia'), ('LHR', 'Heathrow', 'London', 'UK'),
('JFK', 'John F. Kennedy', 'New York', 'USA');

-- CLAIM_MISSING_MILES (20 Data)
INSERT INTO CLAIM_MISSING_MILES (email_member, email_staf, maskapai, bandara_asal, bandara_tujuan, tanggal_penerbangan, flight_number, nomor_tiket, kelas_kabin, pnr, status_penerimaan, timestamp)
SELECT 
    'member' || x || '@aeromiles.com',
    CASE WHEN x % 2 = 0 THEN 'staf' || ((x % 10)+1) || '@aeromiles.com' ELSE NULL END, 
    CASE x % 5 WHEN 0 THEN 'GA' WHEN 1 THEN 'SQ' WHEN 2 THEN 'QZ' WHEN 3 THEN 'JT' ELSE 'CX' END,
    'CGK', 'DPS', '2024-02-01'::date + (x || ' days')::interval,
    'FL' || LPAD(x::varchar, 3, '0'), 'TKT' || LPAD(x::varchar, 6, '0'),
    CASE x % 3 WHEN 0 THEN 'Economy' WHEN 1 THEN 'Business' ELSE 'First' END,
    'PNR' || LPAD(x::varchar, 3, '0'),
    CASE WHEN x % 2 != 0 THEN 'Menunggu' WHEN x % 4 = 0 THEN 'Disetujui' ELSE 'Ditolak' END,
    NOW() - (x || ' days')::interval
FROM generate_series(1, 20) as x;

-- TRANSFER (15 Data)
INSERT INTO TRANSFER (email_member_1, email_member_2, timestamp, jumlah, catatan)
SELECT 
    'member' || x || '@aeromiles.com', 'member' || (x + 1) || '@aeromiles.com',
    NOW() - (x || ' hours')::interval, x * 100, 'Transfer miles'
FROM generate_series(1, 15) as x;

-- HADIAH (10 Data)
INSERT INTO HADIAH (kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia)
SELECT 
    'RWD-' || LPAD(x::varchar, 3, '0'), 'Voucher Diskon ' || (x * 10) || '%', x * 500,
    'Voucher berlaku di merchant terpilih', '2024-01-01'::date, '2025-12-31'::date,
    CASE WHEN x % 2 = 0 THEN 4 ELSE 5 END
FROM generate_series(1, 10) as x;

-- REDEEM (20 Data)
INSERT INTO REDEEM (email_member, kode_hadiah, timestamp)
SELECT 
    'member' || x || '@aeromiles.com', 'RWD-' || LPAD(((x % 10) + 1)::varchar, 3, '0'),
    NOW() - (x || ' minutes')::interval
FROM generate_series(1, 20) as x;
