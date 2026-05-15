SET search_path TO aeromiles, public, extensions;

CREATE OR REPLACE FUNCTION check_duplicate_claim_missing_miles()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM claim_missing_miles
        WHERE LOWER(email_member) = LOWER(NEW.email_member)
          AND UPPER(flight_number) = UPPER(NEW.flight_number)
          AND tanggal_penerbangan = NEW.tanggal_penerbangan
          AND UPPER(nomor_tiket) = UPPER(NEW.nomor_tiket)
          AND id <> COALESCE(NEW.id, -1)
    ) THEN
        RAISE EXCEPTION
        'ERROR: Klaim untuk penerbangan "%" pada tanggal "%" dengan nomor tiket "%" sudah pernah diajukan sebelumnya.',
        NEW.flight_number, NEW.tanggal_penerbangan, NEW.nomor_tiket;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_duplicate_claim_missing_miles ON claim_missing_miles;

CREATE TRIGGER trg_duplicate_claim_missing_miles
BEFORE INSERT OR UPDATE OF email_member, flight_number, tanggal_penerbangan, nomor_tiket
ON claim_missing_miles
FOR EACH ROW
EXECUTE FUNCTION check_duplicate_claim_missing_miles();

CREATE OR REPLACE FUNCTION update_member_tier_by_total_miles()
RETURNS TRIGGER AS $$
DECLARE
    tier_baru VARCHAR(10);
    nama_tier_lama VARCHAR(50);
    nama_tier_baru VARCHAR(50);
BEGIN
    SELECT id_tier
    INTO tier_baru
    FROM tier
    WHERE minimal_tier_miles <= COALESCE(NEW.total_miles, 0)
    ORDER BY minimal_tier_miles DESC
    LIMIT 1;

    IF tier_baru IS NOT NULL AND NEW.id_tier IS DISTINCT FROM tier_baru THEN
        SELECT nama
        INTO nama_tier_lama
        FROM tier
        WHERE id_tier = NEW.id_tier;

        SELECT nama
        INTO nama_tier_baru
        FROM tier
        WHERE id_tier = tier_baru;

        NEW.id_tier := tier_baru;

        RAISE NOTICE
        'SUKSES: Tier Member "%" telah diperbarui dari "%" menjadi "%" berdasarkan total miles yang dimiliki.',
        NEW.email, COALESCE(nama_tier_lama, '-'), nama_tier_baru;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_member_tier ON member;

CREATE TRIGGER trg_update_member_tier
BEFORE INSERT OR UPDATE OF total_miles
ON member
FOR EACH ROW
EXECUTE FUNCTION update_member_tier_by_total_miles();