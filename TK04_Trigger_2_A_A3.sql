SET search_path TO aeromiles, public, extensions;

CREATE OR REPLACE FUNCTION trg_transfer_miles_func()
RETURNS TRIGGER AS $$
DECLARE
    v_pengirim_exist INTEGER;
    v_penerima_exist INTEGER;
    v_saldo_pengirim INT;
BEGIN
    IF LOWER(NEW.email_member_1) = LOWER(NEW.email_member_2) THEN
        RAISE EXCEPTION 'ERROR: Tidak dapat mentransfer miles ke diri sendiri.';
    END IF;

    SELECT COUNT(*)
    INTO v_pengirim_exist
    FROM member
    WHERE LOWER(email) = LOWER(NEW.email_member_1);

    IF v_pengirim_exist = 0 THEN
        RAISE EXCEPTION 'ERROR: Member pengirim dengan email % tidak ditemukan.', NEW.email_member_1;
    END IF;

    SELECT COUNT(*)
    INTO v_penerima_exist
    FROM member
    WHERE LOWER(email) = LOWER(NEW.email_member_2);

    IF v_penerima_exist = 0 THEN
        RAISE EXCEPTION 'ERROR: Member penerima dengan email % tidak ditemukan.', NEW.email_member_2;
    END IF;

    IF NEW.jumlah <= 0 THEN
        RAISE EXCEPTION 'ERROR: Jumlah transfer harus lebih besar dari 0.';
    END IF;

    SELECT award_miles
    INTO v_saldo_pengirim
    FROM member
    WHERE LOWER(email) = LOWER(NEW.email_member_1)
    FOR UPDATE;

    IF v_saldo_pengirim < NEW.jumlah THEN
        RAISE EXCEPTION
            'ERROR: Saldo award miles tidak mencukupi. Saldo Anda saat ini: % miles, jumlah transfer: % miles.',
            v_saldo_pengirim,
            NEW.jumlah;
    END IF;

    UPDATE member
    SET award_miles = award_miles - NEW.jumlah
    WHERE LOWER(email) = LOWER(NEW.email_member_1);

    UPDATE member
    SET award_miles = award_miles + NEW.jumlah,
        total_miles = total_miles + NEW.jumlah
    WHERE LOWER(email) = LOWER(NEW.email_member_2);

    NEW.timestamp := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trigger_transfer_miles ON transfer;

CREATE TRIGGER trigger_transfer_miles
BEFORE INSERT ON transfer
FOR EACH ROW
EXECUTE FUNCTION trg_transfer_miles_func();