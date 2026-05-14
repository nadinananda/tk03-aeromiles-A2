SET search_path TO aeromiles, public, extensions;

-- ============================================================================
-- Backend fitur hijau:
-- 8. CRUD Manajemen Claim Missing Miles Member
-- 9. RU Manajemen Claim Missing Miles Staf
-- 10. CR Transfer Miles antar Member
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Helper untuk menghitung miles klaim berdasarkan rute dan kelas kabin.
-- Rute domestik diberi base 1000 miles, rute internasional base 2500 miles.
-- Kelas Economy = 1x, Premium Economy = 1.5x, Business = 2x, First = 3x.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_hitung_missing_miles(
    p_bandara_asal CHAR(3),
    p_bandara_tujuan CHAR(3),
    p_kelas_kabin VARCHAR
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_negara_asal VARCHAR(100);
    v_negara_tujuan VARCHAR(100);
    v_base_miles INT;
    v_multiplier NUMERIC;
BEGIN
    IF p_bandara_asal = p_bandara_tujuan THEN
        RAISE EXCEPTION 'Bandara asal dan tujuan tidak boleh sama.';
    END IF;

    SELECT negara INTO v_negara_asal
    FROM bandara
    WHERE iata_code = p_bandara_asal;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Bandara asal % tidak ditemukan.', p_bandara_asal;
    END IF;

    SELECT negara INTO v_negara_tujuan
    FROM bandara
    WHERE iata_code = p_bandara_tujuan;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Bandara tujuan % tidak ditemukan.', p_bandara_tujuan;
    END IF;

    v_base_miles := CASE
        WHEN v_negara_asal = v_negara_tujuan THEN 1000
        ELSE 2500
    END;

    v_multiplier := CASE p_kelas_kabin
        WHEN 'Economy' THEN 1
        WHEN 'Premium Economy' THEN 1.5
        WHEN 'Business' THEN 2
        WHEN 'First' THEN 3
        ELSE NULL
    END;

    IF v_multiplier IS NULL THEN
        RAISE EXCEPTION 'Kelas kabin % tidak valid.', p_kelas_kabin;
    END IF;

    RETURN (v_base_miles * v_multiplier)::INT;
END;
$$;

-- ---------------------------------------------------------------------------
-- Stored procedure untuk staf memproses klaim missing miles.
-- Jika klaim disetujui, award_miles dan total_miles member otomatis bertambah.
-- Jika klaim ditolak, hanya status klaim dan email staf yang berubah.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_proses_claim_missing_miles(
    p_id_klaim INT,
    p_email_staf VARCHAR,
    p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_klaim RECORD;
    v_staf_exists BOOLEAN;
    v_miles_tambah INT;
BEGIN
    IF p_status NOT IN ('Disetujui', 'Ditolak') THEN
        RAISE EXCEPTION 'Status klaim tidak valid. Status harus Disetujui atau Ditolak.';
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM staf WHERE LOWER(email) = LOWER(p_email_staf)
    ) INTO v_staf_exists;

    IF NOT v_staf_exists THEN
        RAISE EXCEPTION 'Staf dengan email % tidak ditemukan.', p_email_staf;
    END IF;

    SELECT id, email_member, maskapai, bandara_asal, bandara_tujuan,
           tanggal_penerbangan, kelas_kabin, status_penerimaan
    INTO v_klaim
    FROM claim_missing_miles
    WHERE id = p_id_klaim
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Klaim tidak ditemukan.';
    END IF;

    IF v_klaim.status_penerimaan <> 'Menunggu' THEN
        RAISE EXCEPTION 'Klaim sudah diproses dan tidak dapat diubah lagi.';
    END IF;

    UPDATE claim_missing_miles
    SET status_penerimaan = p_status,
        email_staf = (
            SELECT email FROM staf WHERE LOWER(email) = LOWER(p_email_staf)
        )
    WHERE id = p_id_klaim;

    IF p_status = 'Disetujui' THEN
        v_miles_tambah := fn_hitung_missing_miles(
            v_klaim.bandara_asal,
            v_klaim.bandara_tujuan,
            v_klaim.kelas_kabin
        );

        UPDATE member
        SET award_miles = award_miles + v_miles_tambah,
            total_miles = total_miles + v_miles_tambah
        WHERE email = v_klaim.email_member;
    END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- Stored procedure untuk transfer miles antar member.
-- Validasi saldo, penerima, jumlah, dan larangan transfer ke diri sendiri
-- dilakukan di database agar transaksi lebih aman.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_transfer_miles(
    p_email_pengirim VARCHAR,
    p_email_penerima VARCHAR,
    p_jumlah INT,
    p_catatan VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_email_pengirim VARCHAR(100);
    v_email_penerima VARCHAR(100);
    v_saldo_pengirim INT;
BEGIN
    IF p_email_pengirim IS NULL OR TRIM(p_email_pengirim) = '' THEN
        RAISE EXCEPTION 'Email pengirim wajib diisi.';
    END IF;

    IF p_email_penerima IS NULL OR TRIM(p_email_penerima) = '' THEN
        RAISE EXCEPTION 'Email penerima wajib diisi.';
    END IF;

    IF LOWER(p_email_pengirim) = LOWER(p_email_penerima) THEN
        RAISE EXCEPTION 'Tidak dapat mentransfer miles ke diri sendiri.';
    END IF;

    IF p_jumlah IS NULL OR p_jumlah <= 0 THEN
        RAISE EXCEPTION 'Jumlah transfer harus lebih besar dari 0.';
    END IF;

    SELECT email, award_miles
    INTO v_email_pengirim, v_saldo_pengirim
    FROM member
    WHERE LOWER(email) = LOWER(p_email_pengirim)
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Member pengirim tidak ditemukan.';
    END IF;

    SELECT email
    INTO v_email_penerima
    FROM member
    WHERE LOWER(email) = LOWER(p_email_penerima)
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Email penerima bukan member aktif.';
    END IF;

    IF v_saldo_pengirim < p_jumlah THEN
        RAISE EXCEPTION 'Award miles tidak mencukupi. Saldo saat ini: % miles.', v_saldo_pengirim;
    END IF;

    UPDATE member
    SET award_miles = award_miles - p_jumlah
    WHERE email = v_email_pengirim;

    UPDATE member
    SET award_miles = award_miles + p_jumlah
    WHERE email = v_email_penerima;

    INSERT INTO transfer (
        email_member_1,
        email_member_2,
        timestamp,
        jumlah,
        catatan
    )
    VALUES (
        v_email_pengirim,
        v_email_penerima,
        NOW(),
        p_jumlah,
        NULLIF(TRIM(p_catatan), '')
    );
END;
$$;


-- ---------------------------------------------------------------------------
-- Pastikan kelas kabin Premium Economy diterima pada database yang sudah dibuat.
-- Aman dijalankan berulang karena constraint lama di-drop dulu jika ada.
-- ---------------------------------------------------------------------------
ALTER TABLE IF EXISTS claim_missing_miles
DROP CONSTRAINT IF EXISTS claim_missing_miles_kelas_kabin_check;

ALTER TABLE IF EXISTS claim_missing_miles
ADD CONSTRAINT claim_missing_miles_kelas_kabin_check
CHECK (kelas_kabin IN ('Economy', 'Premium Economy', 'Business', 'First'));
