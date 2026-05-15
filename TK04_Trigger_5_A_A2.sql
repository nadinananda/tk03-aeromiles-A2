SET search_path TO aeromiles, public, extensions;

CREATE OR REPLACE FUNCTION aeromiles.update_member_miles_on_claim_approval()
RETURNS TRIGGER AS $$
DECLARE
    v_success_message TEXT;
BEGIN
    IF NEW.status_penerimaan = 'Disetujui'
       AND OLD.status_penerimaan IS DISTINCT FROM 'Disetujui' THEN

        UPDATE aeromiles.MEMBER
        SET award_miles = award_miles + 1000,
            total_miles = total_miles + 1000
        WHERE LOWER(email) = LOWER(NEW.email_member);

        v_success_message := 'SUKSES: Total miles Member "' || NEW.email_member ||
                             '" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "' ||
                             NEW.flight_number || '".';

        RAISE NOTICE '%', v_success_message;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_member_miles_on_claim_approval
ON aeromiles.CLAIM_MISSING_MILES;

CREATE TRIGGER trg_update_member_miles_on_claim_approval
AFTER UPDATE ON aeromiles.CLAIM_MISSING_MILES
FOR EACH ROW
EXECUTE FUNCTION aeromiles.update_member_miles_on_claim_approval();

CREATE OR REPLACE PROCEDURE aeromiles.sp_proses_claim_missing_miles(
    p_claim_id INTEGER,
    p_staf_email VARCHAR,
    p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_claim RECORD;
    v_staf_email VARCHAR(100);
BEGIN
    IF p_status NOT IN ('Disetujui', 'Ditolak') THEN
        RAISE EXCEPTION 'ERROR: Status klaim tidak valid. Status harus Disetujui atau Ditolak.';
    END IF;

    SELECT email INTO v_staf_email
    FROM aeromiles.STAF
    WHERE LOWER(email) = LOWER(p_staf_email);

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Staf dengan email "%" tidak ditemukan.', p_staf_email;
    END IF;

    SELECT id, email_member, flight_number, status_penerimaan
    INTO v_claim
    FROM aeromiles.CLAIM_MISSING_MILES
    WHERE id = p_claim_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: Klaim missing miles tidak ditemukan.';
    END IF;

    IF v_claim.status_penerimaan <> 'Menunggu' THEN
        RAISE EXCEPTION 'ERROR: Klaim sudah diproses dan tidak dapat diubah lagi.';
    END IF;

    UPDATE aeromiles.CLAIM_MISSING_MILES
    SET status_penerimaan = p_status,
        email_staf = v_staf_email
    WHERE id = p_claim_id;

    IF p_status = 'Disetujui' THEN
        RAISE NOTICE 'SUKSES: Total miles Member "%" telah diperbarui. Miles ditambahkan: 1000 miles dari klaim penerbangan "%".',
            v_claim.email_member, v_claim.flight_number;
    ELSE
        RAISE NOTICE 'SUKSES: Klaim penerbangan untuk member "%" telah ditolak.',
            v_claim.email_member;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION aeromiles.get_top_5_members()
RETURNS TABLE(
    rank INT,
    email VARCHAR,
    nomor_member VARCHAR,
    nama_lengkap VARCHAR,
    total_miles INT,
    award_miles INT,
    id_tier VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROW_NUMBER() OVER (ORDER BY m.total_miles DESC)::INT AS rank,
        m.email,
        m.nomor_member,
        TRIM(p.first_mid_name || ' ' || p.last_name)::VARCHAR AS nama_lengkap,
        m.total_miles,
        m.award_miles,
        COALESCE(t.nama, m.id_tier)::VARCHAR AS id_tier
    FROM aeromiles.MEMBER m
    JOIN aeromiles.PENGGUNA p ON m.email = p.email
    LEFT JOIN aeromiles.TIER t ON m.id_tier = t.id_tier
    ORDER BY m.total_miles DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION aeromiles.display_top_5_members_report()
RETURNS TEXT AS $$
DECLARE
    v_top_member_email VARCHAR;
    v_top_member_miles INT;
BEGIN
    SELECT m.email, m.total_miles
    INTO v_top_member_email, v_top_member_miles
    FROM aeromiles.MEMBER m
    ORDER BY m.total_miles DESC
    LIMIT 1;

    IF v_top_member_email IS NULL THEN
        RETURN 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, belum ada member terdaftar.';
    END IF;

    RETURN 'SUKSES: Daftar Top 5 Member berdasarkan total miles berhasil diperbarui, ' ||
           'dengan peringkat pertama "' || v_top_member_email || '" memiliki ' ||
           v_top_member_miles || ' miles.';
END;
$$ LANGUAGE plpgsql;
