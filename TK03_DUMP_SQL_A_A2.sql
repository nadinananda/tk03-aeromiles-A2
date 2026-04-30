DROP SCHEMA IF EXISTS aeromiles CASCADE;
CREATE SCHEMA aeromiles;
SET search_path TO aeromiles;

--- Buat Tabel Umum
CREATE TABLE TIER (
    id_tier VARCHAR(10) PRIMARY KEY,
    nama VARCHAR(50) NOT NULL,
    minimal_frekuensi_terbang INT NOT NULL,
    minimal_tier_miles INT NOT NULL
);

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

CREATE TABLE MEMBER (
    email VARCHAR(100) PRIMARY KEY REFERENCES PENGGUNA(email) ON DELETE CASCADE,
    nomor_member VARCHAR(20) NOT NULL UNIQUE,
    tanggal_bergabung DATE NOT NULL,
    id_tier VARCHAR(10) NOT NULL REFERENCES TIER(id_tier),
    award_miles INT DEFAULT 0,
    total_miles INT DEFAULT 0
);

CREATE TABLE STAF (
    email VARCHAR(100) PRIMARY KEY REFERENCES PENGGUNA(email) ON DELETE CASCADE,
    nomor_staf VARCHAR(20) NOT NULL UNIQUE
);

--- Buat Feature Warna Merah NO. 15 - 16
CREATE TABLE PENYEDIA (
    id SERIAL PRIMARY KEY
);

CREATE TABLE MITRA (
    email_mitra VARCHAR(100) PRIMARY KEY,
    id_penyedia INT NOT NULL UNIQUE REFERENCES PENYEDIA(id) ON DELETE CASCADE,
    nama_mitra VARCHAR(100) NOT NULL,
    tanggal_kerja_sama DATE NOT NULL
);

CREATE SEQUENCE hadiah_kode_seq START 1;

CREATE TABLE HADIAH (
    kode_hadiah VARCHAR(20) PRIMARY KEY DEFAULT ('RWD-' || LPAD(nextval('hadiah_kode_seq')::TEXT, 3, '0')),
    nama VARCHAR(100) NOT NULL,
    miles INT NOT NULL CHECK (miles > 0),
    deskripsi TEXT NOT NULL,
    valid_start_date DATE NOT NULL,
    program_end DATE NOT NULL,
    id_penyedia INT NOT NULL REFERENCES PENYEDIA(id) ON DELETE CASCADE,
    CHECK (program_end >= valid_start_date)
);

