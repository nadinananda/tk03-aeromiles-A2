SET search_path TO aeromiles, public, extensions;

CREATE OR REPLACE FUNCTION trg_transfer_miles_func()
RETURNS TRIGGER AS $$
DECLARE
    v_pengirim_exist INTEGER;
    v_penerima_exist INTEGER;
    v_saldo_pengirim INT;
BEGIN

    IF LOWER(NEW.email_member_1) = LOWER(NEW.email_member_2) THEN
        RAISE EXCEPTION 'U-umm... Kamu tidak bisa transfer miles ke dirimu sendiri, baka!';
    END IF;

    SELECT COUNT(*) INTO v_pengirim_exist FROM MEMBER WHERE LOWER(email) = LOWER(NEW.email_member_1);
    IF v_pengirim_exist = 0 THEN
        RAISE EXCEPTION 'Member pengirim dengan email % tidak ditemukan!', NEW.email_member_1;
    END IF;

    SELECT COUNT(*) INTO v_penerima_exist FROM MEMBER WHERE LOWER(email) = LOWER(NEW.email_member_2);
    IF v_penerima_exist = 0 THEN
        RAISE EXCEPTION 'Member penerima dengan email % tidak ditemukan!', NEW.email_member_2;
    END IF;

    IF NEW.jumlah <= 0 THEN
         RAISE EXCEPTION 'Jumlah transfer harus lebih besar dari 0!';
    END IF;

    SELECT award_miles INTO v_saldo_pengirim FROM MEMBER WHERE LOWER(email) = LOWER(NEW.email_member_1);
    IF v_saldo_pengirim < NEW.jumlah THEN
        RAISE EXCEPTION 'Saldo award_miles tidak mencukupi untuk melakukan transfer sebesar % miles. Saldo saat ini: %', NEW.jumlah, v_saldo_pengirim;
    END IF;

    UPDATE MEMBER 
    SET award_miles = award_miles - NEW.jumlah 
    WHERE LOWER(email) = LOWER(NEW.email_member_1);

    UPDATE MEMBER 
    SET award_miles = award_miles + NEW.jumlah 
    WHERE LOWER(email) = LOWER(NEW.email_member_2);

    NEW.timestamp := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trigger_transfer_miles ON TRANSFER;

CREATE TRIGGER trigger_transfer_miles
BEFORE INSERT ON TRANSFER
FOR EACH ROW
EXECUTE FUNCTION trg_transfer_miles_func();