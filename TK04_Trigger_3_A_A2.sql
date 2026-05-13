SET search_path TO aeromiles, public, extensions;

-- validasi dan update saldo miles saat redeem hadiah

CREATE OR REPLACE FUNCTION process_redeem_hadiah()
RETURNS TRIGGER AS $$
DECLARE
    v_miles_hadiah INT;
    v_nama_hadiah VARCHAR;
    v_valid_start DATE;
    v_program_end DATE;
    v_saldo_member INT;
BEGIN
    SELECT miles, nama, valid_start_date, program_end
    INTO v_miles_hadiah, v_nama_hadiah, v_valid_start, v_program_end
    FROM aeromiles.HADIAH
    WHERE kode_hadiah = NEW.kode_hadiah;

    IF CURRENT_DATE < v_valid_start OR CURRENT_DATE > v_program_end THEN
        RAISE EXCEPTION 'ERROR: Hadiah "%" tidak tersedia pada periode ini.', v_nama_hadiah;
    END IF;

    SELECT award_miles INTO v_saldo_member
    FROM aeromiles.MEMBER
    WHERE email = NEW.email_member;

    IF v_saldo_member < v_miles_hadiah THEN
        RAISE EXCEPTION 'ERROR: Saldo award miles tidak mencukupi. Dibutuhkan % miles, saldo Anda: % miles.', v_miles_hadiah, v_saldo_member;
    END IF;

    UPDATE aeromiles.MEMBER
    SET award_miles = award_miles - v_miles_hadiah
    WHERE email = NEW.email_member;

    RAISE NOTICE 'SUKSES: Redeem hadiah "%" berhasil. Award miles Anda berkurang % miles.', v_nama_hadiah, v_miles_hadiah;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_redeem_hadiah ON aeromiles.REDEEM;
CREATE TRIGGER trg_redeem_hadiah
BEFORE INSERT ON aeromiles.REDEEM
FOR EACH ROW EXECUTE FUNCTION process_redeem_hadiah();


-- validasi dan update saldo miles saat beli package

CREATE OR REPLACE FUNCTION process_beli_package()
RETURNS TRIGGER AS $$
DECLARE
    v_jumlah_miles INT;
BEGIN
    SELECT jumlah_award_miles INTO v_jumlah_miles
    FROM aeromiles.AWARD_MILES_PACKAGE
    WHERE id = NEW.id_award_miles_package;

    UPDATE aeromiles.MEMBER
    SET award_miles = award_miles + v_jumlah_miles,
        total_miles = total_miles + v_jumlah_miles
    WHERE email = NEW.email_member;

    RAISE NOTICE 'SUKSES: Pembelian package berhasil. Award miles dan total miles Anda bertambah % miles.', v_jumlah_miles;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_beli_package ON aeromiles.MEMBER_AWARD_MILES_PACKAGE;
CREATE TRIGGER trg_beli_package
BEFORE INSERT ON aeromiles.MEMBER_AWARD_MILES_PACKAGE
FOR EACH ROW EXECUTE FUNCTION process_beli_package();