--- Buat Feature Warna Biru NO. 11 - 14
CREATE TABLE REDEEM (
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    kode_hadiah VARCHAR(20) NOT NULL REFERENCES HADIAH(kode_hadiah),
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (email_member, kode_hadiah, timestamp)
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

--- Buat Feature Warna Kuning
CREATE TABLE IDENTITAS (
    nomor VARCHAR(50) PRIMARY KEY,
    email_member VARCHAR(100) NOT NULL REFERENCES MEMBER(email) ON DELETE CASCADE,
    tanggal_habis DATE NOT NULL,
    tanggal_terbit DATE NOT NULL,
    negara_penerbit VARCHAR(50) NOT NULL,
    jenis VARCHAR(30) NOT NULL CHECK (jenis IN ('Paspor', 'KTP', 'SIM'))
);

--- Insert Data Dummy Tabel Umum
INSERT INTO TIER (id_tier, nama, minimal_frekuensi_terbang, minimal_tier_miles)
VALUES
    ('T001', 'Bronze', 0, 0),
    ('T002', 'Silver', 5, 10000),
    ('T003', 'Gold', 10, 30000),
    ('T004', 'Platinum', 20, 70000);

INSERT INTO PENGGUNA (
    email, password, salutation, first_mid_name, last_name, country_code,
    mobile_number, tanggal_lahir, kewarganegaraan
)
SELECT
    'member' || LPAD(n::TEXT, 2, '0') || '@aeromiles.com',
    '12345',
    CASE WHEN n % 3 = 0 THEN 'Ms.' WHEN n % 3 = 1 THEN 'Mr.' ELSE 'Mrs.' END,
    'Member',
    LPAD(n::TEXT, 2, '0'),
    '+62',
    '08120000' || LPAD(n::TEXT, 2, '0'),
    DATE '1995-01-01' + n,
    'Indonesia'
FROM generate_series(1, 50) AS n;

INSERT INTO MEMBER (
    email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles
)
SELECT
    'member' || LPAD(n::TEXT, 2, '0') || '@aeromiles.com',
    'M' || LPAD(n::TEXT, 4, '0'),
    DATE '2024-01-01' + n,
    CASE
        WHEN n <= 15 THEN 'T001'
        WHEN n <= 30 THEN 'T002'
        WHEN n <= 42 THEN 'T003'
        ELSE 'T004'
    END,
    10000 + (n * 750),
    15000 + (n * 1000)
FROM generate_series(1, 50) AS n;

INSERT INTO PENGGUNA (
    email, password, salutation, first_mid_name, last_name, country_code,
    mobile_number, tanggal_lahir, kewarganegaraan
)
SELECT
    'staf' || LPAD(n::TEXT, 2, '0') || '@aeromiles.com',
    '12345',
    'Mr.',
    'Staf',
    LPAD(n::TEXT, 2, '0'),
    '+62',
    '08220000' || LPAD(n::TEXT, 2, '0'),
    DATE '1990-01-01' + n,
    'Indonesia'
FROM generate_series(1, 10) AS n;

INSERT INTO STAF (email, nomor_staf)
SELECT
    'staf' || LPAD(n::TEXT, 2, '0') || '@aeromiles.com',
    'S' || LPAD(n::TEXT, 4, '0')
FROM generate_series(1, 10) AS n;

INSERT INTO PENGGUNA (
    email, password, salutation, first_mid_name, last_name, country_code,
    mobile_number, tanggal_lahir, kewarganegaraan
)
VALUES
    ('member@aeromiles.com', '12345', 'Mr.', 'Akun', 'Member', '+62', '0811111111', '2000-01-01', 'Indonesia'),
    ('staf@aeromiles.com', '12345', 'Mr.', 'Akun', 'Staf', '+62', '0822222222', '1990-01-01', 'Indonesia');

INSERT INTO MEMBER (email, nomor_member, tanggal_bergabung, id_tier, award_miles, total_miles)
VALUES ('member@aeromiles.com', 'M9999', '2024-01-01', 'T003', 32000, 45000);

INSERT INTO STAF (email, nomor_staf)
VALUES ('staf@aeromiles.com', 'S9999');

INSERT INTO PENYEDIA (id)
VALUES
    (1),
    (2),
    (3),
    (4),
    (5),
    (6),
    (7),
    (8);

SELECT setval('penyedia_id_seq', (SELECT MAX(id) FROM PENYEDIA));

INSERT INTO MITRA (email_mitra, id_penyedia, nama_mitra, tanggal_kerja_sama)
VALUES
    ('partner@traveloka.com', 4, 'TravelokaPartner', '2023-01-15'),
    ('partner@plazapremium.com', 5, 'Plaza Premium', '2023-06-01'),
    ('partner@blueskyhotel.com', 6, 'BlueSky Hotel', '2024-03-12'),
    ('partner@aeroshop.com', 7, 'AeroShop', '2024-07-20'),
    ('partner@skymeal.com', 8, 'SkyMeal Indonesia', '2025-02-05');

INSERT INTO AWARD_MILES_PACKAGE (id, harga_paket, jumlah_award_miles) VALUES
('AMP-001', 500000.00, 1000),
('AMP-002', 900000.00, 2000),
('AMP-003', 2000000.00, 5000),
('AMP-004', 3800000.00, 10000),
('AMP-005', 7000000.00, 20000);

INSERT INTO HADIAH (
    kode_hadiah, nama, miles, deskripsi, valid_start_date, program_end, id_penyedia
)
VALUES
    ('RWD-001', 'Tiket Domestik PP', 15000, 'Tiket pulang-pergi rute domestik Indonesia.', '2026-01-01', '2026-12-31', 1),
    ('RWD-002', 'Upgrade ke Business Class', 25000, 'Upgrade dari economy class ke business class.', '2026-01-01', '2027-01-01', 1),
    ('RWD-003', 'Voucher Hotel Rp 500.000', 8000, 'Voucher hotel jaringan mitra AeroMiles.', '2026-02-01', '2026-09-30', 4),
    ('RWD-004', 'Akses Lounge 1x', 3000, 'Akses lounge sebelum keberangkatan untuk satu orang.', '2024-01-01', '2025-12-31', 5),
    ('RWD-005', 'Extra Baggage 10kg', 6000, 'Tambahan bagasi 10kg untuk penerbangan domestik.', '2026-03-01', '2026-11-30', 1),
    ('RWD-006', 'Voucher Makan Bandara', 2500, 'Voucher makan di restoran bandara mitra AeroMiles.', '2026-01-15', '2026-08-31', 8),
    ('RWD-007', 'Hotel Airport Transit', 12000, 'Voucher menginap satu malam di hotel transit bandara.', '2026-04-01', '2026-12-31', 6),
    ('RWD-008', 'Merchandise AeroMiles', 4500, 'Paket merchandise eksklusif AeroMiles.', '2026-01-01', '2026-10-31', 7),
    ('RWD-009', 'Prioritas Boarding', 3500, 'Akses prioritas boarding untuk satu penerbangan.', '2026-02-01', '2026-12-31', 2),
    ('RWD-010', 'Voucher Hotel Rp 1.000.000', 15000, 'Voucher hotel premium untuk jaringan mitra.', '2026-05-01', '2027-05-01', 4);

SELECT setval(
    'hadiah_kode_seq',
    GREATEST(
        COALESCE((SELECT MAX(SUBSTRING(kode_hadiah FROM 5)::INT) FROM HADIAH), 0),
        10
    ),
    TRUE
);

--- Insert Data Dummy Tabel REDEEM (Feature Merah)
INSERT INTO REDEEM (email_member, kode_hadiah, timestamp)
VALUES
    ('member01@aeromiles.com', 'RWD-001', '2026-02-01 10:30:00'),
    ('member02@aeromiles.com', 'RWD-002', '2026-02-05 14:15:00'),
    ('member03@aeromiles.com', 'RWD-003', '2026-02-08 09:45:00'),
    ('member04@aeromiles.com', 'RWD-004', '2026-02-10 16:20:00'),
    ('member05@aeromiles.com', 'RWD-005', '2026-02-12 11:00:00'),
    ('member06@aeromiles.com', 'RWD-006', '2026-02-15 13:30:00'),
    ('member07@aeromiles.com', 'RWD-007', '2026-02-18 10:15:00'),
    ('member08@aeromiles.com', 'RWD-008', '2026-02-20 15:45:00'),
    ('member09@aeromiles.com', 'RWD-009', '2026-02-22 08:50:00'),
    ('member10@aeromiles.com', 'RWD-010', '2026-02-25 12:30:00'),
    ('member11@aeromiles.com', 'RWD-001', '2026-03-01 10:00:00'),
    ('member12@aeromiles.com', 'RWD-003', '2026-03-03 14:30:00'),
    ('member13@aeromiles.com', 'RWD-005', '2026-03-05 09:15:00'),
    ('member14@aeromiles.com', 'RWD-007', '2026-03-07 11:45:00'),
    ('member15@aeromiles.com', 'RWD-009', '2026-03-10 13:20:00'),
    ('member@aeromiles.com', 'RWD-002', '2026-03-12 10:30:00'),
    ('member16@aeromiles.com', 'RWD-004', '2026-03-14 15:00:00'),
    ('member17@aeromiles.com', 'RWD-006', '2026-03-16 12:15:00'),
    ('member18@aeromiles.com', 'RWD-008', '2026-03-18 14:45:00'),
    ('member19@aeromiles.com', 'RWD-010', '2026-03-20 09:30:00');

--- Insert Data Dummy Tabel Kuning
INSERT INTO IDENTITAS (nomor, email_member, tanggal_habis, tanggal_terbit, negara_penerbit, jenis)
SELECT
    'IDN' || LPAD(x::varchar, 8, '0'), 'member' || LPAD(x::varchar, 2, '0') || '@aeromiles.com',
    '2030-01-01'::date, '2020-01-01'::date, 'Indonesia',
    CASE x % 3 WHEN 0 THEN 'Paspor' WHEN 1 THEN 'KTP' ELSE 'SIM' END
FROM generate_series(1, 30) as x;
