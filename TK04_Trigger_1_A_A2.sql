SET search_path TO aeromiles, public, extensions;

-- Trigger Registrasi

CREATE OR REPLACE FUNCTION check_pengguna_email()
RETURNS TRIGGER AS $$
DECLARE
    v_email_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_email_count FROM PENGGUNA WHERE LOWER(email) = LOWER(NEW.email);
    IF v_email_count > 0 THEN
        RAISE EXCEPTION 'Email % sudah terdaftar, silakan gunakan email lain.', NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_email_used
BEFORE INSERT ON pengguna
FOR EACH ROW 
EXECUTE FUNCTION check_pengguna_email();

-- Trigger Login

CREATE OR REPLACE FUNCTION check_kredensial(
    p_email VARCHAR,
    p_password VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_valid BOOLEAN;
BEGIN

    SELECT (password = extensions.crypt(p_password, password)) INTO v_is_valid
    FROM PENGGUNA 
    WHERE LOWER(email) = LOWER(p_email);

    IF v_is_valid IS NULL THEN
        v_is_valid := FALSE;
    END IF;

    RETURN v_is_valid;
END;
$$ LANGUAGE plpgsql;