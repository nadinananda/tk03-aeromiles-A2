SET search_path TO aeromiles, public, extensions;

-- Tansfer Miles

CREATE OR REPLACE PROCEDURE sp_transfer_miles (
    p_email_pengirim VARCHAR,
    p_email_penerima VARCHAR,
    P_jumlah INT,
    p_catatan VARCHAR,
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_pengirim_exist INTEGER;
    v_penerima_exist INTEGER;
    v_saldo_pengirim INT;
BEGIN
    IF LOWER(p_email_pengirim) = LOWER(p_email_penerima) THEN
        RAISE EXCEPTION 'Kamu tidak bisa transfer miles ke dirimu sendiri';
    END IF;

    SELECT COUNT(*) INTO v_pengirim_exist FROM MEMBER WHERE LOWER(email) = LOWER(p_email_pengirim);
    IF v_pengirim_exist = 0 THEN
        RAISE EXCEPTION 'Member pengirim dengan email % tidak ditemukan!', p_email_pengirim;
    END IF;

    SELECT COUNT(*) INTO v_penerima_exist FROM MEMBER WHERE LOWER(email) = LOWER(p_email_penerima);
    IF v_penerima_exist = 0 THEN
        RAISE EXCEPTION 'Member penerima dengan email % tidak ditemukan!', p_email_penerima;
    END IF;

    IF p_jumlah <= 0 THEN
         RAISE EXCEPTION 'Jumlah transfer harus lebih besar dari 0!';
    END IF;

    SELECT award_miles INTO v_saldo_pengirim FROM MEMBER WHERE LOWER(email) = LOWER(p_email_pengirim);
    IF v_saldo_pengirim < p_jumlah THEN
        RAISE EXCEPTION 'Saldo award_miles tidak mencukupi untuk melakukan transfer sebesar % miles. Saldo saat ini: %', p_jumlah, v_saldo_pengirim;
    END IF;

    UPDATE MEMBER 
    SET award_miles = award_miles - p_jumlah 
    WHERE LOWER(email) = LOWER(p_email_pengirim);

    UPDATE MEMBER 
    SET award_miles = award_miles + p_jumlah 
    WHERE LOWER(email) = LOWER(p_email_penerima);

    INSERT INTO TRANSFER (email_member_1, email_member_2, timestamp, jumlah, catatan)
    VALUES (
        (SELECT email FROM MEMBER WHERE LOWER(email) = LOWER(p_email_pengirim)), 
        (SELECT email FROM MEMBER WHERE LOWER(email) = LOWER(p_email_penerima)), 
        CURRENT_TIMESTAMP, 
        p_jumlah, 
        p_catatan
    );

END;
$$;